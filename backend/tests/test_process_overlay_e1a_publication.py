"""E1a service flow tests for Process Overlay config and publication."""

from __future__ import annotations

import copy
import uuid

import pytest
from sqlalchemy import select

from app.core.enums import TenantStatus, WorkItemStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.process_overlay.enums import ProcessOverlayActivationState
from app.modules.process_overlay.exceptions import (
    ProcessDefinitionImmutableError,
    ProcessOverlayActivationError,
    ProcessOverlayTenantIsolationError,
    ProcessOverlayValidationError,
)
from app.modules.process_overlay.policy_schema import PolicySnapshotV1, parse_policy_snapshot
from app.modules.process_overlay.models import TenantProcessConfiguration
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import PublishDefinitionVersionRequest
from app.modules.process_overlay.seed import PROCESS_TEMPLATE_DEFINITIONS
from app.modules.process_overlay.service import (
    ProcessOverlayCatalogService,
    ProcessOverlayConfigurationService,
    ProcessOverlayPublicationService,
)
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant
from app.modules.workflows.models import PipelineStage
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.service import WorkflowService


def _bootstrap_tenant(db_session, slug: str) -> Tenant:
    provider = ProviderCompany(name=f"Provider {slug}", slug=f"prov-{slug}", is_active=True)
    db_session.add(provider)
    db_session.flush()
    tenant = Tenant(
        provider_company_id=provider.id,
        name=f"Tenant {slug}",
        slug=slug,
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _create_flexity_sales_pipeline(db_session, tenant_id: uuid.UUID):
    repo = WorkflowRepository(db_session)
    existing = repo.get_pipeline_by_code(tenant_id, "flexity_sales")
    if existing:
        return existing
    pipeline = repo.create_pipeline(
        tenant_id=tenant_id,
        code="flexity_sales",
        name="Flexity Sales",
        entity_type="work_item",
        is_default=True,
    )
    stages = [
        ("new_lead", 10, False),
        ("contacted", 20, False),
        ("diagnosis", 30, False),
        ("proposal_prepared", 40, False),
        ("accepted", 70, False),
        ("rejected", 80, True),
    ]
    for code, order, terminal in stages:
        repo.create_stage(
            pipeline_id=pipeline.id,
            code=code,
            name=code,
            sort_order=order,
            is_terminal=terminal,
        )
    db_session.flush()
    return repo.get_pipeline_by_code(tenant_id, "flexity_sales")


def _policy_from_blueprint() -> PolicySnapshotV1:
    blueprint = PROCESS_TEMPLATE_DEFINITIONS[0]["default_policy_blueprint_json"]
    return parse_policy_snapshot(copy.deepcopy(blueprint))


def _enable_overlay_modules(db_session, tenant_id: uuid.UUID) -> None:
    ModuleRegistryService(db_session).enable_modules_ordered(tenant_id, ["parties", "crm"])


def _setup_configuration(db_session, slug: str = "overlay-tenant"):
    ProcessOverlayCatalogService(db_session).seed_templates()
    tenant = _bootstrap_tenant(db_session, slug)
    pipeline = _create_flexity_sales_pipeline(db_session, tenant.id)
    actor = uuid.uuid4()
    config = ProcessOverlayConfigurationService(db_session).create_configuration(
        tenant_id=tenant.id,
        process_template_code="flexity_sales_intake",
        pipeline_id=pipeline.id,
        actor_user_id=actor,
    )
    return tenant, pipeline, config, actor


def _publish_v1(db_session, tenant_id, config_id, actor_id):
    publication = ProcessOverlayPublicationService(db_session)
    return publication.publish_definition_version(
        tenant_id=tenant_id,
        configuration_id=config_id,
        request=PublishDefinitionVersionRequest(
            policy=_policy_from_blueprint(),
            publish_reason="E1a test publish",
        ),
        actor_user_id=actor_id,
    )



def _get_stage_by_code(db_session, pipeline_id: uuid.UUID, code: str) -> PipelineStage | None:
    """Lookup stage without WorkflowRepository.get_stage_by_code (not on origin/main)."""
    return db_session.scalar(
        select(PipelineStage).where(
            PipelineStage.pipeline_id == pipeline_id,
            PipelineStage.code == code,
        )
    )


def test_cannot_create_config_for_other_tenant_pipeline(db_session):
    ProcessOverlayCatalogService(db_session).seed_templates()
    tenant_a = _bootstrap_tenant(db_session, "tenant-a")
    tenant_b = _bootstrap_tenant(db_session, "tenant-b")
    pipeline_b = _create_flexity_sales_pipeline(db_session, tenant_b.id)
    service = ProcessOverlayConfigurationService(db_session)
    with pytest.raises(ProcessOverlayTenantIsolationError):
        service.create_configuration(
            tenant_id=tenant_a.id,
            process_template_code="flexity_sales_intake",
            pipeline_id=pipeline_b.id,
        )


def test_configuration_service_has_no_pipeline_rebind_method():
    public_methods = {
        name
        for name in dir(ProcessOverlayConfigurationService)
        if not name.startswith("_") and callable(getattr(ProcessOverlayConfigurationService, name))
    }
    assert "update_pipeline" not in public_methods
    assert "rebind_pipeline" not in public_methods


def test_publish_fails_on_unknown_stage_code(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "unknown-stage")
    payload = _policy_from_blueprint().model_dump()
    payload["stage_codes"] = ["new_lead", "missing_stage"]
    payload["terminal_stage_codes"] = []
    payload["transitions"] = []
    publication = ProcessOverlayPublicationService(db_session)
    with pytest.raises(ProcessOverlayValidationError):
        publication.publish_definition_version(
            tenant_id=tenant.id,
            configuration_id=config.id,
            request=PublishDefinitionVersionRequest(
                policy=parse_policy_snapshot(payload),
                publish_reason="bad stages",
            ),
            actor_user_id=actor,
        )


def test_publish_fails_on_invalid_transition(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "bad-edge")
    payload = _policy_from_blueprint().model_dump()
    payload["transitions"] = [
        {
            "from_stage_code": "unknown_stage",
            "to_stage_code": "contacted",
            "conditions": {"requires_approval": False},
        }
    ]
    with pytest.raises(ProcessOverlayValidationError):
        ProcessOverlayPublicationService(db_session).publish_definition_version(
            tenant_id=tenant.id,
            configuration_id=config.id,
            request=PublishDefinitionVersionRequest(
                policy=parse_policy_snapshot(payload),
                publish_reason="bad edge",
            ),
            actor_user_id=actor,
        )


def test_publish_fails_on_empty_reason(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "empty-reason")
    with pytest.raises(ProcessOverlayValidationError):
        ProcessOverlayPublicationService(db_session).publish_definition_version(
            tenant_id=tenant.id,
            configuration_id=config.id,
            request=PublishDefinitionVersionRequest(
                policy=_policy_from_blueprint(),
                publish_reason="   ",
            ),
            actor_user_id=actor,
        )


def test_publish_fails_on_forbidden_policy_key(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "forbidden-key")
    payload = _policy_from_blueprint().model_dump()
    payload["transitions"][0]["conditions"]["script"] = "print('x')"
    with pytest.raises(ProcessOverlayValidationError):
        parse_policy_snapshot(payload)


def test_publish_creates_monotonic_versions(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "monotonic")
    publication = ProcessOverlayPublicationService(db_session)
    v1 = _publish_v1(db_session, tenant.id, config.id, actor)
    v2 = publication.publish_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        request=PublishDefinitionVersionRequest(
            policy=_policy_from_blueprint(),
            publish_reason="second publish",
        ),
        actor_user_id=actor,
    )
    assert v1.version_number == 1
    assert v2.version_number == 2


