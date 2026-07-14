import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.marketing.enums import (
    DEFAULT_PACK_CHANNELS,
    MarketingChannel,
    MarketingTextStatus,
)
from app.modules.marketing.models import MarketingPublicationPack
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import PackTextResponse, PackTextUpsert
from app.modules.marketing.service.approval_reset import reset_pack_after_content_change


class MarketingTextService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def list_pack_texts(self, pack_id: uuid.UUID) -> list[PackTextResponse]:
        self._get_pack_or_404(pack_id)
        rows = self.repo.list_pack_texts(self.tenant_id, pack_id)
        return [PackTextResponse.model_validate(row) for row in rows]

    def upsert_pack_text(
        self,
        user: User,
        pack_id: uuid.UUID,
        channel: MarketingChannel,
        payload: PackTextUpsert,
    ) -> PackTextResponse:
        if channel not in DEFAULT_PACK_CHANNELS:
            from app.modules.marketing.exceptions import MarketingUnsupportedChannelError

            raise MarketingUnsupportedChannelError(channel.value)

        pack = self._get_pack_or_404(pack_id)
        row = self.repo.get_pack_text(self.tenant_id, pack_id, channel)

        if row is None:
            row = self.repo.create_text(
                tenant_id=self.tenant_id,
                pack_id=pack.id,
                channel=channel,
                text=payload.text,
                status=payload.status or MarketingTextStatus.DRAFT,
                char_count=len(payload.text),
                version=1,
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
            )
        else:
            row.text = payload.text
            row.char_count = len(payload.text)
            row.version += 1
            if payload.status is not None:
                row.status = payload.status
            else:
                row.status = MarketingTextStatus.DRAFT
            row.updated_by_user_id = user.id
            self.db.flush()

        reset_pack_after_content_change(pack, user_id=user.id)
        self.db.flush()

        return PackTextResponse.model_validate(row)

    def _get_pack_or_404(self, pack_id: uuid.UUID) -> MarketingPublicationPack:
        pack = self.repo.get_pack(self.tenant_id, pack_id)
        if pack is None:
            raise NotFoundError("Pack not found")
        return pack
