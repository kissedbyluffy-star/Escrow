from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RateLimit:
    limit: int
    window_sec: int
    hits: deque[float] = field(default_factory=deque)

    def allow(self) -> bool:
        now = time.monotonic()
        while self.hits and now - self.hits[0] > self.window_sec:
            self.hits.popleft()
        if len(self.hits) >= self.limit:
            return False
        self.hits.append(now)
        return True


class RateLimiter:
    def __init__(self) -> None:
        self._limits: dict[str, RateLimit] = {}

    def allow(self, key: str, limit: int, window_sec: int) -> bool:
        limit_key = f"{key}:{limit}:{window_sec}"
        if limit_key not in self._limits:
            self._limits[limit_key] = RateLimit(limit=limit, window_sec=window_sec)
        return self._limits[limit_key].allow()


class GlobalSpikeGuard:
    def __init__(self, hard_limit: int, window_sec: int) -> None:
        self.hard_limit = hard_limit
        self.window_sec = window_sec
        self.hits: deque[float] = deque()

    def record(self) -> bool:
        now = time.monotonic()
        while self.hits and now - self.hits[0] > self.window_sec:
            self.hits.popleft()
        self.hits.append(now)
        return len(self.hits) <= self.hard_limit
