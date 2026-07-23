import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.marketing.enums import MarketingMediaAssetStatus, MarketingPackStatus, MarketingTopicStatus
from app.modules.marketing.models import (
    MarketingContentTopic,
    MarketingMediaAsset,
    MarketingPublicationPack,
    MarketingPublicationText,
    MarketingPublishDestination,
    MarketingPublishingConnection,
    MarketingPublishLog,
    MarketingStorageResourceProfile,
)
from app.modules.marketing.enums import (
    MarketingDestinationStatus,
    MarketingDestinationValidationStatus,
    MarketingPublishDestinationType,
    MarketingPublishingConnectionStatus,
    MarketingPublishingProvider,
    MarketingPublishingTokenStatus,
    MarketingStorageProfileStatus,
    MarketingStorageResourceMode,
    destination_capability_enabled,
    destination_type_provider,
)
from app.modules.marketing.exceptions import (
    MarketingPublishDestinationHardDeleteForbiddenError,
    MarketingPublishDestinationNotFoundError,
    MarketingPublishDestinationValidationError,
    MarketingPublishingConnectionNotFoundError,
)
from app.modules.marketing.service.publish_destination_validation import (
    validate_destination_display_name,
    validate_destination_metadata_json,
)


class MarketingRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Topics ---

    def list_topics(
        self,
        tenant_id: uuid.UUID,
        *,
        status: MarketingTopicStatus | None = None,
        rubric: str | None = None,
        search: str | None = None,
        exclude_archived: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> list[MarketingContentTopic]:
        stmt = (
            select(MarketingContentTopic)
            .where(MarketingContentTopic.tenant_id == tenant_id)
            .order_by(
                MarketingContentTopic.priority.desc(),
                MarketingContentTopic.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(MarketingContentTopic.status == status)
        elif exclude_archived:
            stmt = stmt.where(MarketingContentTopic.status != MarketingTopicStatus.ARCHIVED)
        if rubric:
            stmt = stmt.where(MarketingContentTopic.rubric == rubric)
        if search:
            stmt = stmt.where(MarketingContentTopic.title.ilike(f"%{search}%"))
        return list(self.db.scalars(stmt).all())

    def get_topic(
        self,
        tenant_id: uuid.UUID,
        topic_id: uuid.UUID,
    ) -> MarketingContentTopic | None:
        stmt = select(MarketingContentTopic).where(
            MarketingContentTopic.tenant_id == tenant_id,
            MarketingContentTopic.id == topic_id,
        )
        return self.db.scalar(stmt)

    def create_topic(self, **kwargs) -> MarketingContentTopic:
        topic = MarketingContentTopic(**kwargs)
        self.db.add(topic)
        self.db.flush()
        return topic

    def count_approved_topics(self, tenant_id: uuid.UUID) -> int:
        stmt = select(MarketingContentTopic).where(
            MarketingContentTopic.tenant_id == tenant_id,
            MarketingContentTopic.status == MarketingTopicStatus.APPROVED,
        )
        return len(list(self.db.scalars(stmt).all()))

    def find_pack_for_topic_date(
        self,
        tenant_id: uuid.UUID,
        topic_id: uuid.UUID,
        planned_date: date,
    ) -> MarketingPublicationPack | None:
        stmt = select(MarketingPublicationPack).where(
            MarketingPublicationPack.tenant_id == tenant_id,
            MarketingPublicationPack.topic_id == topic_id,
            MarketingPublicationPack.planned_date == planned_date,
            MarketingPublicationPack.status != MarketingPackStatus.ARCHIVED,
        )
        return self.db.scalar(stmt)

    def list_active_packs_for_topic(
        self,
        tenant_id: uuid.UUID,
        topic_id: uuid.UUID,
    ) -> list[MarketingPublicationPack]:
        stmt = select(MarketingPublicationPack).where(
            MarketingPublicationPack.tenant_id == tenant_id,
            MarketingPublicationPack.topic_id == topic_id,
            MarketingPublicationPack.status != MarketingPackStatus.ARCHIVED,
        )
        return list(self.db.scalars(stmt).all())

    # --- Packs ---

    def list_packs(
        self,
        tenant_id: uuid.UUID,
        *,
        status: MarketingPackStatus | None = None,
        topic_id: uuid.UUID | None = None,
        planned_date: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[MarketingPublicationPack]:
        stmt = (
            select(MarketingPublicationPack)
            .where(MarketingPublicationPack.tenant_id == tenant_id)
            .options(selectinload(MarketingPublicationPack.topic))
            .order_by(MarketingPublicationPack.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(MarketingPublicationPack.status == status)
        if topic_id is not None:
            stmt = stmt.where(MarketingPublicationPack.topic_id == topic_id)
        if planned_date is not None:
            stmt = stmt.where(MarketingPublicationPack.planned_date == planned_date)
        return list(self.db.scalars(stmt).all())

    def get_pack(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
        *,
        with_relations: bool = False,
    ) -> MarketingPublicationPack | None:
        stmt = select(MarketingPublicationPack).where(
            MarketingPublicationPack.tenant_id == tenant_id,
            MarketingPublicationPack.id == pack_id,
        )
        if with_relations:
            stmt = stmt.options(
                selectinload(MarketingPublicationPack.topic),
                selectinload(MarketingPublicationPack.texts),
                selectinload(MarketingPublicationPack.media_assets),
                selectinload(MarketingPublicationPack.publish_logs),
            )
        return self.db.scalar(stmt)

    def get_pack_by_slug(
        self,
        tenant_id: uuid.UUID,
        slug: str,
    ) -> MarketingPublicationPack | None:
        stmt = select(MarketingPublicationPack).where(
            MarketingPublicationPack.tenant_id == tenant_id,
            MarketingPublicationPack.slug == slug,
        )
        return self.db.scalar(stmt)

    def create_pack(self, **kwargs) -> MarketingPublicationPack:
        pack = MarketingPublicationPack(**kwargs)
        self.db.add(pack)
        self.db.flush()
        return pack

    def create_text(self, **kwargs) -> MarketingPublicationText:
        text = MarketingPublicationText(**kwargs)
        self.db.add(text)
        self.db.flush()
        return text

    def list_pack_texts(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
    ) -> list[MarketingPublicationText]:
        stmt = (
            select(MarketingPublicationText)
            .where(
                MarketingPublicationText.tenant_id == tenant_id,
                MarketingPublicationText.pack_id == pack_id,
            )
            .order_by(MarketingPublicationText.channel)
        )
        return list(self.db.scalars(stmt).all())

    def get_pack_text(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
        channel,
    ) -> MarketingPublicationText | None:
        stmt = select(MarketingPublicationText).where(
            MarketingPublicationText.tenant_id == tenant_id,
            MarketingPublicationText.pack_id == pack_id,
            MarketingPublicationText.channel == channel,
        )
        return self.db.scalar(stmt)

    def list_pack_media(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> list[MarketingMediaAsset]:
        stmt = (
            select(MarketingMediaAsset)
            .where(
                MarketingMediaAsset.tenant_id == tenant_id,
                MarketingMediaAsset.pack_id == pack_id,
            )
            .order_by(MarketingMediaAsset.created_at)
        )
        if not include_archived:
            stmt = stmt.where(MarketingMediaAsset.status != MarketingMediaAssetStatus.ARCHIVED)
        return list(self.db.scalars(stmt).all())

    def get_media_asset(
        self,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> MarketingMediaAsset | None:
        stmt = select(MarketingMediaAsset).where(
            MarketingMediaAsset.tenant_id == tenant_id,
            MarketingMediaAsset.id == asset_id,
        )
        return self.db.scalar(stmt)

    def create_media_asset(self, **kwargs) -> MarketingMediaAsset:
        asset = MarketingMediaAsset(**kwargs)
        self.db.add(asset)
        self.db.flush()
        return asset

    def list_pack_logs(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
    ) -> list[MarketingPublishLog]:
        stmt = (
            select(MarketingPublishLog)
            .where(
                MarketingPublishLog.tenant_id == tenant_id,
                MarketingPublishLog.pack_id == pack_id,
            )
            .order_by(MarketingPublishLog.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def create_publish_log(self, **kwargs) -> MarketingPublishLog:
        row = MarketingPublishLog(**kwargs)
        self.db.add(row)
        self.db.flush()
        return row

    def find_historical_publish_log(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
        *,
        channel: str,
        source: str,
        evidence_ref: str | None,
        published_at_date: str | None,
    ) -> MarketingPublishLog | None:
        """Idempotency lookup for action=historical_record."""
        stmt = select(MarketingPublishLog).where(
            MarketingPublishLog.tenant_id == tenant_id,
            MarketingPublishLog.pack_id == pack_id,
            MarketingPublishLog.channel == channel,
            MarketingPublishLog.action == "historical_record",
        )
        candidates = list(self.db.scalars(stmt).all())
        for row in candidates:
            meta = row.metadata_json or {}
            if meta.get("source") != source:
                continue
            if evidence_ref:
                if meta.get("evidence_ref") == evidence_ref:
                    return row
            else:
                if meta.get("evidence_ref"):
                    continue
                if meta.get("published_at_date") == published_at_date:
                    return row
        return None

    # --- Publishing connections (M8-B) ---

    def list_publishing_connections(
        self,
        tenant_id: uuid.UUID,
        *,
        provider: MarketingPublishingProvider | None = None,
        status: MarketingPublishingConnectionStatus | None = None,
        token_status: MarketingPublishingTokenStatus | None = None,
    ) -> list[MarketingPublishingConnection]:
        stmt = (
            select(MarketingPublishingConnection)
            .where(MarketingPublishingConnection.tenant_id == tenant_id)
            .order_by(MarketingPublishingConnection.created_at.desc())
        )
        if provider is not None:
            stmt = stmt.where(MarketingPublishingConnection.provider == provider)
        if status is not None:
            stmt = stmt.where(MarketingPublishingConnection.status == status)
        if token_status is not None:
            stmt = stmt.where(MarketingPublishingConnection.token_status == token_status)
        return list(self.db.scalars(stmt).all())

    def get_publishing_connection(
        self,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
    ) -> MarketingPublishingConnection | None:
        stmt = select(MarketingPublishingConnection).where(
            MarketingPublishingConnection.tenant_id == tenant_id,
            MarketingPublishingConnection.id == connection_id,
        )
        return self.db.scalar(stmt)

    def get_publishing_connection_for_update(
        self,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
    ) -> MarketingPublishingConnection | None:
        """Tenant-scoped load with row lock (FOR UPDATE). SQLite may no-op the lock."""
        stmt = (
            select(MarketingPublishingConnection)
            .where(
                MarketingPublishingConnection.tenant_id == tenant_id,
                MarketingPublishingConnection.id == connection_id,
            )
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def create_publishing_connection(
        self,
        *,
        tenant_id: uuid.UUID,
        provider: MarketingPublishingProvider,
        account_display_name: str,
        account_identifier: str | None,
        status: MarketingPublishingConnectionStatus,
        token_status: MarketingPublishingTokenStatus,
        scopes_json: list,
        metadata_json: dict,
        created_by_user_id: uuid.UUID | None,
        updated_by_user_id: uuid.UUID | None,
    ) -> MarketingPublishingConnection:
        row = MarketingPublishingConnection(
            tenant_id=tenant_id,
            provider=provider,
            account_display_name=account_display_name,
            account_identifier=account_identifier,
            status=status,
            token_status=token_status,
            scopes_json=scopes_json,
            metadata_json=metadata_json,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=updated_by_user_id,
        )
        self.db.add(row)
        return row

    # --- Publish destinations (M8-D1) ---

    def list_publish_destinations_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        status: MarketingDestinationStatus | None = None,
        publishing_connection_id: uuid.UUID | None = None,
        destination_type: MarketingPublishDestinationType | None = None,
        exclude_archived: bool = True,
    ) -> list[MarketingPublishDestination]:
        stmt = (
            select(MarketingPublishDestination)
            .where(MarketingPublishDestination.tenant_id == tenant_id)
            .order_by(MarketingPublishDestination.created_at.desc())
        )
        if publishing_connection_id is not None:
            stmt = stmt.where(
                MarketingPublishDestination.publishing_connection_id
                == publishing_connection_id
            )
        if destination_type is not None:
            stmt = stmt.where(
                MarketingPublishDestination.destination_type == destination_type
            )
        if status is not None:
            stmt = stmt.where(MarketingPublishDestination.status == status)
        elif exclude_archived:
            stmt = stmt.where(
                MarketingPublishDestination.status != MarketingDestinationStatus.ARCHIVED
            )
        return list(self.db.scalars(stmt).all())

    def list_publish_destinations_by_connection(
        self,
        tenant_id: uuid.UUID,
        publishing_connection_id: uuid.UUID,
        *,
        exclude_archived: bool = True,
    ) -> list[MarketingPublishDestination]:
        stmt = (
            select(MarketingPublishDestination)
            .where(
                MarketingPublishDestination.tenant_id == tenant_id,
                MarketingPublishDestination.publishing_connection_id
                == publishing_connection_id,
            )
            .order_by(MarketingPublishDestination.created_at.desc())
        )
        if exclude_archived:
            stmt = stmt.where(
                MarketingPublishDestination.status != MarketingDestinationStatus.ARCHIVED
            )
        return list(self.db.scalars(stmt).all())

    def get_publish_destination(
        self,
        tenant_id: uuid.UUID,
        destination_id: uuid.UUID,
    ) -> MarketingPublishDestination | None:
        stmt = select(MarketingPublishDestination).where(
            MarketingPublishDestination.tenant_id == tenant_id,
            MarketingPublishDestination.id == destination_id,
        )
        return self.db.scalar(stmt)

    def create_publish_destination(
        self,
        *,
        tenant_id: uuid.UUID,
        publishing_connection_id: uuid.UUID,
        destination_type: MarketingPublishDestinationType,
        external_id: str,
        display_name: str,
        metadata_json: dict | None = None,
        status: MarketingDestinationStatus | None = None,
        created_by_user_id: uuid.UUID | None = None,
        updated_by_user_id: uuid.UUID | None = None,
    ) -> MarketingPublishDestination:
        connection = self.get_publishing_connection(tenant_id, publishing_connection_id)
        if connection is None:
            # Cross-tenant or missing connection — fail closed (same as not found).
            raise MarketingPublishingConnectionNotFoundError()

        expected_provider = destination_type_provider(destination_type)
        if connection.provider != expected_provider:
            raise MarketingPublishDestinationValidationError("provider_destination_type_mismatch")

        external = external_id.strip()
        if not external:
            raise MarketingPublishDestinationValidationError("external_id_required")
        name = validate_destination_display_name(display_name)

        initial_status = status
        if initial_status is None:
            if destination_capability_enabled(destination_type):
                initial_status = MarketingDestinationStatus.ENABLED
            else:
                initial_status = MarketingDestinationStatus.DISABLED
        elif initial_status == MarketingDestinationStatus.ENABLED and not destination_capability_enabled(
            destination_type
        ):
            raise MarketingPublishDestinationValidationError("destination_capability_disabled")
        elif initial_status == MarketingDestinationStatus.ARCHIVED:
            raise MarketingPublishDestinationValidationError("cannot_create_archived")

        safe_metadata = validate_destination_metadata_json(metadata_json)

        row = MarketingPublishDestination(
            tenant_id=tenant_id,
            publishing_connection_id=publishing_connection_id,
            provider=connection.provider,
            destination_type=destination_type,
            external_id=external,
            display_name=name,
            status=initial_status,
            validation_status=MarketingDestinationValidationStatus.UNCHECKED,
            metadata_json=safe_metadata,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=updated_by_user_id,
        )
        self.db.add(row)
        return row

    def update_publish_destination_display(
        self,
        tenant_id: uuid.UUID,
        destination_id: uuid.UUID,
        *,
        display_name: str | None = None,
        metadata_json: dict | None = None,
        updated_by_user_id: uuid.UUID | None = None,
    ) -> MarketingPublishDestination:
        row = self.get_publish_destination(tenant_id, destination_id)
        if row is None:
            raise MarketingPublishDestinationNotFoundError()
        if row.status == MarketingDestinationStatus.ARCHIVED:
            raise MarketingPublishDestinationValidationError("archived_destination_immutable")
        if display_name is not None:
            row.display_name = validate_destination_display_name(display_name)
        if metadata_json is not None:
            row.metadata_json = validate_destination_metadata_json(metadata_json)
        row.updated_by_user_id = updated_by_user_id
        return row

    def update_publish_destination_external_id(
        self,
        tenant_id: uuid.UUID,
        destination_id: uuid.UUID,
        external_id: str,
        *,
        updated_by_user_id: uuid.UUID | None = None,
    ) -> MarketingPublishDestination:
        row = self.get_publish_destination(tenant_id, destination_id)
        if row is None:
            raise MarketingPublishDestinationNotFoundError()
        if row.status == MarketingDestinationStatus.ARCHIVED:
            raise MarketingPublishDestinationValidationError("archived_destination_immutable")
        row.update_external_id(external_id)
        row.updated_by_user_id = updated_by_user_id
        return row

    def enable_publish_destination(
        self,
        tenant_id: uuid.UUID,
        destination_id: uuid.UUID,
        *,
        updated_by_user_id: uuid.UUID | None = None,
    ) -> MarketingPublishDestination:
        row = self.get_publish_destination(tenant_id, destination_id)
        if row is None:
            raise MarketingPublishDestinationNotFoundError()
        row.enable()
        row.updated_by_user_id = updated_by_user_id
        return row

    def disable_publish_destination(
        self,
        tenant_id: uuid.UUID,
        destination_id: uuid.UUID,
        *,
        updated_by_user_id: uuid.UUID | None = None,
    ) -> MarketingPublishDestination:
        row = self.get_publish_destination(tenant_id, destination_id)
        if row is None:
            raise MarketingPublishDestinationNotFoundError()
        row.disable()
        row.updated_by_user_id = updated_by_user_id
        return row

    def archive_publish_destination(
        self,
        tenant_id: uuid.UUID,
        destination_id: uuid.UUID,
        *,
        updated_by_user_id: uuid.UUID | None = None,
    ) -> MarketingPublishDestination:
        row = self.get_publish_destination(tenant_id, destination_id)
        if row is None:
            raise MarketingPublishDestinationNotFoundError()
        row.archive()
        row.updated_by_user_id = updated_by_user_id
        return row

    def structural_validate_publish_destination(
        self,
        tenant_id: uuid.UUID,
        destination_id: uuid.UUID,
        *,
        validation_status: MarketingDestinationValidationStatus,
        validation_error_code: str | None = None,
        updated_by_user_id: uuid.UUID | None = None,
    ) -> MarketingPublishDestination:
        """Apply structural validation only — never claims provider adapter success."""
        row = self.get_publish_destination(tenant_id, destination_id)
        if row is None:
            raise MarketingPublishDestinationNotFoundError()
        row.apply_structural_validation(
            validation_status=validation_status,
            validation_error_code=validation_error_code,
        )
        row.updated_by_user_id = updated_by_user_id
        return row

    def delete_publish_destination(self, *_args, **_kwargs) -> None:
        """Hard delete is forbidden — archive instead."""
        raise MarketingPublishDestinationHardDeleteForbiddenError()

    # --- Storage resource profiles (M8-C2a) ---

    def list_storage_profiles(
        self, tenant_id: uuid.UUID
    ) -> list[MarketingStorageResourceProfile]:
        stmt = (
            select(MarketingStorageResourceProfile)
            .where(MarketingStorageResourceProfile.tenant_id == tenant_id)
            .order_by(MarketingStorageResourceProfile.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_storage_profile(
        self,
        tenant_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> MarketingStorageResourceProfile | None:
        stmt = select(MarketingStorageResourceProfile).where(
            MarketingStorageResourceProfile.tenant_id == tenant_id,
            MarketingStorageResourceProfile.id == profile_id,
        )
        return self.db.scalar(stmt)

    def get_active_storage_profile(
        self,
        tenant_id: uuid.UUID,
        mode: MarketingStorageResourceMode,
    ) -> MarketingStorageResourceProfile | None:
        stmt = select(MarketingStorageResourceProfile).where(
            MarketingStorageResourceProfile.tenant_id == tenant_id,
            MarketingStorageResourceProfile.mode == mode,
            MarketingStorageResourceProfile.status == MarketingStorageProfileStatus.ACTIVE,
        )
        return self.db.scalar(stmt)

    def get_default_storage_profile(
        self, tenant_id: uuid.UUID
    ) -> MarketingStorageResourceProfile | None:
        stmt = select(MarketingStorageResourceProfile).where(
            MarketingStorageResourceProfile.tenant_id == tenant_id,
            MarketingStorageResourceProfile.is_default.is_(True),
        )
        return self.db.scalar(stmt)

    def create_storage_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        mode: MarketingStorageResourceMode,
        status: MarketingStorageProfileStatus,
        is_default: bool,
        display_name: str,
        max_upload_bytes: int | None,
        max_url_length: int | None,
        allowed_mime_types: list | None,
        created_by_user_id: uuid.UUID | None,
        updated_by_user_id: uuid.UUID | None,
    ) -> MarketingStorageResourceProfile:
        row = MarketingStorageResourceProfile(
            tenant_id=tenant_id,
            mode=mode,
            status=status,
            is_default=is_default,
            display_name=display_name,
            max_upload_bytes=max_upload_bytes,
            max_url_length=max_url_length,
            allowed_mime_types=allowed_mime_types,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=updated_by_user_id,
        )
        self.db.add(row)
        return row


# Backward-compatible alias used by topics service
MarketingTopicRepository = MarketingRepository
