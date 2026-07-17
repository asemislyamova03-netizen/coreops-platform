import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import (
    ContactMethodType,
    PartyStatus,
    PartyType,
    SubscriptionStatus,
    TenantStatus,
    WorkItemParticipantRole,
)
from app.modules.auth.models import User
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.parties.models import ContactMethod, Party
from app.modules.parties.service import PartyService
from app.modules.provider.models import ProviderCompany
from app.modules.public_leads.rate_limit import (
    PUBLIC_LEADS_RATE_LIMIT_MESSAGE,
    public_leads_rate_limiter,
)
from app.modules.subscriptions.repository import SubscriptionRepository
from app.modules.subscriptions.service import SubscriptionService
from app.modules.tenants.models import Tenant
from app.modules.workflows.models import Pipeline, PipelineStage, WorkItem, WorkItemParticipant


ENDPOINT = "/api/v1/public/leads"
ALLOWED_ORIGIN = "https://www.flexity.asia"


@pytest.fixture(autouse=True)
def reset_public_leads_rate_limiter():
    public_leads_rate_limiter.reset()
    yield
    public_leads_rate_limiter.reset()


@pytest.fixture
def public_leads_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "public_leads_enabled", False)
    monkeypatch.setattr(settings, "public_leads_target_tenant_id", None)
    monkeypatch.setattr(settings, "public_leads_pipeline_id", None)
    monkeypatch.setattr(settings, "public_leads_stage_id", None)
    monkeypatch.setattr(settings, "public_leads_created_by_user_id", None)
    monkeypatch.setattr(settings, "public_leads_allowed_origins", "")
    monkeypatch.setattr(settings, "public_leads_telegram_bot_token", None)
    monkeypatch.setattr(settings, "public_leads_telegram_chat_id", None)
    monkeypatch.setattr(settings, "public_leads_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "public_leads_rate_limit_window_seconds", 600)
    monkeypatch.setattr(settings, "public_leads_rate_limit_max_requests", 5)
    monkeypatch.setattr(settings, "public_leads_rate_limit_hour_window_seconds", 3600)
    monkeypatch.setattr(settings, "public_leads_rate_limit_hour_max_requests", 20)
    return settings


@pytest.fixture
def runtime_targets(db_session: Session):
    provider = ProviderCompany(name="Flexity", slug=f"flexity-{uuid.uuid4().hex[:8]}")
    user = User(
        email=f"lead-owner-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="not-used",
        full_name="Lead Owner",
    )
    db_session.add_all([provider, user])
    db_session.flush()

    tenant = Tenant(
        provider_company_id=provider.id,
        name="Consulting Demo",
        slug=f"consulting-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.TRIAL,
    )
    db_session.add(tenant)
    db_session.flush()

    ModuleRegistryService(db_session).enable_modules_ordered(
        tenant.id,
        ["parties", "crm"],
        as_trial=True,
    )
    SubscriptionService(db_session).seed_catalog()
    subscription_repo = SubscriptionRepository(db_session)
    plan = subscription_repo.get_plan_by_code("starter")
    assert plan is not None
    subscription_repo.upsert_subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status=SubscriptionStatus.TRIAL,
    )

    pipeline = Pipeline(
        tenant_id=tenant.id,
        code="public_leads",
        name="Public leads",
        is_default=True,
    )
    db_session.add(pipeline)
    db_session.flush()
    stage = PipelineStage(
        pipeline_id=pipeline.id,
        code="new",
        name="New",
        sort_order=10,
    )
    db_session.add(stage)
    db_session.commit()

    return {
        "tenant_id": tenant.id,
        "pipeline_id": pipeline.id,
        "stage_id": stage.id,
        "user_id": user.id,
    }


def _configure_public_leads(settings, targets, *, allowed_origins=ALLOWED_ORIGIN):
    settings.public_leads_enabled = True
    settings.public_leads_target_tenant_id = str(targets["tenant_id"])
    settings.public_leads_pipeline_id = str(targets["pipeline_id"])
    settings.public_leads_stage_id = str(targets["stage_id"])
    settings.public_leads_created_by_user_id = str(targets["user_id"])
    settings.public_leads_allowed_origins = allowed_origins


def _payload(**overrides):
    payload = {
        "name": "Asem",
        "phone": "+77001234567",
        "email": "asem@example.com",
        "company": "Flexity Client",
        "preferred_channel": "telegram",
        "process_area": "content operations",
        "message": "Need a demo",
        "source_page": "https://www.flexity.asia/demo/",
        "utm_source": "insights",
        "utm_medium": "site",
        "utm_campaign": "public-demo",
        "utm_content": "hero",
        "utm_term": "automation",
        "referrer": "https://www.flexity.asia/insights/",
        "consent_accepted": True,
        "website": "",
    }
    payload.update(overrides)
    return payload


