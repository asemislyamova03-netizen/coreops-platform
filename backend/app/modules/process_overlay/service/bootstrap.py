"""LOCAL/ops bootstrap helpers for Process Overlay (not production deploy)."""

from __future__ import annotations

import copy
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.process_overlay.policy_schema import parse_policy_snapshot
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import (
    PublishDefinitionVersionRequest,
    TenantProcessConfigurationResponse,
)
from app.modules.process_overlay.service.catalog import ProcessOverlayCatalogService
from app.modules.process_overlay.service.configuration import ProcessOverlayConfigurationService
from app.modules.process_overlay.service.publication import ProcessOverlayPublicationService
from app.modules.workflows.repository import WorkflowRepository


class ProcessOverlayBootstrapService:
    """Ops/local helpers to stand up overlay config without HTTP/UI.

    C2a does **not** activate production. Callers must run this intentionally
    on a local/ops tenant (e.g. flexity-sales) and always get a **new**
    immutable definition version — published versions are never mutated.
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
        publish_reason: str = "C2a local/ops bootstrap — new immutable definition version",
    ) -> TenantProcessConfigurationResponse:
        """Seed catalog, ensure config, publish NEW version, set_active, activate.

        Production activation is intentionally out of C2a scope.
        """
        self.catalog.seed_templates()

        pipeline = self.workflows.get_pipeline_by_code(tenant_id, "flexity_sales")
        if pipeline is None:
            raise NotFoundError("Pipeline 'flexity_sales' not found for tenant")

        existing = self.repo.get_configuration_by_pipeline(tenant_id, pipeline.id)
        if existing is None:
            created = self.configuration.create_configuration(
                tenant_id=tenant_id,
                process_template_code="flexity_sales_intake",
                pipeline_id=pipeline.id,
                actor_user_id=actor_user_id,
            )
            configuration_id = created.id
        else:
            configuration_id = existing.id

        template = self.repo.get_template_by_code("flexity_sales_intake")
        if template is None or not template.is_active:
            raise NotFoundError("Process template 'flexity_sales_intake' not found")

        version = self.publication.publish_definition_version(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            request=PublishDefinitionVersionRequest(
                policy=parse_policy_snapshot(
                    copy.deepcopy(template.default_policy_blueprint_json)
                ),
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
        return self.configuration.activate_configuration(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            actor_user_id=actor_user_id,
        )
