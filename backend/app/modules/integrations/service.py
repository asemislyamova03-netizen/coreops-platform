import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import (
    ExternalSyncStatus,
    IntegrationConnectionStatus,
    ModuleMode,
    SyncJobStatus,
    SyncJobType,
    SyncLogLevel,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.integrations.models import IntegrationConnection
from app.modules.integrations.providers.registry import get_adapter
from app.modules.integrations.repository import IntegrationRepository
from app.modules.integrations.schemas import (
    ConnectionTestResponse,
    ExternalReferenceCreate,
    ExternalReferenceResponse,
    IntegrationConnectionCreate,
    IntegrationConnectionResponse,
    IntegrationConnectionUpdate,
    IntegrationProviderResponse,
    SyncJobDetailResponse,
    SyncJobResponse,
    SyncLogResponse,
    WebhookReceiveResponse,
)
from app.modules.integrations.seed import INTEGRATION_PROVIDERS
from app.modules.parties.models import Party
from app.modules.workflows.models import WorkItem


class IntegrationService:
    def __init__(self, db: Session, tenant_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = IntegrationRepository(db)

    def seed_providers(self) -> None:
        for item in INTEGRATION_PROVIDERS:
            self.repo.upsert_provider(**item)
        self.db.commit()

    def list_providers(self) -> list[IntegrationProviderResponse]:
        return [
            IntegrationProviderResponse.model_validate(p)
            for p in self.repo.list_providers()
        ]

    def list_connections(
        self,
        *,
        module_code: str | None = None,
        provider_code: str | None = None,
    ) -> list[IntegrationConnectionResponse]:
        self._require_tenant()
        connections = self.repo.list_connections(
            self.tenant_id,
            module_code=module_code,
            provider_code=provider_code,
        )
        return [self._to_connection_response(c) for c in connections]

    def create_connection(
        self,
        payload: IntegrationConnectionCreate,
    ) -> IntegrationConnectionResponse:
        self._require_tenant()
        provider = self.repo.get_provider(payload.provider_code)
        if not provider or not provider.is_active:
            raise NotFoundError(f"Provider '{payload.provider_code}' not found")

        if payload.module_code not in provider.supported_modules_json:
            raise ConflictError(
                f"Provider '{payload.provider_code}' does not support module '{payload.module_code}'"
            )

        existing = self.repo.list_connections(
            self.tenant_id,
            module_code=payload.module_code,
            provider_code=payload.provider_code,
        )
        if existing:
            raise ConflictError("Connection for this provider and module already exists")

        connection = self.repo.create_connection(
            tenant_id=self.tenant_id,
            provider_code=payload.provider_code,
            module_code=payload.module_code,
            name=payload.name,
            status=IntegrationConnectionStatus.PENDING,
            credentials_json=payload.credentials_json,
            settings_json=payload.settings_json,
        )
        return self._to_connection_response(connection)

    def get_connection(self, connection_id: uuid.UUID) -> IntegrationConnectionResponse:
        connection = self._get_connection_or_404(connection_id)
        return self._to_connection_response(connection)

    def update_connection(
        self,
        connection_id: uuid.UUID,
        payload: IntegrationConnectionUpdate,
    ) -> IntegrationConnectionResponse:
        connection = self._get_connection_or_404(connection_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(connection, key, value)
        self.db.flush()
        return self._to_connection_response(connection)

    def test_connection(self, connection_id: uuid.UUID) -> ConnectionTestResponse:
        connection = self._get_connection_or_404(connection_id)
        adapter = get_adapter(connection.provider_code)
        result = adapter.test_connection(connection.credentials_json, connection.settings_json)

        if result.success:
            connection.status = IntegrationConnectionStatus.ACTIVE
            connection.last_error = None
        else:
            connection.status = IntegrationConnectionStatus.ERROR
            connection.last_error = result.message

        self.db.flush()
        return ConnectionTestResponse(
            success=result.success,
            message=result.message,
            details=result.details,
        )

    def run_sync(
        self,
        connection_id: uuid.UUID,
        job_type: SyncJobType = SyncJobType.INCREMENTAL,
    ) -> SyncJobDetailResponse:
        connection = self._get_connection_or_404(connection_id)
        adapter = get_adapter(connection.provider_code)

        job = self.repo.create_sync_job(
            tenant_id=self.tenant_id,
            connection_id=connection.id,
            job_type=job_type,
            status=SyncJobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self._log(job, SyncLogLevel.INFO, f"Starting {job_type.value} sync")

        try:
            test = adapter.test_connection(connection.credentials_json, connection.settings_json)
            if not test.success:
                raise ConflictError(test.message)

            sync_result = adapter.sync(
                credentials=connection.credentials_json,
                settings=connection.settings_json,
                job_type=job_type.value,
            )
            if not sync_result.success:
                raise ConflictError(sync_result.message)

            refs_created = self._apply_mock_references(connection, sync_result.details)

            job.status = SyncJobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.stats_json = {
                "entities_synced": sync_result.entities_synced,
                "references_created": refs_created,
                "references_updated": sync_result.references_updated,
                **sync_result.details,
            }
            connection.status = IntegrationConnectionStatus.ACTIVE
            connection.last_sync_at = job.completed_at
            connection.last_error = None
            self._log(job, SyncLogLevel.INFO, sync_result.message, job.stats_json)

        except Exception as exc:
            job.status = SyncJobStatus.FAILED
            job.completed_at = datetime.now(UTC)
            job.error_message = str(exc)
            connection.status = IntegrationConnectionStatus.ERROR
            connection.last_error = str(exc)
            self._log(job, SyncLogLevel.ERROR, str(exc))

        self.db.flush()
        self.db.refresh(job)
        return self._to_job_detail(job)

    def list_sync_jobs(
        self,
        *,
        connection_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[SyncJobResponse]:
        self._require_tenant()
        jobs = self.repo.list_sync_jobs(
            self.tenant_id,
            connection_id=connection_id,
            limit=limit,
        )
        return [SyncJobResponse.model_validate(j) for j in jobs]

    def get_sync_job(self, job_id: uuid.UUID) -> SyncJobDetailResponse:
        self._require_tenant()
        job = self.repo.get_sync_job(self.tenant_id, job_id)
        if not job:
            raise NotFoundError("Sync job not found")
        return self._to_job_detail(job)

    def list_external_references(
        self,
        *,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        provider_code: str | None = None,
    ) -> list[ExternalReferenceResponse]:
        self._require_tenant()
        refs = self.repo.list_external_references(
            self.tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            provider_code=provider_code,
        )
        return [ExternalReferenceResponse.model_validate(r) for r in refs]

    def create_external_reference(
        self,
        payload: ExternalReferenceCreate,
    ) -> ExternalReferenceResponse:
        self._require_tenant()
        now = datetime.now(UTC)
        ref = self.repo.upsert_external_reference(
            tenant_id=self.tenant_id,
            connection_id=payload.connection_id,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            provider_code=payload.provider_code,
            external_entity_type=payload.external_entity_type,
            external_id=payload.external_id,
            external_url=payload.external_url,
            sync_status=ExternalSyncStatus.LINKED,
            last_synced_at=now,
            metadata_json=payload.metadata_json,
        )
        return ExternalReferenceResponse.model_validate(ref)

    def receive_webhook(
        self,
        provider_code: str,
        *,
        event_type: str,
        payload: dict,
        tenant_id: uuid.UUID | None = None,
    ) -> WebhookReceiveResponse:
        provider = self.repo.get_provider(provider_code)
        if not provider:
            raise NotFoundError(f"Provider '{provider_code}' not found")

        connection_id = None
        if tenant_id:
            connections = self.repo.list_connections(tenant_id, provider_code=provider_code)
            if connections:
                connection_id = connections[0].id

        event = self.repo.create_webhook_event(
            tenant_id=tenant_id,
            connection_id=connection_id,
            provider_code=provider_code,
            event_type=event_type,
            payload_json=payload,
            processed_at=datetime.now(UTC),
            status="processed",
        )
        return WebhookReceiveResponse(
            event_id=event.id,
            status="processed",
            message="Webhook accepted (mock processing)",
        )

    @classmethod
    def validate_external_module_mode(
        cls,
        db: Session,
        tenant_id: uuid.UUID,
        module_code: str,
        provider_code: str,
        mode: ModuleMode,
    ) -> None:
        if mode != ModuleMode.EXTERNAL:
            return
        repo = IntegrationRepository(db)
        provider = repo.get_provider(provider_code)
        if not provider:
            raise NotFoundError(f"Integration provider '{provider_code}' not found")
        if module_code not in provider.supported_modules_json:
            raise ConflictError(
                f"Provider '{provider_code}' does not support module '{module_code}'"
            )
        connection = repo.get_active_connection(tenant_id, provider_code, module_code)
        if not connection:
            raise ConflictError(
                f"Active integration connection required for external mode "
                f"({provider_code} / {module_code}). Create and test a connection first."
            )

    def _apply_mock_references(self, connection: IntegrationConnection, details: dict) -> int:
        created = 0
        now = datetime.now(UTC)
        portal = connection.settings_json.get("portal_url") or connection.credentials_json.get(
            "portal_url", "https://example.bitrix24.ru"
        )

        party = self.db.scalar(
            select(Party)
            .where(Party.tenant_id == self.tenant_id)
            .order_by(Party.created_at)
            .limit(1)
        )
        if party:
            self.repo.upsert_external_reference(
                tenant_id=self.tenant_id,
                connection_id=connection.id,
                entity_type="party",
                entity_id=party.id,
                provider_code=connection.provider_code,
                external_entity_type="contact",
                external_id=f"MOCK-CONTACT-{party.id.hex[:8]}",
                external_url=f"{portal}/crm/contact/details/MOCK/",
                sync_status=ExternalSyncStatus.SYNCED,
                last_synced_at=now,
                metadata_json={"mock": True},
            )
            created += 1

        work_item = self.db.scalar(
            select(WorkItem)
            .where(WorkItem.tenant_id == self.tenant_id)
            .order_by(WorkItem.created_at)
            .limit(1)
        )
        if work_item:
            self.repo.upsert_external_reference(
                tenant_id=self.tenant_id,
                connection_id=connection.id,
                entity_type="work_item",
                entity_id=work_item.id,
                provider_code=connection.provider_code,
                external_entity_type="deal",
                external_id=f"MOCK-DEAL-{work_item.id.hex[:8]}",
                external_url=f"{portal}/crm/deal/details/MOCK/",
                sync_status=ExternalSyncStatus.SYNCED,
                last_synced_at=now,
                metadata_json={"mock": True},
            )
            created += 1

        for item in details.get("mock_entities", []):
            if party or work_item:
                continue
            created += 1

        return created

    def _log(self, job, level: SyncLogLevel, message: str, details: dict | None = None) -> None:
        self.repo.create_sync_log(
            tenant_id=self.tenant_id,
            job_id=job.id,
            connection_id=job.connection_id,
            level=level,
            message=message,
            details_json=details or {},
        )

    def _get_connection_or_404(self, connection_id: uuid.UUID) -> IntegrationConnection:
        self._require_tenant()
        connection = self.repo.get_connection(self.tenant_id, connection_id)
        if not connection:
            raise NotFoundError("Integration connection not found")
        return connection

    def _require_tenant(self) -> None:
        if self.tenant_id is None:
            raise ConflictError("Tenant context required")

    def _to_connection_response(self, connection: IntegrationConnection) -> IntegrationConnectionResponse:
        return IntegrationConnectionResponse(
            id=connection.id,
            tenant_id=connection.tenant_id,
            provider_code=connection.provider_code,
            module_code=connection.module_code,
            name=connection.name,
            status=connection.status,
            settings_json=connection.settings_json,
            has_credentials=bool(connection.credentials_json),
            last_sync_at=connection.last_sync_at,
            last_error=connection.last_error,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )

    def _to_job_detail(self, job) -> SyncJobDetailResponse:
        return SyncJobDetailResponse(
            **SyncJobResponse.model_validate(job).model_dump(),
            logs=[SyncLogResponse.model_validate(log) for log in job.logs],
        )