def _assert_private_response(data: dict) -> None:
    assert data["status"] == "created"
    assert data["message"] == "Lead received"
    assert "party_id" not in data
    assert "work_item_id" not in data
    assert "matches" not in data
    assert "matched_on" not in data


def _seed_party(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    display_name: str,
    email: str | None = None,
    phone: str | None = None,
) -> Party:
    party = Party(
        tenant_id=tenant_id,
        party_type=PartyType.PERSON,
        display_name=display_name,
        status=PartyStatus.ACTIVE,
        metadata_json={"party_role": "lead"},
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db_session.add(party)
    db_session.flush()
    if email:
        db_session.add(
            ContactMethod(
                tenant_id=tenant_id,
                party_id=party.id,
                method_type=ContactMethodType.EMAIL,
                value=email,
                is_primary=True,
            )
        )
    if phone:
        db_session.add(
            ContactMethod(
                tenant_id=tenant_id,
                party_id=party.id,
                method_type=ContactMethodType.PHONE,
                value=phone,
                is_primary=email is None,
            )
        )
    db_session.commit()
    return party


def test_public_leads_endpoint_disabled(client, db_session: Session, public_leads_settings):
    party_before = db_session.query(Party).count()
    wi_before = db_session.query(WorkItem).count()

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 403
    assert response.json()["detail"] == "Public lead capture is disabled"
    assert db_session.query(Party).count() == party_before
    assert db_session.query(WorkItem).count() == wi_before


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"phone": "", "email": None},
        {"message": "", "process_area": None},
        {"source_page": ""},
        {"consent_accepted": False},
    ],
)
def test_public_leads_validation_errors(
    client,
    public_leads_settings,
    runtime_targets,
    overrides,
):
    _configure_public_leads(public_leads_settings, runtime_targets)

    response = client.post(ENDPOINT, json=_payload(**overrides), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 422


def test_public_leads_honeypot_rejection(client, public_leads_settings, runtime_targets):
    _configure_public_leads(public_leads_settings, runtime_targets)

    response = client.post(
        ENDPOINT,
        json=_payload(website="spam.example"),
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 422


def test_public_leads_disallowed_origin_rejected(client, public_leads_settings, runtime_targets):
    _configure_public_leads(public_leads_settings, runtime_targets)

    response = client.post(
        ENDPOINT,
        json=_payload(),
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Origin is not allowed"


def test_public_leads_missing_runtime_config_when_enabled(client, public_leads_settings):
    public_leads_settings.public_leads_enabled = True
    public_leads_settings.public_leads_allowed_origins = ALLOWED_ORIGIN

    response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 400
    assert response.json()["detail"] == "Public lead target IDs are not configured"


def test_public_leads_success_creates_party_and_work_item(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    party_before = db_session.query(Party).count()
    wi_before = db_session.query(WorkItem).count()

    response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 201
    data = response.json()
    _assert_private_response(data)

    assert db_session.query(Party).count() == party_before + 1
    assert db_session.query(WorkItem).count() == wi_before + 1

    party = (
        db_session.query(Party)
        .filter(Party.tenant_id == runtime_targets["tenant_id"])
        .order_by(Party.created_at.desc())
        .first()
    )
    assert party is not None
    assert party.display_name == "Asem"
    assert party.metadata_json["source"] == "website_demo"
    assert party.metadata_json["form_name"] == "demo"
    assert party.metadata_json["process_area"] == "content operations"
    assert "consent_accepted_at" in party.metadata_json

    methods = db_session.query(ContactMethod).filter(ContactMethod.party_id == party.id).all()
    assert {method.method_type.value for method in methods} == {"email", "phone"}

    work_item = (
        db_session.query(WorkItem)
        .filter(WorkItem.tenant_id == runtime_targets["tenant_id"])
        .order_by(WorkItem.created_at.desc())
        .first()
    )
    assert work_item is not None
    assert work_item.pipeline_id == runtime_targets["pipeline_id"]
    assert work_item.stage_id == runtime_targets["stage_id"]
    assert work_item.primary_party_id == party.id
    assert work_item.work_item_type == "demo_request"
    assert work_item.source == "website_demo"
    assert work_item.custom_fields_json["utm_campaign"] == "public-demo"
    assert work_item.custom_fields_json["form_name"] == "demo"
    assert work_item.custom_fields_json["page_url"] == "https://www.flexity.asia/demo/"
    assert work_item.custom_fields_json["party_match"] == "none"
    assert "consent_accepted_at" in work_item.custom_fields_json

    participant = (
        db_session.query(WorkItemParticipant)
        .filter(WorkItemParticipant.work_item_id == work_item.id)
        .one()
    )
    assert participant.party_id == party.id
    assert participant.role == WorkItemParticipantRole.CLIENT


def test_public_leads_exact_email_reuses_party(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    existing = _seed_party(
        db_session,
        tenant_id=runtime_targets["tenant_id"],
        user_id=runtime_targets["user_id"],
        display_name="Existing Contact",
        email="asem@example.com",
        phone="+77009998877",
    )
    party_before = db_session.query(Party).count()

    response = client.post(
        ENDPOINT,
        json=_payload(phone="+77001110000", email="asem@example.com", name="Asem New"),
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 201
    _assert_private_response(response.json())
    assert db_session.query(Party).count() == party_before

    work_item = (
        db_session.query(WorkItem)
        .filter(WorkItem.tenant_id == runtime_targets["tenant_id"])
        .order_by(WorkItem.created_at.desc())
        .first()
    )
    assert work_item is not None
    assert work_item.primary_party_id == existing.id
    assert work_item.source == "website_demo"
    assert work_item.custom_fields_json["party_match"] == "exact"
    assert "email" in work_item.custom_fields_json["matched_on"]
    assert "matched existing contact" in work_item.description.lower()


def test_public_leads_exact_phone_reuses_party(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    existing = _seed_party(
        db_session,
        tenant_id=runtime_targets["tenant_id"],
        user_id=runtime_targets["user_id"],
        display_name="Phone Contact",
        phone="+77001234567",
    )
    party_before = db_session.query(Party).count()

    response = client.post(
        ENDPOINT,
        json=_payload(email="other@example.com", phone="+7 (700) 123-45-67"),
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 201
    _assert_private_response(response.json())
    assert db_session.query(Party).count() == party_before

    work_item = (
        db_session.query(WorkItem)
        .filter(WorkItem.tenant_id == runtime_targets["tenant_id"])
        .order_by(WorkItem.created_at.desc())
        .first()
    )
    assert work_item is not None
    assert work_item.primary_party_id == existing.id
    assert work_item.custom_fields_json["party_match"] == "exact"
    assert "phone" in work_item.custom_fields_json["matched_on"]


def test_public_leads_weak_name_creates_party_with_candidates(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    existing = _seed_party(
        db_session,
        tenant_id=runtime_targets["tenant_id"],
        user_id=runtime_targets["user_id"],
        display_name="Asem Weak Candidate",
        email="other-weak@example.com",
        phone="+77005554433",
    )
    party_before = db_session.query(Party).count()

    response = client.post(
        ENDPOINT,
        json=_payload(
            name="Asem",
            email="brand-new-weak@example.com",
            phone="+77006667788",
        ),
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 201
    _assert_private_response(response.json())
    assert db_session.query(Party).count() == party_before + 1

    work_item = (
        db_session.query(WorkItem)
        .filter(WorkItem.tenant_id == runtime_targets["tenant_id"])
        .order_by(WorkItem.created_at.desc())
        .first()
    )
    assert work_item is not None
    assert work_item.primary_party_id != existing.id
    assert work_item.custom_fields_json["party_match"] == "weak_only"
    assert work_item.custom_fields_json["possible_match_count"] >= 1
    assert str(existing.id) in work_item.custom_fields_json["possible_match_party_ids"]


def test_public_leads_invalid_configured_tenant_fails_closed(
    client,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    public_leads_settings.public_leads_target_tenant_id = str(uuid.uuid4())

    response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 400
    assert response.json()["detail"] == "Public lead target tenant is invalid"


def test_public_leads_invalid_configured_pipeline_fails_closed(
    client,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    public_leads_settings.public_leads_pipeline_id = str(uuid.uuid4())

    response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 400
    assert response.json()["detail"] == "Public lead target pipeline is invalid"


def test_public_leads_invalid_configured_stage_fails_closed(
    client,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    public_leads_settings.public_leads_stage_id = str(uuid.uuid4())

    response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 400
    assert response.json()["detail"] == "Public lead target stage is invalid"


def test_public_leads_invalid_configured_created_by_user_fails_closed(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    public_leads_settings.public_leads_created_by_user_id = str(uuid.uuid4())

    party_count_before = db_session.query(Party).count()
    work_item_count_before = db_session.query(WorkItem).count()

    response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 400
    assert response.json()["detail"] == "Public lead created-by user is invalid"
    assert db_session.query(Party).count() == party_count_before
    assert db_session.query(WorkItem).count() == work_item_count_before


def test_public_leads_inactive_created_by_user_fails_closed(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    user = db_session.get(User, runtime_targets["user_id"])
    assert user is not None
    user.is_active = False
    db_session.commit()

    party_count_before = db_session.query(Party).count()
    work_item_count_before = db_session.query(WorkItem).count()

    response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 400
    assert response.json()["detail"] == "Public lead created-by user is invalid"
    assert db_session.query(Party).count() == party_count_before
    assert db_session.query(WorkItem).count() == work_item_count_before


def test_public_leads_notification_failure_does_not_rollback(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    public_leads_settings.public_leads_telegram_bot_token = "token"
    public_leads_settings.public_leads_telegram_chat_id = "chat"
    wi_before = db_session.query(WorkItem).count()

    with patch(
        "app.modules.public_leads.notifications.PublicLeadTelegramNotifier.send",
        side_effect=RuntimeError("telegram failed"),
    ):
        response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 201
    _assert_private_response(response.json())
    assert db_session.query(WorkItem).count() == wi_before + 1


def test_public_leads_disabled_does_not_increment_rate_limiter(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    public_leads_settings.public_leads_rate_limit_max_requests = 2
    public_leads_settings.public_leads_rate_limit_hour_max_requests = 100

    # Disabled posts must not consume quota
    for _ in range(5):
        response = client.post(
            ENDPOINT,
            json=_payload(),
            headers={"Origin": ALLOWED_ORIGIN, "X-Forwarded-For": "203.0.113.10"},
        )
        assert response.status_code == 403

    _configure_public_leads(public_leads_settings, runtime_targets)
    party_before = db_session.query(Party).count()

    ok1 = client.post(
        ENDPOINT,
        json=_payload(email="rl1@example.com", phone="+77001110001"),
        headers={"Origin": ALLOWED_ORIGIN, "X-Forwarded-For": "203.0.113.10"},
    )
    ok2 = client.post(
        ENDPOINT,
        json=_payload(email="rl2@example.com", phone="+77001110002"),
        headers={"Origin": ALLOWED_ORIGIN, "X-Forwarded-For": "203.0.113.10"},
    )
    assert ok1.status_code == 201
    assert ok2.status_code == 201
    assert db_session.query(Party).count() == party_before + 2


def test_public_leads_rate_limit_returns_429(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    public_leads_settings.public_leads_rate_limit_max_requests = 2
    public_leads_settings.public_leads_rate_limit_hour_max_requests = 100
    headers = {"Origin": ALLOWED_ORIGIN, "X-Forwarded-For": "198.51.100.20"}

    assert client.post(ENDPOINT, json=_payload(email="a1@example.com", phone="+77002110001"), headers=headers).status_code == 201
    assert client.post(ENDPOINT, json=_payload(email="a2@example.com", phone="+77002110002"), headers=headers).status_code == 201

    party_before = db_session.query(Party).count()
    wi_before = db_session.query(WorkItem).count()

    with patch.object(PartyService, "match_parties") as match_mock:
        blocked = client.post(
            ENDPOINT,
            json=_payload(email="a3@example.com", phone="+77002110003"),
            headers=headers,
        )
        match_mock.assert_not_called()

    assert blocked.status_code == 429
    body = blocked.json()
    assert body["detail"] == PUBLIC_LEADS_RATE_LIMIT_MESSAGE
    assert "party_id" not in body
    assert "matches" not in str(body).lower()
    assert db_session.query(Party).count() == party_before
    assert db_session.query(WorkItem).count() == wi_before


def test_public_leads_rate_limit_separate_ips(
    client,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    public_leads_settings.public_leads_rate_limit_max_requests = 1
    public_leads_settings.public_leads_rate_limit_hour_max_requests = 100

    ip_a = {"Origin": ALLOWED_ORIGIN, "X-Forwarded-For": "198.51.100.30"}
    ip_b = {"Origin": ALLOWED_ORIGIN, "X-Forwarded-For": "198.51.100.31"}

    assert (
        client.post(
            ENDPOINT,
            json=_payload(email="ip-a@example.com", phone="+77003110001"),
            headers=ip_a,
        ).status_code
        == 201
    )
    assert (
        client.post(
            ENDPOINT,
            json=_payload(email="ip-a2@example.com", phone="+77003110002"),
            headers=ip_a,
        ).status_code
        == 429
    )
    assert (
        client.post(
            ENDPOINT,
            json=_payload(email="ip-b@example.com", phone="+77003110003"),
            headers=ip_b,
        ).status_code
        == 201
    )
