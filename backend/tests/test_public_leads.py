import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import SubscriptionStatus, TenantStatus, WorkItemParticipantRole
from app.modules.auth.models import User
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.parties.models import ContactMethod, Party
from app.modules.provider.models import ProviderCompany
from app.modules.subscriptions.repository import SubscriptionRepository
from app.modules.subscriptions.service import SubscriptionService
from app.modules.tenants.models import Tenant
from app.modules.workflows.models import Pipeline, PipelineStage, WorkItem, WorkItemParticipant


ENDPOINT = "/api/v1/public/leads"
ALLOWED_ORIGIN = "https://www.flexity.asia"


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


def test_public_leads_endpoint_disabled(client, public_leads_settings):
    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 403
    assert response.json()["detail"] == "Public lead capture is disabled"


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

    response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 201
    data = response.json()

    party = db_session.get(Party, uuid.UUID(data["party_id"]))
    assert party is not None
    assert party.tenant_id == runtime_targets["tenant_id"]
    assert party.display_name == "Asem"
    assert party.metadata_json["source"] == "public_demo_form"
    assert party.metadata_json["process_area"] == "content operations"

    methods = db_session.query(ContactMethod).filter(ContactMethod.party_id == party.id).all()
    assert {method.method_type.value for method in methods} == {"email", "phone"}

    work_item = db_session.get(WorkItem, uuid.UUID(data["work_item_id"]))
    assert work_item is not None
    assert work_item.tenant_id == runtime_targets["tenant_id"]
    assert work_item.pipeline_id == runtime_targets["pipeline_id"]
    assert work_item.stage_id == runtime_targets["stage_id"]
    assert work_item.primary_party_id == party.id
    assert work_item.work_item_type == "demo_request"
    assert work_item.source == "public_demo_form"
    assert work_item.custom_fields_json["utm_campaign"] == "public-demo"

    participant = (
        db_session.query(WorkItemParticipant)
        .filter(WorkItemParticipant.work_item_id == work_item.id)
        .one()
    )
    assert participant.party_id == party.id
    assert participant.role == WorkItemParticipantRole.CLIENT


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


def test_public_leads_notification_failure_does_not_rollback(
    client,
    db_session: Session,
    public_leads_settings,
    runtime_targets,
):
    _configure_public_leads(public_leads_settings, runtime_targets)
    public_leads_settings.public_leads_telegram_bot_token = "token"
    public_leads_settings.public_leads_telegram_chat_id = "chat"

    with patch(
        "app.modules.public_leads.notifications.PublicLeadTelegramNotifier.send",
        side_effect=RuntimeError("telegram failed"),
    ):
        response = client.post(ENDPOINT, json=_payload(), headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 201
    data = response.json()
    assert db_session.get(Party, uuid.UUID(data["party_id"])) is not None
    assert db_session.get(WorkItem, uuid.UUID(data["work_item_id"])) is not None