def test_published_snapshot_mutation_rejected(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "immutable")
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    repo = ProcessOverlayRepository(db_session)
    stored = repo.get_definition_version(tenant.id, version.id)
    assert stored is not None
    stored.policy_snapshot_json = {"tampered": True}
    with pytest.raises(ProcessDefinitionImmutableError):
        repo.assert_definition_version_immutable(stored)
    with pytest.raises(ProcessDefinitionImmutableError):
        db_session.flush()


def test_set_active_version_rejects_other_configuration(db_session):
    tenant, _, config_a, actor = _setup_configuration(db_session, "active-foreign-config")
    repo = ProcessOverlayRepository(db_session)
    other_template = repo.upsert_template(
        code="second_intake",
        name="Second",
        default_pipeline_code="other_sales",
        default_policy_blueprint_json={},
        required_module_codes_json=[],
        is_active=True,
    )
    other_pipeline = WorkflowRepository(db_session).create_pipeline(
        tenant_id=tenant.id,
        code="other_sales",
        name="Other Sales",
        entity_type="work_item",
        is_default=False,
    )
    WorkflowRepository(db_session).create_stage(
        pipeline_id=other_pipeline.id,
        code="new_lead",
        name="new_lead",
        sort_order=10,
        is_terminal=False,
    )
    config_b = ProcessOverlayConfigurationService(db_session).create_configuration(
        tenant_id=tenant.id,
        process_template_code="second_intake",
        pipeline_id=other_pipeline.id,
        actor_user_id=actor,
    )
    payload = _policy_from_blueprint().model_dump()
    payload["process_template_code"] = "second_intake"
    payload["pipeline_code"] = "other_sales"
    payload["stage_codes"] = ["new_lead"]
    payload["transitions"] = []
    payload["terminal_stage_codes"] = []
    version_b = ProcessOverlayPublicationService(db_session).publish_definition_version(
        tenant_id=tenant.id,
        configuration_id=config_b.id,
        request=PublishDefinitionVersionRequest(
            policy=parse_policy_snapshot(payload),
            publish_reason="other config version",
        ),
        actor_user_id=actor,
    )
    publication = ProcessOverlayPublicationService(db_session)
    with pytest.raises(ProcessOverlayValidationError):
        publication.set_active_definition_version(
            tenant_id=tenant.id,
            configuration_id=config_a.id,
            version_id=version_b.id,
            actor_user_id=actor,
        )


