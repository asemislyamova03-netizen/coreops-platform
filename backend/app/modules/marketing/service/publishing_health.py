"""Publishing connection health-check port (M8-C1a)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.core.secrets.ref import SecretRef
from app.modules.marketing.enums import MarketingPublishingProvider


class HealthCheckStatus(str, Enum):
    UNCHECKED = "unchecked"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    status: HealthCheckStatus
    error_code: str | None = None


class PublishingHealthCheckPort(Protocol):
    def check_connection_health(
        self,
        *,
        provider: MarketingPublishingProvider,
        secret_ref: SecretRef,
        scopes: list[str],
    ) -> HealthCheckResult: ...


class UncheckedHealthCheckStub:
    """No-op health checker. Must never mark token_status=valid."""

    def check_connection_health(
        self,
        *,
        provider: MarketingPublishingProvider,
        secret_ref: SecretRef,
        scopes: list[str],
    ) -> HealthCheckResult:
        # Explicitly ignore inputs; stub cannot validate provider credentials.
        _ = (provider, secret_ref, scopes)
        return HealthCheckResult(status=HealthCheckStatus.UNCHECKED, error_code="unchecked_health")
