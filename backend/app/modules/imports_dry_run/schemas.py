import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from app.modules.audit.schemas import ImportBatchEntitySummary, ImportBatchSummary


class IssueSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class DryRunIssue(BaseModel):
    entity: str
    issue_code: str
    severity: IssueSeverity
    row_ref: str
    message: str


class FinanceAggregateCheck(BaseModel):
    source_payments_total: Decimal
    mapped_payments_total: Decimal
    difference: Decimal
    passed: bool


class TenantBranchReadiness(BaseModel):
    tenant_ready: bool
    default_branch_ready: bool
    tenant_id: uuid.UUID | None = None
    default_branch_id: uuid.UUID | None = None
    passed: bool


class DryRunValidationReport(BaseModel):
    issues: list[DryRunIssue] = Field(default_factory=list)
    duplicate_warnings: int = 0
    orphan_warnings: int = 0
    unknown_status_warnings: int = 0
    required_field_errors: int = 0
    finance_check: FinanceAggregateCheck
    tenant_branch_readiness: TenantBranchReadiness


class SyntheticDryRunResult(BaseModel):
    summary: ImportBatchSummary
    report: DryRunValidationReport
    notes: str = "Synthetic dry-run only. No DB writes. No Core API/DB writes."


class SyntheticDryRunContext(BaseModel):
    tenant_id: uuid.UUID
    default_branch_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID | None = None
    source_system: str = "consult_app_synthetic"
    scenario_name: str = "default"


# Alias kept for C2b docs/call sites; same context contract.
ImportDryRunContext = SyntheticDryRunContext


def build_batch_summary(
    *,
    context: SyntheticDryRunContext,
    entities: list[ImportBatchEntitySummary],
    status_mapping_warnings: int,
    review_count: int,
    error_count: int,
    notes: str,
) -> ImportBatchSummary:
    total_source_rows = sum(item.source_count for item in entities)
    total_imported_rows = sum(item.imported_count for item in entities)
    total_skipped_rows = sum(item.skipped_count for item in entities)

    return ImportBatchSummary(
        id=uuid.uuid4(),
        tenant_id=context.tenant_id,
        created_by_user_id=context.created_by_user_id,
        source_system=context.source_system,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        total_source_rows=total_source_rows,
        total_imported_rows=total_imported_rows,
        total_skipped_rows=total_skipped_rows,
        total_error_rows=error_count,
        total_review_rows=review_count,
        status_mapping_warnings=status_mapping_warnings,
        entities=entities,
        notes=notes,
    )
