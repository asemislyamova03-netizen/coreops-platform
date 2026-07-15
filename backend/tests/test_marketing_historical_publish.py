import inspect
import uuid

from app.modules.marketing.enums import MarketingPackStatus
from app.modules.marketing.models import MarketingPublicationPack
from app.modules.marketing.service.historical_publish import MarketingHistoricalPublishService


REGISTER_PAYLOAD = {
    "email": "historical-owner@example.com",
    "password": "securepass123",
    "full_name": "Historical Owner",
    "company_name": "Historical Provider",
    "company_slug": "historical-provider",
}


def _setup_marketing_tenant(client, *, suffix: str) -> tuple[dict[str, str], str]:
    payload = {
        **REGISTER_PAYLOAD,
        "email": f"historical-{suffix}@example.com",
        "company_name": f"Historical Provider {suffix}",
        "company_slug": f"historical-provider-{suffix}",
    }
    registration = client.post("/api/v1/auth/register", json=payload)
    assert registration.status_code == 201, registration.text
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": f"Historical {suffix}", "slug": f"historical-{suffix}"},
        headers=headers,
    ).json()["id"]
    client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers)
    return {**headers, "X-Tenant-ID": tenant_id}, tenant_id


def _create_pack(client, headers, *, slug: str) -> str:
    response = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": f"Historical {slug}", "slug": slug},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _record(client, headers, pack_id: str, channels: list[str], **extra):
    return client.post(
        f"/api/v1/marketing/packs/{pack_id}/record-historical-publish",
        headers=headers,
        json={"channels": channels, "evidence_ref": "archive-2026-01", **extra},
    )


def test_historical_telegram_and_instagram_marks_published_without_workflow_change(client):
    headers, _ = _setup_marketing_tenant(client, suffix="tg-ig")
    pack_id = _create_pack(client, headers, slug="historical-tg-ig")

    response = _record(client, headers, pack_id, ["telegram", "instagram"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["logs_created"] == 2
    assert body["publish_status"] == "published"
    assert body["pack_status"] == "draft"
    assert body["approval_status"] == "draft"
    assert {item["channel"] for item in body["channel_results"]} == {"telegram", "instagram"}

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers).json()
    assert detail["status"] == "draft"
    assert detail["approval_status"] == "draft"
    assert detail["publish_status"] == "published"
    assert {log["action"] for log in detail["publish_logs"]} == {"historical_record"}
    assert {log["status"] for log in detail["publish_logs"]} == {"recorded"}


def test_historical_telegram_only_marks_partial(client):
    headers, _ = _setup_marketing_tenant(client, suffix="tg")
    pack_id = _create_pack(client, headers, slug="historical-tg")

    response = _record(client, headers, pack_id, ["telegram"])

    assert response.status_code == 200, response.text
    assert response.json()["publish_status"] == "partial"


def test_historical_instagram_only_marks_partial(client):
    headers, _ = _setup_marketing_tenant(client, suffix="ig")
    pack_id = _create_pack(client, headers, slug="historical-ig")

    response = _record(client, headers, pack_id, ["instagram"])

    assert response.status_code == 200, response.text
    assert response.json()["publish_status"] == "partial"


def test_historical_insights_site_only_marks_partial(client):
    headers, _ = _setup_marketing_tenant(client, suffix="insights")
    pack_id = _create_pack(client, headers, slug="historical-insights")

    response = _record(client, headers, pack_id, ["insights_site"])

    assert response.status_code == 200, response.text
    assert response.json()["publish_status"] == "partial"


def test_historical_record_is_idempotent_for_same_evidence(client):
    headers, _ = _setup_marketing_tenant(client, suffix="idempotent")
    pack_id = _create_pack(client, headers, slug="historical-idempotent")

    first = _record(client, headers, pack_id, ["telegram", "instagram"])
    second = _record(client, headers, pack_id, ["telegram", "instagram"])

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["logs_created"] == 0
    assert second.json()["skipped_existing"] == 2
    assert {item["status"] for item in second.json()["channel_results"]} == {"existing"}
    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers).json()
    assert len(detail["publish_logs"]) == 2


