import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import IntegrationConnectionStatus, SyncJobStatus
from app.modules.integrations.models import (
    ExternalReference,
    IntegrationConnection,
    IntegrationProvider,
    SyncJob,
    SyncLog,
    WebhookEvent,
)


class IntegrationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_providers(self, active_only: bool = True) -> list[IntegrationProvider]:
        stmt = select(IntegrationProvider).order_by(IntegrationProvider.name)
        if active_only:
            stmt = stmt.where(IntegrationProvider.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_provider(self, code: str) -> IntegrationProvider | None:
        return self.db.scalar(select(IntegrationProvider).where(IntegrationProvider.code == code))

    def upsert_provider(self, **kwargs) -> IntegrationProvider:
        provider = self.get_provider(kwargs["code"])
        if provider:
            for key, value in kwargs.items():
                setattr(provider, key, value)
        else:
            provider = IntegrationProvider(**kwargs)
            self.db.add(provider)
        self.db.flush()
        return provider

    def list_connections(
        self,
        tenant_id: uuid.UUID,
        *,
        module_code: str | None = None,
        provider_code: str | None = None,
    ) -> list[IntegrationConnection]:
        stmt = (
            select(IntegrationConnection)
            .where(IntegrationConnection.tenant_id == tenant_id)
            .order_by(IntegrationConnection.name)
        )
        if module_code:
            stmt = stmt.where(IntegrationConnection.module_code == module_code)
        if provider_code:
            stmt = stmt.where(IntegrationConnection.provider_code == provider_code)
        return list(self.db.scalars(stmt).all())

    def get_connection(self, tenant_id: uuid.UUID, connection_id: uuid.UUID) -> IntegrationConnection | None:
        stmt = select(IntegrationConnection).where(
            IntegrationConnection.tenant_id == tenant_id,
            IntegrationConnection.id == connection_id,
        )
        return self.db.scalar(stmt)

    def get_active_connection(
        self,
        tenant_id: uuid.UUID,
        provider_code: str,
        module_code: str,
    ) -> IntegrationConnection | None:
        stmt = select(IntegrationConnection).where(
            IntegrationConnection.tenant_id == tenant_id,
            IntegrationConnection.provider_code == provider_code,
            IntegrationConnection.module_code == module_code,
            IntegrationConnection.status == IntegrationConnectionStatus.ACTIVE,
        )
        return self.db.scalar(stmt)

    def create_connection(self, **kwargs) -> IntegrationConnection:
        connection = IntegrationConnection(**kwargs)
        self.db.add(connection)
        self.db.flush()
        return connection

    def list_external_references(
        self,
        tenant_id: uuid.UUID,
        *,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        provider_code: str | None = None,
    ) -> list[ExternalReference]:
        stmt = select(ExternalReference).where(ExternalReference.tenant_id == tenant_id)
        if entity_type:
            stmt = stmt.where(ExternalReference.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(ExternalReference.entity_id == entity_id)
        if provider_code:
            stmt = stmt.where(ExternalReference.provider_code == provider_code)
        stmt = stmt.order_by(ExternalReference.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_external_reference(
        self,
        tenant_id: uuid.UUID,
        reference_id: uuid.UUID,
    ) -> ExternalReference | None:
        stmt = select(ExternalReference).where(
            ExternalReference.tenant_id == tenant_id,
            ExternalReference.id == reference_id,
        )
        return self.db.scalar(stmt)

    def upsert_external_reference(self, **kwargs) -> ExternalReference:
        stmt = select(ExternalReference).where(
            ExternalReference.tenant_id == kwargs["tenant_id"],
            ExternalReference.entity_type == kwargs["entity_type"],
            ExternalReference.entity_id == kwargs["entity_id"],
            ExternalReference.provider_code == kwargs["provider_code"],
        )
        ref = self.db.scalar(stmt)
        if ref:
            for key in (
                "connection_id",
                "external_entity_type",
                "external_id",
                "external_url",
                "sync_status",
                "last_synced_at",
                "metadata_json",
            ):
                if key in kwargs:
                    setattr(ref, key, kwargs[key])
        else:
            ref = ExternalReference(**kwargs)
            self.db.add(ref)
        self.db.flush()
        return ref

    def create_sync_job(self, **kwargs) -> SyncJob:
        job = SyncJob(**kwargs)
        self.db.add(job)
        self.db.flush()
        return job

    def get_sync_job(self, tenant_id: uuid.UUID, job_id: uuid.UUID) -> SyncJob | None:
        stmt = (
            select(SyncJob)
            .where(SyncJob.tenant_id == tenant_id, SyncJob.id == job_id)
            .options(selectinload(SyncJob.logs))
        )
        return self.db.scalar(stmt)

    def list_sync_jobs(
        self,
        tenant_id: uuid.UUID,
        *,
        connection_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[SyncJob]:
        stmt = (
            select(SyncJob)
            .where(SyncJob.tenant_id == tenant_id)
            .options(selectinload(SyncJob.logs))
            .order_by(SyncJob.created_at.desc())
            .limit(limit)
        )
        if connection_id:
            stmt = stmt.where(SyncJob.connection_id == connection_id)
        return list(self.db.scalars(stmt).all())

    def create_sync_log(self, **kwargs) -> SyncLog:
        log = SyncLog(**kwargs)
        self.db.add(log)
        self.db.flush()
        return log

    def create_webhook_event(self, **kwargs) -> WebhookEvent:
        event = WebhookEvent(**kwargs)
        self.db.add(event)
        self.db.flush()
        return event