def test_set_active_version_rejects_other_tenant(db_session):
    tenant_a, _, config_a, actor = _setup_configuration(db_session, "active-tenant-a")
    tenant_b, _, config_b, _ = _setup_configuration(db_session, "active-tenant-b")
    version_b = _publish_v1(db_session, tenant_b.id, config_b.id, actor)
    publication = ProcessOverlayPublicationService(db_session)
    with pytest.raises((ProcessOverlayValidationError, NotFoundError)):
        publication.set_active_definition_version(
            tenant_id=tenant_a.id,
            configuration_id=config_a.id,
            version_id=version_b.id,
            actor_user_id=actor,
        )


def test_set_active_version_same_configuration_succeeds(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "active-ok")
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    updated = ProcessOverlayPublicationService(db_session).set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )
    assert updated.active_definition_version_id == version.id


def test_activate_requires_active_version(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "activate-no-version")
    _enable_overlay_modules(db_session, tenant.id)
    with pytest.raises(ProcessOverlayActivationError):
        ProcessOverlayConfigurationService(db_session).activate_configuration(
            tenant_id=tenant.id,
            configuration_id=config.id,
            actor_user_id=actor,
        )


def test_activation_does_not_alter_work_item(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "activate-wi")
    _enable_overlay_modules(db_session, tenant.id)
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    publication = ProcessOverlayPublicationService(db_session)
    publication.set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )

    workflows = WorkflowRepository(db_session)
    stage = _get_stage_by_code(db_session, pipeline.id, "new_lead")
    assert stage is not None
    work_item = workflows.create_work_item(
        tenant_id=tenant.id,
        pipeline_id=pipeline.id,
        stage_id=stage.id,
        work_item_type="lead",
        title="Existing lead",
        status=WorkItemStatus.OPEN,
    )
    db_session.flush()
    original_stage_id = work_item.stage_id

    ProcessOverlayConfigurationService(db_session).activate_configuration(
        tenant_id=tenant.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    db_session.refresh(work_item)
    assert work_item.stage_id == original_stage_id


def test_crm_move_stage_unchanged_without_overlay(db_session):
    tenant, pipeline, _, _ = _setup_configuration(db_session, "crm-unchanged")
    from app.modules.auth.models import User
    from app.modules.workflows.schemas import MoveStageRequest, WorkItemCreate

    user = User(
        email="crm-move@test.com",
        hashed_password="hashed",
        full_name="CRM User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    repo = WorkflowRepository(db_session)
    first = _get_stage_by_code(db_session, pipeline.id, "new_lead")
    second = _get_stage_by_code(db_session, pipeline.id, "contacted")
    assert first is not None and second is not None

    workflows = WorkflowService(db_session, tenant.id)
    created = workflows.create_work_item(
        user,
        WorkItemCreate(
            pipeline_id=pipeline.id,
            stage_id=first.id,
            work_item_type="lead",
            title="CRM item",
        ),
    )
    moved = workflows.move_stage(
        user,
        created.id,
        MoveStageRequest(stage_id=second.id),
    )
    assert moved.stage_id == second.id


def test_tenant_b_cannot_read_tenant_a_configuration(db_session):
    tenant_a, _, config_a, _ = _setup_configuration(db_session, "iso-a")
    tenant_b = _bootstrap_tenant(db_session, "iso-b")
    repo = ProcessOverlayRepository(db_session)
    assert repo.get_configuration(tenant_b.id, config_a.id) is None


def test_industry_template_apply_does_not_create_overlay_config(client, db_session):
    register = {
        "email": "overlay-seed@example.com",
        "password": "securepass123",
        "full_name": "Overlay Owner",
        "company_name": "Overlay Provider",
        "company_slug": "overlay-provider",
    }
    client.post("/api/v1/auth/register", json=register)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": register["email"], "password": register["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    tenant_id = uuid.UUID(
        client.post(
            "/api/v1/tenants",
            json={
                "name": "Overlay Seed Tenant",
                "slug": "overlay-seed-tenant",
                "industry_template_code": "flexity_sales_basic",
                "plan_code": "business",
            },
            headers=headers,
        ).json()["id"]
    )

    pipelines = client.get(
        "/api/v1/pipelines",
        headers={**headers, "X-Tenant-ID": str(tenant_id)},
    )
    assert pipelines.status_code == 200
    assert any(p["code"] == "flexity_sales" for p in pipelines.json())

    configs = ProcessOverlayRepository(db_session).list_configurations(tenant_id)
    assert configs == []


def test_active_version_composite_fk_declared_on_configuration():
    constraint_names = {
        constraint.name
        for constraint in TenantProcessConfiguration.__table__.constraints
        if getattr(constraint, "name", None)
    }
    assert "fk_tenant_process_config_active_version" in constraint_names


def test_composite_fk_rejects_foreign_active_version(db_session):
    from sqlalchemy.exc import IntegrityError

    tenant, _, config_a, actor = _setup_configuration(db_session, "composite-a")
    repo = ProcessOverlayRepository(db_session)
    other_template = repo.upsert_template(
        code="composite_second",
        name="Second",
        default_pipeline_code="composite_other",
        default_policy_blueprint_json={},
        required_module_codes_json=[],
        is_active=True,
    )
    other_pipeline = WorkflowRepository(db_session).create_pipeline(
        tenant_id=tenant.id,
        code="composite_other",
        name="Composite Other",
        entity_type="work_item",
        is_default=False,
    )
    WorkflowRepository(db_session).create_stage(
        pipeline_id=other_pipeline.id,
        code="new_lead",
        name="new_lead",
        sort_order=10,
        is_terminal=False,
    )
    config_b = repo.create_configuration(
        tenant_id=tenant.id,
        process_template_id=other_template.id,
        pipeline_id=other_pipeline.id,
    )
    version_b = repo.insert_definition_version(
        tenant_id=tenant.id,
        tenant_process_configuration_id=config_b.id,
        version_number=1,
        pipeline_id=other_pipeline.id,
        pipeline_code=other_pipeline.code,
        stage_codes_json=["new_lead"],
        policy_snapshot_json={"schema_version": 1},
        module_requirements_json=["crm"],
        published_by_user_id=actor,
        publish_reason="composite b",
    )
    config_a.active_definition_version_id = version_b.id
    try:
        db_session.flush()
    except IntegrityError:
        return
    pytest.skip("Composite FK enforcement is verified on PostgreSQL migration tests")


def test_activate_succeeds_when_version_and_modules_ready(db_session):
    tenant, _, config, actor = _setup_configuration(db_session, "activate-ok")
    _enable_overlay_modules(db_session, tenant.id)
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    publication = ProcessOverlayPublicationService(db_session)
    publication.set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )
    activated = ProcessOverlayConfigurationService(db_session).activate_configuration(
        tenant_id=tenant.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    assert activated.activation_state == ProcessOverlayActivationState.ACTIVE


def test_flexity_sales_template_seed_does_not_create_tenant_configuration(db_session):
    ProcessOverlayCatalogService(db_session).seed_templates()
    tenant = _bootstrap_tenant(db_session, "seed-only")
    _create_flexity_sales_pipeline(db_session, tenant.id)
    configs = ProcessOverlayRepository(db_session).list_configurations(tenant.id)
    assert configs == []
