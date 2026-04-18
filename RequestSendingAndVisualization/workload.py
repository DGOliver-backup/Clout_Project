import httpx
import time
import asyncio
import numpy as np
import json
from typing import List
import os

#Allow the input of IP when executing this file, it has been set to 127.0.0.1 bu default
PROXY_IP = os.getenv("PROXY_IP", "127.0.0.1")
PROXY_URL = f"http://{PROXY_IP}:8000"
POLICIES = ["LRU", "LFU", "TTL"]

SMALL_FILES = [f"small{i}.txt" for i in range(1, 111)]
MEDIUM_FILES = [f"medium{i}.txt" for i in range(1, 71)]
LARGE_FILES = [f"large{i}.txt" for i in range(1, 21)]

FILES = SMALL_FILES + MEDIUM_FILES + LARGE_FILES
REQUEST_COUNT = 1000

# workload distribution
p_small_total = 0.33
p_medium_total = 0.33
p_large_total = 0.33

probs = (
    [p_small_total / len(SMALL_FILES)] * len(SMALL_FILES) +
    [p_medium_total / len(MEDIUM_FILES)] * len(MEDIUM_FILES) +
    [p_large_total / len(LARGE_FILES)] * len(LARGE_FILES)
)

probs = np.array(probs)
probs /= probs.sum()

# Fixed workload for all policies
np.random.seed(42)
FIXED_WORKLOAD = np.random.choice(FILES, size=REQUEST_COUNT, p=probs).tolist()


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

# Record whole Headers
async def fetch_file(client: httpx.AsyncClient, filename: str):
    start = time.perf_counter()

    try:
        url = f"{PROXY_URL}/test_data/{filename}"
        resp = await client.get(url)
        latency = (time.perf_counter() - start) * 1000

        headers = dict(resp.headers)

        return {
            "file": filename,
            "url": url,
            "status_code": resp.status_code,
            "latency_ms": round(latency, 3),
            "content_length": to_int(headers.get("content-length")),
            "content_type": headers.get("content-type"),
            "last_modified": headers.get("last-modified"),
            "etag": headers.get("etag"),
            "date": headers.get("date"),
            "server": headers.get("server"),
            "cache": headers.get("x-cache"),
            "cache_policy": headers.get("x-cache-policy"),
            "cache_key": headers.get("x-cache-key"),
            "cache_reason": headers.get("x-cache-reason"),
            "cache_ttl": headers.get("x-cache-ttl"),
            "cache_ttl_float": to_float(headers.get("x-cache-ttl")),
            "cache_usage": headers.get("x-cache-usage"),
            "cache_usage_float": to_float(headers.get("x-cache-usage")),
            "cache_hits": to_int(headers.get("x-cache-hits")),
            "cache_misses": to_int(headers.get("x-cache-misses")),
            "cache_object_count": to_int(headers.get("x-cache-object-count")),
            "cache_evictions": to_int(headers.get("x-cache-evictions")),
            "response_time_ms": to_float(headers.get("x-response-time-ms")),
            "origin_latency_ms": to_float(headers.get("x-origin-latency-ms")),


            "headers": headers,
        }

    except Exception as e:
        return {
            "file": filename,
            "url": f"{PROXY_URL}/test_data/{filename}",
            "error": str(e),
        }

# Concurrency control
async def run_parallel_workload(policy: str, workload: List[str]):
    batch_size = 5
    results = []

    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)

    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        for i in range(0, len(workload), batch_size):
            chunk = workload[i:i + batch_size]

            tasks = [fetch_file(client, fname) for fname in chunk]
            chunk_results = await asyncio.gather(*tasks)
            results.extend(chunk_results)

            current_sent = min(i + batch_size, len(workload))
            if current_sent % 10 == 0 or current_sent == len(workload):
                print(f"  Progress: {current_sent}/{len(workload)} requests processed...")

            if current_sent < len(workload):
                await asyncio.sleep(1)

    return results


def set_policy(policy: str):
    print(f"\n Switching policy to: {policy}")
    httpx.post(f"{PROXY_URL}/cache/clear", timeout=10.0)
    httpx.post(f"{PROXY_URL}/cache/policy/{policy}", timeout=10.0)


def get_stats():
    return httpx.get(f"{PROXY_URL}/cache/stats", timeout=10.0).json()


async def main():
    all_results = {}

    for policy in POLICIES:
        set_policy(policy)

        results = await run_parallel_workload(policy, FIXED_WORKLOAD)
        stats = get_stats()

        all_results[policy] = {
            "stats": stats,
            "requests": results,
        }

        print(f" {policy} Hit Rate: {stats.get('hit_rate', 0):.2%}")
        print(f" Avg Hit Latency: {stats.get('average_hit_latency_ms', 0):.2f}ms")
        print(f" Avg Miss Latency: {stats.get('average_miss_latency_ms', 0):.2f}ms")
        print(f" Avg Origin Latency: {stats.get('average_origin_latency_ms', 0):.2f}ms")
        print(f" Origin Fetches: {stats.get('origin_fetches', 0)}")
        print(f" Evictions: {stats.get('evictions', 0)}")
        print(f" Cache Usage: {stats.get('cache_usage', 0):.2f}")

    with open("experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print("\n Experiment completed. Results saved to experiment_results.json")


if __name__ == "__main__":
    asyncio.run(main())

    print("\n Test finished. Launching visualization...")

    exit_code = os.system("python visualize.py")

    if exit_code == 0:
        print(" Visualization completed successfully!")
    else:
        print(" Visualization failed to run. Please check visualize.py.")
