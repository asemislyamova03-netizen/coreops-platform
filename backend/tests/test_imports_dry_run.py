import uuid

from app.modules.imports_dry_run.pipeline import (
    DryRunNoOpTargetAdapter,
    SyntheticDryRunPipeline,
    SyntheticSourceAdapter,
)
from app.modules.imports_dry_run.schemas import SyntheticDryRunContext
from app.modules.imports_dry_run.synthetic_fixtures import build_consulting_synthetic_fixture


def _run_default_scenario():
    pipeline = SyntheticDryRunPipeline(
        source=SyntheticSourceAdapter(build_consulting_synthetic_fixture()),
        target=DryRunNoOpTargetAdapter(),
    )
    result = pipeline.run(
        SyntheticDryRunContext(
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000123"),
            default_branch_id=uuid.UUID("00000000-0000-0000-0000-000000000125"),
            created_by_user_id=uuid.UUID("00000000-0000-0000-0000-000000000124"),
            scenario_name="pytest_default",
        )
    )
    return pipeline, result


def test_dry_run_generates_summary_without_db_writes():
    pipeline, result = _run_default_scenario()

    assert result.summary.total_source_rows > 0
    assert result.summary.total_imported_rows >= 0
    assert result.summary.source_system == "consult_app_synthetic"
    assert "No DB writes" in result.notes
    assert result.report.tenant_branch_readiness.passed is True

    endpoints = {item.endpoint for item in pipeline.target.endpoint_checks}
    assert "/api/v1/tenants" in endpoints
    assert "/api/v1/parties" in endpoints
    assert "/api/v1/catalog/items" in endpoints
    assert "/api/v1/work-items" in endpoints
    assert "/api/v1/documents/import" in endpoints
    assert "/api/v1/finance/payments" in endpoints
    endpoint_status = {item.endpoint: item.status for item in pipeline.target.endpoint_checks}
    assert endpoint_status["/api/v1/documents/import"] == "ready"
    assert endpoint_status["/api/v1/finance/payments"] == "ready"


def test_dry_run_covers_validation_rules_and_warnings():
    _, result = _run_default_scenario()
    codes = {issue.issue_code for issue in result.report.issues}

    assert "duplicate_login" in codes
    assert "unknown_status" in codes
    assert "unknown_stage_status" in codes
    assert "missing_template_id" in codes
    assert "null_order_link" in codes
    assert "zero_amount" in codes
    assert "unknown_payment_type" in codes
    assert result.report.orphan_warnings > 0
    assert result.report.unknown_status_warnings > 0


def test_dry_run_finance_aggregate_check():
    _, result = _run_default_scenario()
    assert result.report.finance_check.passed is True
    assert result.report.finance_check.difference == 0


def test_dry_run_fails_without_default_branch_id():
    pipeline = SyntheticDryRunPipeline(
        source=SyntheticSourceAdapter(build_consulting_synthetic_fixture()),
        target=DryRunNoOpTargetAdapter(),
    )
    result = pipeline.run(
        SyntheticDryRunContext(
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000123"),
            default_branch_id=None,
            scenario_name="pytest_missing_branch",
        )
    )
    codes = {issue.issue_code for issue in result.report.issues}
    assert "missing_default_branch_id" in codes
    assert result.report.tenant_branch_readiness.passed is False
