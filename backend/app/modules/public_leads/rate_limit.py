"""In-memory sliding-window rate limiter for public inbound leads (E5-B MVP).

Limitations:
- process-local only (not shared across workers);
- resets on process restart;
- acceptable for single-process MVP, not final multi-worker protection.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.core.exceptions import RateLimitExceededError

PUBLIC_LEADS_RATE_LIMIT_MESSAGE = "Too many requests. Please try again later."


@dataclass(frozen=True)
class RateLimitRule:
    window_seconds: int
    max_requests: int


class InMemorySlidingWindowRateLimiter:
    """Thread-safe sliding window limiter keyed by opaque client id (e.g. IP)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (key, window_seconds) -> monotonic timestamps of accepted hits
        self._buckets: dict[tuple[str, int], list[float]] = {}

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()

    def check_and_increment(self, key: str, rules: list[RateLimitRule]) -> None:
        if not key:
            key = "unknown"
        now = time.monotonic()
        with self._lock:
            for rule in rules:
                if rule.window_seconds <= 0 or rule.max_requests <= 0:
                    continue
                bucket_key = (key, rule.window_seconds)
                timestamps = [
                    stamp
                    for stamp in self._buckets.get(bucket_key, [])
                    if now - stamp < rule.window_seconds
                ]
                if len(timestamps) >= rule.max_requests:
                    raise RateLimitExceededError(PUBLIC_LEADS_RATE_LIMIT_MESSAGE)
                timestamps.append(now)
                self._buckets[bucket_key] = timestamps


# Process-wide singleton used by PublicLeadService
public_leads_rate_limiter = InMemorySlidingWindowRateLimiter()
