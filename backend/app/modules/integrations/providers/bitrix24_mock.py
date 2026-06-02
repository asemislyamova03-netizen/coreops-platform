from app.modules.integrations.providers.base import (
    IntegrationAdapter,
    ProviderSyncResult,
    ProviderTestResult,
)


class Bitrix24MockAdapter(IntegrationAdapter):
    provider_code = "bitrix24"

    def test_connection(self, credentials: dict, settings: dict) -> ProviderTestResult:
        portal = credentials.get("portal_url") or settings.get("portal_url")
        if not portal:
            return ProviderTestResult(
                success=False,
                message="portal_url is required in credentials or settings",
            )
        return ProviderTestResult(
            success=True,
            message="Mock Bitrix24 connection OK",
            details={"portal_url": portal, "mock": True},
        )

    def sync(
        self,
        *,
        credentials: dict,
        settings: dict,
        job_type: str,
    ) -> ProviderSyncResult:
        portal = credentials.get("portal_url") or settings.get("portal_url", "https://example.bitrix24.ru")
        return ProviderSyncResult(
            success=True,
            message=f"Mock sync completed ({job_type})",
            entities_synced=3,
            references_created=2,
            references_updated=1,
            details={
                "portal_url": portal,
                "mock_entities": [
                    {"external_entity_type": "deal", "external_id": "MOCK-DEAL-1"},
                    {"external_entity_type": "contact", "external_id": "MOCK-CONTACT-1"},
                    {"external_entity_type": "company", "external_id": "MOCK-COMPANY-1"},
                ],
            },
        )
