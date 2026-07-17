"""In-memory sliding-window rate limiter for public inbound leads (E5-B MVP).

Limitations (process-local / multi-worker):
- Counters live in one OS process only; they are NOT shared across gunicorn/uvicorn
  workers, multiple containers, or restarts.
- Each worker enforces its own window independently, so effective capacity scales
  roughly with worker count (N workers ≈ N × configured max).
- Acceptable for single-process / low-traffic MVP only — not distributed protection.
- Do not treat this as a substitute for edge/CDN or shared-store rate limiting.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from fastapi import Request

from app.core.exceptions import RateLimitExceededError

PUBLIC_LEADS_RATE_LIMIT_MESSAGE = "Too many requests. Please try again later."


@dataclass(frozen=True)
class RateLimitRule:
    window_seconds: int
    max_requests: int


def rate_limit_client_ip(request: Request | None) -> str:
    """Client key for public-leads rate limiting.

    Uses the ASGI peer address (``request.client.host``) only.

    ``X-Forwarded-For`` / ``Forwarded`` are intentionally ignored: there is no
    trusted-proxy allowlist mechanism yet, so honoring client-supplied forwarded
    headers would let attackers rotate spoofed IPs and bypass the limit.
    """
    if request is None or request.client is None:
        return "unknown"
    host = (request.client.host or "").strip()
    return host or "unknown"


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


# Process-wide singleton used by PublicLeadService (not shared across workers)
public_leads_rate_limiter = InMemorySlidingWindowRateLimiter()
