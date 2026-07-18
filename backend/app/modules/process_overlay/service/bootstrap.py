"""LOCAL/ops bootstrap helpers for Process Overlay (not production deploy)."""

from __future__ import annotations

import copy
import hashlib
import json
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.modules.process_overlay.policy_schema import PolicySnapshotV1, parse_policy_snapshot
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import (
    PublishDefinitionVersionRequest,
    TenantProcessConfigurationResponse,
)
from app.modules.process_overlay.service.catalog import ProcessOverlayCatalogService
from app.modules.process_overlay.service.configuration import ProcessOverlayConfigurationService
from app.modules.process_overlay.service.publication import ProcessOverlayPublicationService
from app.modules.workflows.repository import WorkflowRepository

_DEFAULT_PUBLISH_REASON = "C2a local/ops bootstrap — new immutable definition version"
_FLEXITY_SALES_TEMPLATE = "flexity_sales_intake"
_FLEXITY_SALES_PIPELINE = "flexity_sales"


def policy_fingerprint(policy: PolicySnapshotV1 | dict) -> str:
    """Stable SHA-256 of a canonical policy representation.

    Transitions are ordered by (from, to) so list order does not create
    false-positive "policy changed" publishes.
    """
    if isinstance(policy, PolicySnapshotV1):
        data = policy.model_dump()
    else:
        data = parse_policy_snapshot(policy).model_dump()

    transitions = sorted(
        data.get("transitions") or [],
        key=lambda item: (item["from_stage_code"], item["to_stage_code"]),
    )
    data["transitions"] = transitions
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ProcessOverlayBootstrapService:
    """Ops/local helpers to stand up overlay config without HTTP/UI.

    Bootstrap is **disabled by default** and forbidden in production.
    Callers must pass explicit tenant_id + pipeline_code and set
    PROCESS_OVERLAY_BOOTSTRAP_ENABLED=true. Activation is opt-in via activate=True.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcessOverlayRepository(db)
        self.workflows = WorkflowRepository(db)
        self.catalog = ProcessOverlayCatalogService(db)
        self.configuration = ProcessOverlayConfigurationService(db)
        self.publication = ProcessOverlayPublicationService(db)

    def bootstrap_flexity_sales_intake(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        pipeline_code: str,
        activate: bool = False,
        publish_reason: str = _DEFAULT_PUBLISH_REASON,
    ) -> TenantProcessConfigurationResponse:
        """Seed catalog, ensure config, publish only when policy changed, optionally activate.

        Idempotent: if a published version with the same policy fingerprint already
        exists (prefer active, else latest), re-run reuses that version id and does
        not publish a duplicate. Never creates a second configuration for the pipeline.
        """
        self._assert_ops_guard()
        if not pipeline_code or not str(pipeline_code).strip():
            raise PermissionDeniedError("pipeline_code is required for process overlay bootstrap")
        pipeline_code = str(pipeline_code).strip()
        if pipeline_code != _FLEXITY_SALES_PIPELINE:
            raise PermissionDeniedError(
                f"bootstrap_flexity_sales_intake requires pipeline_code='{_FLEXITY_SALES_PIPELINE}'"
            )

        self.catalog.seed_templates()

        pipeline = self.workflows.get_pipeline_by_code(tenant_id, pipeline_code)
        if pipeline is None:
            raise NotFoundError(f"Pipeline '{pipeline_code}' not found for tenant")

        existing = self.repo.get_configuration_by_pipeline(tenant_id, pipeline.id)
        if existing is None:
            created = self.configuration.create_configuration(
                tenant_id=tenant_id,
                process_template_code=_FLEXITY_SALES_TEMPLATE,
                pipeline_id=pipeline.id,
                actor_user_id=actor_user_id,
            )
            configuration_id = created.id
        else:
            configuration_id = existing.id

        template = self.repo.get_template_by_code(_FLEXITY_SALES_TEMPLATE)
        if template is None or not template.is_active:
            raise NotFoundError(f"Process template '{_FLEXITY_SALES_TEMPLATE}' not found")

        desired_policy = parse_policy_snapshot(
            copy.deepcopy(template.default_policy_blueprint_json)
        )
        desired_fp = policy_fingerprint(desired_policy)

        matching = self._find_matching_published_version(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            fingerprint=desired_fp,
        )
        if matching is not None:
            config = self.repo.get_configuration(tenant_id, configuration_id)
            assert config is not None
            if config.active_definition_version_id != matching.id:
                self.publication.set_active_definition_version(
                    tenant_id=tenant_id,
                    configuration_id=configuration_id,
                    version_id=matching.id,
                    actor_user_id=actor_user_id,
                )
            return self._finalize(
                tenant_id=tenant_id,
                configuration_id=configuration_id,
                actor_user_id=actor_user_id,
                activate=activate,
            )

        version = self.publication.publish_definition_version(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            request=PublishDefinitionVersionRequest(
                policy=desired_policy,
                publish_reason=publish_reason,
            ),
            actor_user_id=actor_user_id,
        )
        self.publication.set_active_definition_version(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            version_id=version.id,
            actor_user_id=actor_user_id,
        )
        return self._finalize(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            actor_user_id=actor_user_id,
            activate=activate,
        )

    def _finalize(
        self,
        *,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        activate: bool,
    ) -> TenantProcessConfigurationResponse:
        if activate:
            return self.configuration.activate_configuration(
                tenant_id=tenant_id,
                configuration_id=configuration_id,
                actor_user_id=actor_user_id,
            )
        return self.configuration.get_configuration(tenant_id, configuration_id)

    def _find_matching_published_version(
        self,
        *,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
        fingerprint: str,
    ):
        """Prefer active published version; else latest published with same fingerprint."""
        config = self.repo.get_configuration(tenant_id, configuration_id)
        if config is None:
            return None

        if config.active_definition_version_id is not None:
            active = self.repo.get_definition_version_for_configuration(
                tenant_id,
                configuration_id,
                config.active_definition_version_id,
            )
            if active is not None and policy_fingerprint(active.policy_snapshot_json) == fingerprint:
                return active

        latest = self.repo.get_latest_definition_version(tenant_id, configuration_id)
        if latest is not None and policy_fingerprint(latest.policy_snapshot_json) == fingerprint:
            return latest
        return None

    def _assert_ops_guard(self) -> None:
        settings = get_settings()
        if not settings.process_overlay_bootstrap_enabled:
            raise PermissionDeniedError(
                "Process overlay bootstrap is disabled "
                "(set PROCESS_OVERLAY_BOOTSTRAP_ENABLED=true for local/ops only)"
            )
        if settings.app_env.strip().lower() == "production":
            raise PermissionDeniedError(
                "Process overlay bootstrap is forbidden in production"
            )
