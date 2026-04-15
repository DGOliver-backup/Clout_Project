from fastapi import FastAPI, Request, Response
import httpx
import re
import time

from cache_store import CacheStore
from config import load_settings

settings = load_settings()
cache = CacheStore(
    policy=settings.policy,
    max_bytes=settings.max_bytes,
    default_ttl=settings.default_ttl,
)

app = FastAPI(title="Cache Proxy")


def make_cache_key(request: Request, path: str) -> str:
    query = request.url.query
    return f"{request.method}:{path}?{query}" if query else f"{request.method}:{path}"


def filter_origin_headers(headers: dict) -> dict:
    allowed = {
        "content-type",
        "content-length",
        "cache-control",
        "etag",
        "last-modified",
    }
    return {k: v for k, v in headers.items() if k.lower() in allowed}


def parse_ttl_from_cache_control(cache_control_value: str):
    """
    Returns:
    - int ttl seconds if max-age found
    - 0 if no-store or no-cache
    - None if no usable TTL found
    """
    if not cache_control_value:
        return None

    value = cache_control_value.lower()

    if "no-store" in value or "no-cache" in value:
        return 0

    match = re.search(r"max-age=(\d+)", value)
    if match:
        return int(match.group(1))

    return None


@app.get("/health")
async def health():
    return {"status": "ok", "policy": cache.policy}


@app.get("/cache/stats")
async def cache_stats():
    return cache.stats()


@app.get("/cache/entries")
async def cache_entries():
    return cache.list_entries()


@app.get("/cache/logs")
async def cache_logs():
    return cache.get_logs()


@app.post("/cache/clear")
async def cache_clear():
    cache.clear()
    return {"status": "cleared", "policy": cache.policy}


@app.post("/cache/policy/{policy_name}")
async def change_policy(policy_name: str):
    policy_name = policy_name.upper()
    if policy_name not in {"LRU", "LFU", "TTL"}:
        return {"status": "error", "message": "invalid policy"}

    cache.clear()
    cache.set_policy(policy_name)
    return {"status": "ok", "policy": cache.policy}


@app.api_route("/{path:path}", methods=["GET"])
async def proxy(path: str, request: Request):
    start_time = time.perf_counter()
    key = make_cache_key(request, path)

    entry, reason = cache.get(key)

    if entry is not None:
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        cache.record_hit_latency(total_latency_ms)
        cache._log_request(
            key=key,
            result="HIT",
            reason=reason,
            size=entry.size,
            total_latency_ms=total_latency_ms,
            origin_latency_ms=0.0,
        )

        response = Response(
            content=entry.body,
            status_code=entry.status_code,
            media_type=entry.content_type,
        )
        for h, v in entry.origin_headers.items():
            response.headers[h] = v

        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Policy"] = cache.policy
        response.headers["X-Cache-Key"] = key
        response.headers["X-Cache-Reason"] = reason
        response.headers["X-Cache-TTL"] = (
            str(max(0, round(entry.expires_at - time.time(), 3)))
            if entry.expires_at is not None else "none"
        )
        response.headers["X-Response-Time-Ms"] = f"{total_latency_ms:.3f}"
        response.headers["X-Origin-Latency-Ms"] = "0.000"
        return response

    origin_url = f"{settings.origin_base_url.rstrip('/')}/{path}"
    if request.url.query:
        origin_url += f"?{request.url.query}"

    origin_latency_ms = 0.0
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        origin_start = time.perf_counter()
        origin_resp = await client.get(origin_url)
        origin_latency_ms = (time.perf_counter() - origin_start) * 1000

    cache.origin_fetches += 1
    cache.record_origin_latency(origin_latency_ms)

    response_headers = filter_origin_headers(dict(origin_resp.headers))
    content_type = origin_resp.headers.get("content-type", "application/octet-stream")
    body = origin_resp.content

    store_result = "not_cached"
    ttl_seconds = settings.default_ttl

    cache_control = origin_resp.headers.get("cache-control", "")
    parsed_ttl = parse_ttl_from_cache_control(cache_control)
    if parsed_ttl is not None:
        ttl_seconds = parsed_ttl

    if origin_resp.status_code == 200 and ttl_seconds != 0:
        store_result = cache.put(
            key=key,
            body=body,
            content_type=content_type,
            status_code=origin_resp.status_code,
            origin_headers=response_headers,
            ttl_seconds=ttl_seconds,
        )
    elif ttl_seconds == 0:
        store_result = "no_store"

    total_latency_ms = (time.perf_counter() - start_time) * 1000
    cache.record_miss_latency(total_latency_ms)

    final_reason = reason if store_result == "stored" else store_result
    cache._log_request(
        key=key,
        result="MISS",
        reason=final_reason,
        size=len(body),
        total_latency_ms=total_latency_ms,
        origin_latency_ms=origin_latency_ms,
    )

    response = Response(
        content=body,
        status_code=origin_resp.status_code,
        media_type=content_type,
    )
    for h, v in response_headers.items():
        response.headers[h] = v

    stats = cache.stats()
    response.headers["X-Cache-Usage"] = str(round(cache.used_bytes / cache.max_bytes, 2) if cache.max_bytes else 0.0)
    response.headers["X-Cache-Occupancy-Percent"] = str(stats["cache_occupancy_percent"])
    response.headers["X-Cache-Bytes-Used"] = str(stats["bytes_used"])
    response.headers["X-Cache-Max-Bytes"] = str(stats["max_bytes"])
    response.headers["X-Cache-Object-Count"] = str(stats["object_count"])
    response.headers["X-Cache-Hit-Rate"] = str(stats["hit_rate"])
    response.headers["X-Cache-Hits"] = str(stats["hits"])
    response.headers["X-Cache-Misses"] = str(stats["misses"])
    response.headers["X-Cache-Evictions"] = str(stats["evictions"])
    response.headers["X-Cache-Expired-Removals"] = str(stats["expired_removals"])
    response.headers["X-Cache-Oversize-Skips"] = str(stats["oversize_skips"])
    response.headers["X-Cache-Origin-Fetches"] = str(stats["origin_fetches"])

    return response