def test_historical_later_missing_target_channel_rolls_up_to_published(client):
    headers, _ = _setup_marketing_tenant(client, suffix="rollup")
    pack_id = _create_pack(client, headers, slug="historical-rollup")

    first = _record(client, headers, pack_id, ["telegram"])
    second = _record(client, headers, pack_id, ["instagram"])

    assert first.json()["publish_status"] == "partial"
    assert second.status_code == 200
    assert second.json()["publish_status"] == "published"


def test_historical_needs_review_log_does_not_complete_later_rollup(client):
    headers, _ = _setup_marketing_tenant(client, suffix="needs-review")
    pack_id = _create_pack(client, headers, slug="historical-needs-review")

    first = _record(client, headers, pack_id, ["telegram"], needs_review=True)
    second = _record(client, headers, pack_id, ["instagram"])

    assert first.status_code == 200
    assert first.json()["publish_status"] == "partial"
    assert second.status_code == 200
    assert second.json()["publish_status"] == "partial"


def test_historical_record_without_evidence_is_idempotent_by_published_date(client):
    headers, _ = _setup_marketing_tenant(client, suffix="fallback-idempotency")
    pack_id = _create_pack(client, headers, slug="historical-fallback-idempotency")
    payload = {
        "channels": ["telegram"],
        "evidence_ref": None,
        "published_at": "2025-01-02T12:00:00Z",
    }

    first = client.post(
        f"/api/v1/marketing/packs/{pack_id}/record-historical-publish",
        headers=headers,
        json=payload,
    )
    second = client.post(
        f"/api/v1/marketing/packs/{pack_id}/record-historical-publish",
        headers=headers,
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["logs_created"] == 0
    assert second.json()["skipped_existing"] == 1


def test_historical_unknown_channel_is_rejected(client):
    headers, _ = _setup_marketing_tenant(client, suffix="invalid")
    pack_id = _create_pack(client, headers, slug="historical-invalid")

    response = _record(client, headers, pack_id, ["linkedin"])

    assert response.status_code == 422


def test_historical_record_returns_404_for_missing_or_other_tenant_pack(client):
    headers_a, _ = _setup_marketing_tenant(client, suffix="tenant-a")
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "Historical tenant B", "slug": "historical-tenant-b"},
        headers=headers_a,
    ).json()["id"]
    client.post(f"/api/v1/tenants/{tenant_b}/modules/parties/enable", headers=headers_a)
    client.post(f"/api/v1/tenants/{tenant_b}/modules/marketing/enable", headers=headers_a)
    headers_b = {**headers_a, "X-Tenant-ID": tenant_b}
    pack_id = _create_pack(client, headers_a, slug="historical-private")

    missing = _record(client, headers_a, str(uuid.uuid4()), ["telegram"])
    cross_tenant = _record(client, headers_b, pack_id, ["telegram"])

    assert missing.status_code == 404
    assert cross_tenant.status_code == 404


def test_historical_record_blocks_publishing_pack_without_writes(client, db_session):
    headers, _ = _setup_marketing_tenant(client, suffix="publishing")
    pack_id = _create_pack(client, headers, slug="historical-publishing")
    pack = db_session.get(MarketingPublicationPack, uuid.UUID(pack_id))
    pack.status = MarketingPackStatus.PUBLISHING
    db_session.flush()

    response = _record(client, headers, pack_id, ["telegram"])

    assert response.status_code == 409
    db_session.refresh(pack)
    assert pack.status == MarketingPackStatus.PUBLISHING
    assert pack.publish_status.value == "not_started"
    assert pack.publish_logs == []


def test_historical_publish_service_has_no_outbound_publisher_or_margosya_dependency():
    source = inspect.getsource(MarketingHistoricalPublishService).lower()

    assert "margosya" not in source
    assert "publish_telegram" not in source
    assert "publish_instagram" not in source
