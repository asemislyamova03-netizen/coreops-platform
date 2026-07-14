"""Reset pack approval/preflight state after content changes."""

import uuid

from app.modules.marketing.enums import (
    MarketingApprovalStatus,
    MarketingPackStatus,
    MarketingPreflightStatus,
)
from app.modules.marketing.models import MarketingPublicationPack


def reset_pack_after_content_change(
    pack: MarketingPublicationPack,
    *,
    user_id: uuid.UUID | None = None,
) -> bool:
    """Return True if pack state was reset."""
    if (
        pack.status == MarketingPackStatus.DRAFT
        and pack.preflight_status == MarketingPreflightStatus.NOT_RUN
        and pack.approval_status == MarketingApprovalStatus.DRAFT
    ):
        return False

    pack.approval_status = MarketingApprovalStatus.DRAFT
    pack.preflight_status = MarketingPreflightStatus.NOT_RUN
    pack.status = MarketingPackStatus.DRAFT
    pack.approved_at = None
    pack.approved_by_user_id = None
    pack.preflight_at = None
    pack.preflight_report_json = {}
    if user_id is not None:
        pack.updated_by_user_id = user_id
    return True
