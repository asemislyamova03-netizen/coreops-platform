from decimal import Decimal

from app.core.enums import DocumentStatus, PaymentDirection, PaymentStatus, WorkItemStatus
from app.modules.documents.schemas import (
    LegacyContractImportInput,
    assess_legacy_contract_import,
    map_legacy_contract_status,
)
from app.modules.finance.schemas import map_legacy_payment_type
from app.modules.workflows.service import map_legacy_order_status, map_legacy_stage_status


def test_map_legacy_order_status_known_values():
    status, needs_review = map_legacy_order_status("COMPLETED")
    assert status == WorkItemStatus.WON
    assert needs_review is False

    status, needs_review = map_legacy_order_status("CANCELLED")
    assert status == WorkItemStatus.CANCELLED
    assert needs_review is False


def test_map_legacy_order_status_unknown_goes_to_review():
    status, needs_review = map_legacy_order_status("SOMETHING_ELSE")
    assert status == WorkItemStatus.OPEN
    assert needs_review is True


def test_map_legacy_stage_status_known_and_unknown():
    mapped, needs_review = map_legacy_stage_status("NOT_STARTED")
    assert mapped == "not_started"
    assert needs_review is False

    mapped, needs_review = map_legacy_stage_status(None)
    assert mapped == "needs_review"
    assert needs_review is True


def test_map_legacy_contract_status_and_assessment():
    status, needs_review = map_legacy_contract_status("SIGNED")
    assert status == DocumentStatus.SIGNED
    assert needs_review is False

    assessment = assess_legacy_contract_import(
        LegacyContractImportInput(legacy_status="UNKNOWN", work_item_id=None, amount=Decimal("0"))
    )
    assert assessment.target_status == DocumentStatus.DRAFT
    assert assessment.status_needs_review is True
    assert assessment.link_needs_review is True
    assert assessment.amount_needs_review is True


def test_map_legacy_payment_type_contract():
    direction, status, needs_review = map_legacy_payment_type("INCOME")
    assert direction == PaymentDirection.INCOMING
    assert status == PaymentStatus.COMPLETED
    assert needs_review is False

    direction, status, needs_review = map_legacy_payment_type("EXPENSE")
    assert direction == PaymentDirection.OUTGOING
    assert status == PaymentStatus.COMPLETED
    assert needs_review is False

    direction, status, needs_review = map_legacy_payment_type("UNKNOWN")
    assert direction == PaymentDirection.NEEDS_REVIEW
    assert status == PaymentStatus.PENDING
    assert needs_review is True
