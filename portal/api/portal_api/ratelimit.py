"""A per-address sliding-window limit for the public property endpoints.

Kept in memory: the portal runs one API process. If it ever runs several, each
process allows the full limit, which multiplies it; move this to the database then.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from portal_api.auth import rate_bucket


class SlidingWindow:
    def __init__(self, limit: int, window_seconds: float = 60):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


def _check(request: Request, name: str) -> None:
    limiter: SlidingWindow = getattr(request.app.state, name)
    key = rate_bucket(request.client.host if request.client else None) or "unknown"
    if not limiter.allow(key):
        raise HTTPException(status_code=429, detail="too_many_requests")


def lookup_limit(request: Request) -> None:
    _check(request, "lookup_limiter")


def tile_limit(request: Request) -> None:
    _check(request, "tile_limiter")
