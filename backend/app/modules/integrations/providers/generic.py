from app.modules.integrations.providers.base import (
    IntegrationAdapter,
    ProviderSyncResult,
    ProviderTestResult,
)


class GenericCrmAdapter(IntegrationAdapter):
    provider_code = "generic_crm"

    def test_connection(self, credentials: dict, settings: dict) -> ProviderTestResult:
        base_url = credentials.get("base_url") or settings.get("base_url")
        if not base_url:
            return ProviderTestResult(success=False, message="base_url is required")
        return ProviderTestResult(
            success=True,
            message="Generic CRM endpoint reachable (mock)",
            details={"base_url": base_url},
        )

    def sync(
        self,
        *,
        credentials: dict,
        settings: dict,
        job_type: str,
    ) -> ProviderSyncResult:
        return ProviderSyncResult(
            success=True,
            message=f"Generic CRM mock sync ({job_type})",
            entities_synced=1,
            references_created=1,
            details={"mock": True},
        )


class MockAccountingAdapter(IntegrationAdapter):
    provider_code = "mock_accounting"

    def test_connection(self, credentials: dict, settings: dict) -> ProviderTestResult:
        return ProviderTestResult(success=True, message="Mock accounting connection OK")

    def sync(
        self,
        *,
        credentials: dict,
        settings: dict,
        job_type: str,
    ) -> ProviderSyncResult:
        return ProviderSyncResult(
            success=True,
            message=f"Mock accounting sync ({job_type})",
            entities_synced=2,
            references_created=2,
            details={"mock": True},
        )
