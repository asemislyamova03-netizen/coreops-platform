"""Unit tests for public leads in-memory rate limiter."""

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
