import time
from typing import Optional, Tuple, List, Dict
from models import CacheEntry


class CacheStore:
    def __init__(self, policy: str, max_bytes: int, default_ttl: int):
        self.policy = policy.upper()
        self.max_bytes = max_bytes
        self.default_ttl = default_ttl

        self.entries: Dict[str, CacheEntry] = {}
        self.used_bytes = 0

        self.requests = 0
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expired_removals = 0
        self.oversize_skips = 0
        self.origin_fetches = 0

        self.bytes_served_from_cache = 0
        self.bytes_fetched_from_origin = 0

        self.per_key_hits: Dict[str, int] = {}
        self.per_key_misses: Dict[str, int] = {}

        self.request_logs: List[dict] = []
        self.max_log_entries = 500

        self.total_hit_latency_ms = 0.0
        self.total_miss_latency_ms = 0.0
        self.total_origin_latency_ms = 0.0
        self.hit_latency_count = 0
        self.miss_latency_count = 0
        self.origin_latency_count = 0

    def set_policy(self, policy: str) -> None:
        self.policy = policy.upper()

    def record_hit_latency(self, latency_ms: float) -> None:
        self.total_hit_latency_ms += latency_ms
        self.hit_latency_count += 1

    def record_miss_latency(self, latency_ms: float) -> None:
        self.total_miss_latency_ms += latency_ms
        self.miss_latency_count += 1

    def record_origin_latency(self, latency_ms: float) -> None:
        self.total_origin_latency_ms += latency_ms
        self.origin_latency_count += 1

    def _log_request(
        self,
        key: str,
        result: str,
        reason: str,
        size: int,
        total_latency_ms: Optional[float] = None,
        origin_latency_ms: Optional[float] = None,
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "key": key,
            "result": result,
            "reason": reason,
            "size": size,
            "policy": self.policy,
            "total_latency_ms": round(total_latency_ms, 3) if total_latency_ms is not None else None,
            "origin_latency_ms": round(origin_latency_ms, 3) if origin_latency_ms is not None else None,
        }
        self.request_logs.append(entry)
        if len(self.request_logs) > self.max_log_entries:
            self.request_logs.pop(0)

    def _remove(self, key: str) -> None:
        entry = self.entries.pop(key, None)
        if entry is not None:
            self.used_bytes -= entry.size

    def clear(self) -> None:
        self.entries.clear()
        self.used_bytes = 0
        self.request_logs.clear()

    def _eviction_candidate_key(self) -> Optional[str]:
        if not self.entries:
            return None

        if self.policy == "LRU":
            return min(self.entries, key=lambda k: self.entries[k].last_access)

        if self.policy == "LFU":
            return min(
                self.entries,
                key=lambda k: (self.entries[k].access_count, self.entries[k].last_access),
            )

        if self.policy == "TTL":
            return min(
                self.entries,
                key=lambda k: (
                    self.entries[k].expires_at if self.entries[k].expires_at is not None else float("inf"),
                    self.entries[k].last_access,
                ),
            )

        return min(self.entries, key=lambda k: self.entries[k].last_access)

    def _evict_one(self) -> bool:
        victim = self._eviction_candidate_key()
        if victim is None:
            return False
        self._remove(victim)
        self.evictions += 1
        return True

    def _cleanup_expired(self) -> None:
        expired_keys = [k for k, v in self.entries.items() if v.is_expired()]
        for key in expired_keys:
            self._remove(key)
            self.expired_removals += 1

    def get(self, key: str) -> Tuple[Optional[CacheEntry], str]:
        self.requests += 1

        entry = self.entries.get(key)
        if entry is None:
            self.misses += 1
            self.per_key_misses[key] = self.per_key_misses.get(key, 0) + 1
            return None, "not_found"

        if entry.is_expired():
            self._remove(key)
            self.misses += 1
            self.expired_removals += 1
            self.per_key_misses[key] = self.per_key_misses.get(key, 0) + 1
            return None, "expired"

        entry.last_access = time.time()
        entry.access_count += 1
        entry.hit_count += 1

        self.hits += 1
        self.bytes_served_from_cache += entry.size
        self.per_key_hits[key] = self.per_key_hits.get(key, 0) + 1
        return entry, "fresh"

    def put(
        self,
        key: str,
        body: bytes,
        content_type: str,
        status_code: int,
        origin_headers: dict,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        size = len(body)

        if size > self.max_bytes:
            self.oversize_skips += 1
            return "oversize"

        if key in self.entries:
            self._remove(key)

        self._cleanup_expired()

        while self.used_bytes + size > self.max_bytes:
            evicted = self._evict_one()
            if not evicted:
                break

        expires_at = None
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        if ttl is not None and ttl > 0:
            expires_at = time.time() + ttl

        entry = CacheEntry(
            key=key,
            body=body,
            content_type=content_type,
            status_code=status_code,
            origin_headers=origin_headers,
            size=size,
            expires_at=expires_at,
        )
        self.entries[key] = entry
        self.used_bytes += size
        self.bytes_fetched_from_origin += size
        return "stored"

    def stats(self) -> dict:
        hit_rate = (self.hits / self.requests) if self.requests else 0.0
        object_count = len(self.entries)
        avg_object_size = (self.used_bytes / object_count) if object_count else 0.0
        occupancy_pct = (self.used_bytes / self.max_bytes * 100) if self.max_bytes else 0.0

        avg_hit_latency = (
            self.total_hit_latency_ms / self.hit_latency_count
            if self.hit_latency_count else 0.0
        )
        avg_miss_latency = (
            self.total_miss_latency_ms / self.miss_latency_count
            if self.miss_latency_count else 0.0
        )
        avg_origin_latency = (
            self.total_origin_latency_ms / self.origin_latency_count
            if self.origin_latency_count else 0.0
        )

        return {
            "policy": self.policy,
            "requests": self.requests,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4),
            "evictions": self.evictions,
            "expired_removals": self.expired_removals,
            "oversize_skips": self.oversize_skips,
            "origin_fetches": self.origin_fetches,
            "bytes_used": self.used_bytes,
            "max_bytes": self.max_bytes,
            "object_count": object_count,
            "bytes_served_from_cache": self.bytes_served_from_cache,
            "bytes_fetched_from_origin": self.bytes_fetched_from_origin,
            "average_object_size": round(avg_object_size, 2),
            "cache_occupancy_percent": round(occupancy_pct, 2),
            "average_hit_latency_ms": round(avg_hit_latency, 3),
            "average_miss_latency_ms": round(avg_miss_latency, 3),
            "average_origin_latency_ms": round(avg_origin_latency, 3),
            "per_key_hits": self.per_key_hits,
            "per_key_misses": self.per_key_misses,
        }

    def list_entries(self) -> List[dict]:
        result = []
        now = time.time()

        for key, entry in self.entries.items():
            ttl_remaining = None
            if entry.expires_at is not None:
                ttl_remaining = max(0, round(entry.expires_at - now, 2))

            result.append(
                {
                    "key": key,
                    "size": entry.size,
                    "content_type": entry.content_type,
                    "created_at": entry.created_at,
                    "last_access": entry.last_access,
                    "access_count": entry.access_count,
                    "hit_count": entry.hit_count,
                    "miss_count": entry.miss_count,
                    "expires_at": entry.expires_at,
                    "ttl_remaining_seconds": ttl_remaining,
                }
            )
        return result

    def get_logs(self) -> List[dict]:
        return self.request_logs