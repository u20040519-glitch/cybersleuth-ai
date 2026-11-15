# =============================================================================
# CYBERSLEUTH AI - In-memory rate limiter (Phase 7)
# =============================================================================
# Fixed-window, per-process rate limiting for abuse-prone endpoints (auth).
# This is intentionally dependency-free: a deployment with several replicas
# should move to the shared REDIS_URL-backed limiter instead (the middleware
# contract is identical).
# =============================================================================

from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Tuple


class RateLimiter:
    """Thread-safe fixed-window counter keyed by an arbitrary string."""

    def __init__(self, max_requests: int, window_seconds: float):
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.Lock()

    def _prune_locked(self, key: str, now: float) -> Tuple[int, float]:
        count, window_start = self._hits.get(key, (0, now))
        if now - window_start >= self.window_seconds:
            return 0, now
        return count, window_start

    def check(self, key: str) -> Tuple[bool, int]:
        """Register one hit. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            count, window_start = self._prune_locked(key, now)
            if count >= self.max_requests:
                retry_after = int(self.window_seconds - (now - window_start)) + 1
                return False, max(retry_after, 1)
            self._hits[key] = (count + 1, window_start)
            # Opportunistic cleanup so the map does not grow unbounded.
            if len(self._hits) > 4096:
                cutoff = now - self.window_seconds
                self._hits = {k: v for k, v in self._hits.items() if v[1] >= cutoff}
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# Shared registry so tests can reset state between cases.
_limiters: Dict[str, RateLimiter] = {}


def get_limiter(name: str, max_requests: int, window_seconds: float) -> RateLimiter:
    limiter = _limiters.get(name)
    if limiter is None:
        limiter = RateLimiter(max_requests, window_seconds)
        _limiters[name] = limiter
    return limiter


def reset_limiters() -> None:
    for limiter in _limiters.values():
        limiter.reset()
