"""Unit tests for public leads in-memory rate limiter.

The limiter is process-local only: each worker process has its own buckets.
These unit tests cover single-process behavior; they do not claim distributed
multi-worker enforcement.
"""

import pytest

from app.core.exceptions import RateLimitExceededError
from app.modules.public_leads.rate_limit import (
    PUBLIC_LEADS_RATE_LIMIT_MESSAGE,
    InMemorySlidingWindowRateLimiter,
    RateLimitRule,
)


def test_rate_limiter_allows_under_limit_then_blocks():
    limiter = InMemorySlidingWindowRateLimiter()
    rules = [RateLimitRule(window_seconds=60, max_requests=2)]

    limiter.check_and_increment("1.1.1.1", rules)
    limiter.check_and_increment("1.1.1.1", rules)
    with pytest.raises(RateLimitExceededError) as exc:
        limiter.check_and_increment("1.1.1.1", rules)
    assert str(exc.value) == PUBLIC_LEADS_RATE_LIMIT_MESSAGE


def test_rate_limiter_separate_keys():
    limiter = InMemorySlidingWindowRateLimiter()
    rules = [RateLimitRule(window_seconds=60, max_requests=1)]
    limiter.check_and_increment("a", rules)
    limiter.check_and_increment("b", rules)
    with pytest.raises(RateLimitExceededError):
        limiter.check_and_increment("a", rules)


def test_rate_limiter_reset_clears_buckets():
    limiter = InMemorySlidingWindowRateLimiter()
    rules = [RateLimitRule(window_seconds=60, max_requests=1)]
    limiter.check_and_increment("x", rules)
    limiter.reset()
    limiter.check_and_increment("x", rules)


def test_rate_limit_client_ip_ignores_xff():
    from types import SimpleNamespace

    from app.modules.public_leads.rate_limit import rate_limit_client_ip

    request = SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.10"),
        headers={"x-forwarded-for": "198.51.100.1, 10.0.0.1"},
    )
    assert rate_limit_client_ip(request) == "203.0.113.10"


def test_rate_limit_client_ip_unknown_without_peer():
    from types import SimpleNamespace

    from app.modules.public_leads.rate_limit import rate_limit_client_ip

    assert rate_limit_client_ip(SimpleNamespace(client=None)) == "unknown"
    assert rate_limit_client_ip(None) == "unknown"
