from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class CacheEntry:
    key: str
    body: bytes
    content_type: str
    status_code: int
    origin_headers: dict
    size: int
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    access_count: int = 0
    expires_at: Optional[float] = None
    hit_count: int = 0
    miss_count: int = 0

    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at
