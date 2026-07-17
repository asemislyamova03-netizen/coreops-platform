import argparse
import json
import shutil
import sqlite3
import tempfile
import uuid
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.orm import configure_mappers

from app.modules.imports_dry_run.production_sqlite_fixture import (
    build_production_gate_b_sqlite_fixture,
)
from app.modules.imports_dry_run.real_source_allowlist import OutputPathError
from app.modules.imports_dry_run.staging_write_import_runner import (
    EXIT_PREFLIGHT_FAIL,
    REQUIRED_IMPORT_SEQUENCE,
    SOURCE_SYSTEM,
    STAGING_WRITE_EXECUTE_MODE,
    StagingWriteAdapter,
    STAGING_WRITE_PLAN_MODE,
    SourceIdentity,
    SourceRefConflictError,
    StagingWriteImportPreflightError,
    build_parser,
    build_batch_source_ref,
    build_source_ref,
    main,
    parse_masked_dry_run_report,
    resolve_conflict_action,
    run_staging_write_import,
    scan_output_payload_for_pii,
    validate_required_import_sequence,
    validate_staging_write_import_args,
)

_LOCAL_TMP_ROOT = Path(__file__).resolve().parent / "_staging_write_tmp"
_TENANT_ID = "2507e425-d4bc-432d-8f75-97fb69567de9"
_BRANCH_ID = "e85d837b-7951-4a61-9d69-d96d58010ced"
_BATCH_ID = "batch-20260709-1"
_BACKUP_ID = "consulting-gate-b-20260709-0734-asem"


@pytest.fixture()
def local_tmp() -> Path:
    _LOCAL_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    case_dir = _LOCAL_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=True)
    yield case_dir
    shutil.rmtree(case_dir, ignore_errors=True)


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _masked_report_payload() -> dict:
    return {
        "gate": "B",
        "mode": "real-source-readonly",
        "summary": {
            "total_source_rows": 1,
            "total_imported_rows": 1,
            "total_skipped_rows": 0,
            "total_error_rows": 0,
            "total_review_rows": 0,
        },
    }


def _write_masked_report(path: Path, payload: dict | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload or _masked_report_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _base_args(**overrides):
    values = {
        "mode": STAGING_WRITE_PLAN_MODE,
        "source_db": "/var/www/consult_app/instance/consulting_os.db",
        "backup_id": _BACKUP_ID,
        "tenant_id": _TENANT_ID,
        "default_branch_id": _BRANCH_ID,
        "target_db": "coreops_staging_0013",
        "dry_run_report": "/opt/flexity/import_work/reports/gate_b_masked.json",
        "import_batch_id": _BATCH_ID,
        "output": "/opt/flexity/import_work/reports/write_import_plan.json",
        "allow_execution": False,
        "overwrite": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_parser_requires_all_mandatory_flags():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_configure_mappers_passes_for_staging_write_runner_imports():
    # Regression guard for isolated CLI process: all relationship targets
    # (including ProviderStaff) must be resolvable after runner import.
    configure_mappers()


def test_runner_import_bootstraps_full_model_registry():
    import sys

    assert "app.modules.models" in sys.modules


def test_cli_fails_when_mode_wrong(repo_root: Path):
    with pytest.raises(StagingWriteImportPreflightError, match="staging-write-import-plan"):
        validate_staging_write_import_args(_base_args(mode="real-source-readonly"), repo_root=repo_root)


def test_cli_rejects_ambiguous_legacy_mode(repo_root: Path):
    with pytest.raises(StagingWriteImportPreflightError, match="Ambiguous mode"):
        validate_staging_write_import_args(_base_args(mode="staging-write-import"), repo_root=repo_root)


def test_cli_fails_when_target_db_not_staging(repo_root: Path, monkeypatch, local_tmp: Path):
    masked = _write_masked_report(local_tmp / "masked.json")
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.assert_path_allowlisted_for_real_source",
        lambda _path: Path(__file__).resolve(),
    )
    with pytest.raises(StagingWriteImportPreflightError, match="coreops_staging_0013"):
        validate_staging_write_import_args(
            _base_args(target_db="other_db", dry_run_report=str(masked), output=str(local_tmp / "out.json")),
            repo_root=repo_root,
        )


def test_cli_rejects_live_coreops_target(repo_root: Path, monkeypatch, local_tmp: Path):
    masked = _write_masked_report(local_tmp / "masked.json")
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.assert_path_allowlisted_for_real_source",
        lambda _path: Path(__file__).resolve(),
    )
    with pytest.raises(StagingWriteImportPreflightError, match="production-like|blocked"):
        validate_staging_write_import_args(
            _base_args(target_db="coreops", dry_run_report=str(masked), output=str(local_tmp / "out.json")),
            repo_root=repo_root,
        )


def test_cli_fails_if_dry_run_report_missing(repo_root: Path, monkeypatch, local_tmp: Path):
    missing = local_tmp / "missing.json"
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.assert_path_allowlisted_for_real_source",
        lambda _path: Path(__file__).resolve(),
    )
    with pytest.raises(StagingWriteImportPreflightError, match="not found"):
        validate_staging_write_import_args(
            _base_args(dry_run_report=str(missing), output=str(local_tmp / "out.json")),
            repo_root=repo_root,
        )


def test_cli_fails_if_dry_run_report_has_pii(local_tmp: Path):
    report = _write_masked_report(
        local_tmp / "masked_pii.json",
        payload={
            "gate": "B",
            "mode": "real-source-readonly",
            "summary": {"total_error_rows": 0},
            "extra": "contact user@example.com",
        },
    )
    with pytest.raises(StagingWriteImportPreflightError, match="PII"):
        parse_masked_dry_run_report(report)


def test_cli_fails_if_dry_run_report_has_error_rows(local_tmp: Path):
    report = _write_masked_report(
        local_tmp / "masked_error_rows.json",
        payload={
            "gate": "B",
            "mode": "real-source-readonly",
            "summary": {"total_error_rows": 1},
        },
    )
    with pytest.raises(StagingWriteImportPreflightError, match="error rows"):
        parse_masked_dry_run_report(report)


def test_source_ref_format_stable():
    source_ref = build_source_ref("orders", "123")
    assert source_ref == "legacy_consulting_os:orders:123"


def test_batch_source_ref_format_stable():
    source_ref = build_batch_source_ref("batch-1", "orders", "123")
    assert source_ref == "legacy_consulting_os:batch-1:orders:123"


def test_pii_scan_allows_technical_identifiers():
    payload = {
        "import_batch_id": "consulting-staging-import-20260709-001",
        "tenant_id": _TENANT_ID,
        "default_branch_id": _BRANCH_ID,
        "backup_id": _BACKUP_ID,
        "source_ref": "legacy_consulting_os:orders:123",
    }
    assert scan_output_payload_for_pii(payload) == []


def test_pii_scan_blocks_phone_like_in_unsafe_field():
    payload = {"note": "+7 700 000 00 00"}
    findings = scan_output_payload_for_pii(payload)
    assert any("phone-like pattern" in item for item in findings)


def test_pii_scan_blocks_email_like_in_unsafe_field():
    payload = {"note": "user@example.com"}
    findings = scan_output_payload_for_pii(payload)
    assert any("email-like pattern" in item for item in findings)


def test_pii_scan_fails_technical_identifier_with_email():
    payload = {"import_batch_id": "batch-user@example.com"}
    findings = scan_output_payload_for_pii(payload)
    assert any("email-like pattern" in item or "technical_identifier_email_like" in item for item in findings)


def test_conflict_policy_skip_existing_by_source_ref():
    incoming = SourceIdentity(
        source_system=SOURCE_SYSTEM,
        source_table="orders",
        source_id="1",
        tenant_id=UUID(_TENANT_ID),
        import_batch_id=_BATCH_ID,
    )
    existing = [incoming]
    assert resolve_conflict_action(existing, incoming) == "skip_existing"


def test_conflict_policy_fail_on_ambiguous_duplicate():
    incoming = SourceIdentity(
        source_system=SOURCE_SYSTEM,
        source_table="orders",
        source_id="1",
        tenant_id=UUID(_TENANT_ID),
        import_batch_id=_BATCH_ID,
    )
    existing = [incoming, incoming]
    with pytest.raises(SourceRefConflictError, match="Ambiguous"):
        resolve_conflict_action(existing, incoming)


def test_conflict_policy_fail_on_tenant_mismatch():
    incoming = SourceIdentity(
        source_system=SOURCE_SYSTEM,
        source_table="orders",
        source_id="1",
        tenant_id=UUID(_TENANT_ID),
        import_batch_id=_BATCH_ID,
    )
    existing = [
        SourceIdentity(
            source_system=SOURCE_SYSTEM,
            source_table="orders",
            source_id="1",
            tenant_id=UUID("00000000-0000-0000-0000-000000000999"),
            import_batch_id=_BATCH_ID,
        )
    ]
    with pytest.raises(SourceRefConflictError, match="Tenant mismatch"):
        resolve_conflict_action(existing, incoming)


def test_import_order_is_enforced():
    validate_required_import_sequence(list(REQUIRED_IMPORT_SEQUENCE))
    with pytest.raises(StagingWriteImportPreflightError, match="Import order mismatch"):
        validate_required_import_sequence(list(reversed(REQUIRED_IMPORT_SEQUENCE)))


def test_business_policy_mappings_from_planned_summary(local_tmp: Path):
    db_path = build_production_gate_b_sqlite_fixture(local_tmp / "prod_like.sqlite")
    # force one orphan payment and one mismatched order
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE payments SET order_id=NULL WHERE id=1")
        conn.execute("UPDATE orders SET total_amount='1' WHERE id=1")
        conn.commit()
    finally:
        conn.close()

    from app.modules.imports_dry_run.staging_write_import_runner import StagingWriteImportConfig

    config = StagingWriteImportConfig(
        source_db=db_path,
        backup_id=_BACKUP_ID,
        tenant_id=UUID(_TENANT_ID),
        default_branch_id=UUID(_BRANCH_ID),
        target_db="coreops_staging_0013",
        dry_run_report=local_tmp / "masked.json",
        import_batch_id=_BATCH_ID,
        output=local_tmp / "out.json",
        mode=STAGING_WRITE_PLAN_MODE,
    )
    from app.modules.imports_dry_run import sqlite_readonly

    original_guard = sqlite_readonly.assert_path_allowlisted_for_real_source
    sqlite_readonly.assert_path_allowlisted_for_real_source = lambda _p: Path(db_path)
    try:
        report = run_staging_write_import(config, allow_execution=False)
    finally:
        sqlite_readonly.assert_path_allowlisted_for_real_source = original_guard
    assert report["required_execution_sequence"] == REQUIRED_IMPORT_SEQUENCE
    assert report["writes_executed"] is False
    assert report["execution_allowed"] is False
    assert report["verdict"] == "PLAN_ONLY"
    assert report["business_policy"]["orphan_payments_standalone_historical"] is True
    assert report["business_policy"]["orphan_payments_needs_review"] is True
    assert report["business_policy"]["orphan_payments_relation_status"] == "unlinked_legacy_payment"
    assert report["business_policy"]["amount_needs_review_orders"] > 0
    assert report["business_policy"]["missing_template_fallback"] == "legacy_unknown_template"


def test_main_blocks_allow_execution_without_separate_gate(local_tmp: Path, monkeypatch):
    db_path = build_production_gate_b_sqlite_fixture(local_tmp / "prod_like.sqlite")
    masked = _write_masked_report(local_tmp / "masked.json")
    out = local_tmp / "out.json"
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.assert_path_allowlisted_for_real_source",
        lambda _path: db_path,
    )
    code = main(
        [
            "--mode",
            STAGING_WRITE_PLAN_MODE,
            "--source-db",
            "/var/www/consult_app/instance/consulting_os.db",
            "--backup-id",
            _BACKUP_ID,
            "--tenant-id",
            _TENANT_ID,
            "--default-branch-id",
            _BRANCH_ID,
            "--target-db",
            "coreops_staging_0013",
            "--dry-run-report",
            str(masked),
            "--import-batch-id",
            _BATCH_ID,
            "--output",
            str(out),
            "--allow-execution",
        ]
    )
    assert code == EXIT_PREFLIGHT_FAIL
    assert not out.exists()


def test_execute_mode_without_write_adapter_returns_nonzero(local_tmp: Path, monkeypatch):
    db_path = build_production_gate_b_sqlite_fixture(local_tmp / "prod_like.sqlite")
    masked = _write_masked_report(local_tmp / "masked.json")
    out = local_tmp / "out.json"
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.assert_path_allowlisted_for_real_source",
        lambda _path: db_path,
    )
    code = main(
        [
            "--mode",
            STAGING_WRITE_EXECUTE_MODE,
            "--source-db",
            "/var/www/consult_app/instance/consulting_os.db",
            "--backup-id",
            _BACKUP_ID,
            "--tenant-id",
            _TENANT_ID,
            "--default-branch-id",
            _BRANCH_ID,
            "--target-db",
            "coreops_staging_0013",
            "--dry-run-report",
            str(masked),
            "--import-batch-id",
            _BATCH_ID,
            "--output",
            str(out),
        ]
    )
    assert code == EXIT_PREFLIGHT_FAIL
    assert not out.exists()


def test_execute_mode_uses_injected_adapter(local_tmp: Path):
    db_path = build_production_gate_b_sqlite_fixture(local_tmp / "prod_like.sqlite")

    from app.modules.imports_dry_run.staging_write_import_runner import StagingWriteImportConfig

    config = StagingWriteImportConfig(
        source_db=db_path,
        backup_id=_BACKUP_ID,
        tenant_id=UUID(_TENANT_ID),
        default_branch_id=UUID(_BRANCH_ID),
        target_db="coreops_staging_0013",
        dry_run_report=local_tmp / "masked.json",
        import_batch_id=_BATCH_ID,
        output=local_tmp / "out.json",
        mode=STAGING_WRITE_EXECUTE_MODE,
    )

    class _Adapter(StagingWriteAdapter):
        def __init__(self):
            self.called = False

        def run(self, cfg, data):
            self.called = True
            assert cfg.mode == STAGING_WRITE_EXECUTE_MODE
            assert "orders" in data
            return {"writes_executed": True, "verdict": "EXECUTED_STAGING_ONLY"}

    adapter = _Adapter()
    from app.modules.imports_dry_run import sqlite_readonly

    original_guard = sqlite_readonly.assert_path_allowlisted_for_real_source
    sqlite_readonly.assert_path_allowlisted_for_real_source = lambda _p: Path(db_path)
    try:
        report = run_staging_write_import(config, allow_execution=True, write_adapter=adapter)
    finally:
        sqlite_readonly.assert_path_allowlisted_for_real_source = original_guard
    assert adapter.called is True
    assert report["writes_executed"] is True


def test_execute_mode_requires_allow_execution(local_tmp: Path):
    db_path = build_production_gate_b_sqlite_fixture(local_tmp / "prod_like.sqlite")
    from app.modules.imports_dry_run.staging_write_import_runner import StagingWriteImportConfig

    config = StagingWriteImportConfig(
        source_db=db_path,
        backup_id=_BACKUP_ID,
        tenant_id=UUID(_TENANT_ID),
        default_branch_id=UUID(_BRANCH_ID),
        target_db="coreops_staging_0013",
        dry_run_report=local_tmp / "masked.json",
        import_batch_id=_BATCH_ID,
        output=local_tmp / "out.json",
        mode=STAGING_WRITE_EXECUTE_MODE,
    )
    with pytest.raises(StagingWriteImportPreflightError, match="APPROVAL_REQUIRED"):
        run_staging_write_import(config, allow_execution=False)


def test_plan_mode_returns_zero_and_writes_executed_false(local_tmp: Path, monkeypatch):
    db_path = build_production_gate_b_sqlite_fixture(local_tmp / "prod_like.sqlite")
    masked = _write_masked_report(local_tmp / "masked.json")
    out = Path(tempfile.gettempdir()) / f"staging_write_out_{uuid.uuid4().hex}.json"
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.assert_path_allowlisted_for_real_source",
        lambda _path: db_path,
    )
    monkeypatch.setattr(
        "app.modules.imports_dry_run.sqlite_readonly.assert_path_allowlisted_for_real_source",
        lambda _path: db_path,
    )
    code = main(
        [
            "--mode",
            STAGING_WRITE_PLAN_MODE,
            "--source-db",
            "/var/www/consult_app/instance/consulting_os.db",
            "--backup-id",
            _BACKUP_ID,
            "--tenant-id",
            _TENANT_ID,
            "--default-branch-id",
            _BRANCH_ID,
            "--target-db",
            "coreops_staging_0013",
            "--dry-run-report",
            str(masked),
            "--import-batch-id",
            _BATCH_ID,
            "--output",
            str(out),
        ]
    )
    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["writes_executed"] is False
    assert report["verdict"] == "PLAN_ONLY"


def test_coreops_staging_target_is_accepted(repo_root: Path, monkeypatch, local_tmp: Path):
    masked = _write_masked_report(local_tmp / "masked.json")
    out = Path(tempfile.gettempdir()) / f"staging_write_accept_{uuid.uuid4().hex}.json"
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.assert_path_allowlisted_for_real_source",
        lambda _path: Path(__file__).resolve(),
    )
    cfg = validate_staging_write_import_args(
        _base_args(target_db="coreops_staging_0013", dry_run_report=str(masked), output=str(out)),
        repo_root=repo_root,
    )
    assert cfg.target_db == "coreops_staging_0013"


def test_output_path_inside_repo_rejected(repo_root: Path, monkeypatch, local_tmp: Path):
    masked = _write_masked_report(local_tmp / "masked.json")
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.assert_path_allowlisted_for_real_source",
        lambda _path: Path(__file__).resolve(),
    )
    inside_repo = repo_root / "tests" / "_staging_write_tmp" / "out.json"
    with pytest.raises(OutputPathError, match="git repository"):
        validate_staging_write_import_args(
            _base_args(dry_run_report=str(masked), output=str(inside_repo)),
            repo_root=repo_root,
        )


def _seed_staging_tenant_branch(db_session) -> tuple[UUID, UUID]:
    from app.core.enums import TenantStatus
    from app.modules.branches.models import Branch
    from app.modules.provider.models import ProviderCompany
    from app.modules.tenants.models import Tenant

    tenant_id = UUID(_TENANT_ID)
    branch_id = UUID(_BRANCH_ID)
    if db_session.get(Tenant, tenant_id) is not None:
        return tenant_id, branch_id

    provider = ProviderCompany(
        name="Staging Write Import Provider",
        slug=f"staging-write-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(provider)
    db_session.flush()

    tenant = Tenant(
        id=tenant_id,
        provider_company_id=provider.id,
        name="Consulting Staging Tenant",
        slug=f"consulting-staging-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.flush()

    branch = Branch(
        id=branch_id,
        tenant_id=tenant_id,
        code="main",
        name="Main Branch",
        is_active=True,
        is_default=True,
    )
    db_session.add(branch)
    # Flush branch first so SQLite can satisfy tenants.default_branch_id → branches.id
    # (circular FK with branches.tenant_id → tenants.id).
    db_session.flush()
    tenant.default_branch_id = branch_id
    db_session.commit()
    return tenant_id, branch_id


def _adapter_execute_config(local_tmp: Path) -> "StagingWriteImportConfig":
    from app.modules.imports_dry_run.staging_write_import_runner import StagingWriteImportConfig

    return StagingWriteImportConfig(
        source_db=local_tmp / "unused.sqlite",
        backup_id=_BACKUP_ID,
        tenant_id=UUID(_TENANT_ID),
        default_branch_id=UUID(_BRANCH_ID),
        target_db="coreops_staging_0013",
        dry_run_report=local_tmp / "masked.json",
        import_batch_id=_BATCH_ID,
        output=local_tmp / "out.json",
        mode=STAGING_WRITE_EXECUTE_MODE,
    )


def test_sqlalchemy_adapter_run_avoids_nested_begin_on_active_session(db_engine, db_session, local_tmp):
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session, sessionmaker

    from app.core.enums import AuditAction
    from app.modules.audit.models import AuditLog
    from app.modules.imports_dry_run.staging_write_import_runner import (
        SqlAlchemyStagingWriteAdapter,
        StageResult,
    )

    _seed_staging_tenant_branch(db_session)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    adapter = SqlAlchemyStagingWriteAdapter(session_factory=factory, verify_target_db=False)
    config = _adapter_execute_config(local_tmp)

    session_begin_calls: list[bool] = []
    original_begin = Session.begin

    def tracked_begin(self, nested: bool = False):
        session_begin_calls.append(nested)
        return original_begin(self, nested=nested)

    Session.begin = tracked_begin
    try:

        def _fake_execute(db, cfg, _data, _stats):
            db.add(
                AuditLog(
                    tenant_id=cfg.tenant_id,
                    action=AuditAction.EXECUTE,
                    entity_type="legacy_import_batch",
                    summary=f"batch:{cfg.import_batch_id}",
                    metadata_json={"import_batch_id": cfg.import_batch_id},
                )
            )
            return [StageResult("import_batch_audit_context", imported=1)]

        adapter._execute_import_order = _fake_execute  # type: ignore[method-assign]
        report = adapter.run(config, {})
    finally:
        Session.begin = original_begin

    assert report["writes_executed"] is True
    assert session_begin_calls.count(False) <= 1

    with factory() as verify:
        count = verify.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.tenant_id == UUID(_TENANT_ID),
                AuditLog.entity_type == "legacy_import_batch",
            )
        )
        assert count == 1


def test_sqlalchemy_adapter_write_transaction_commits_on_success(db_engine, db_session, local_tmp):
    from sqlalchemy import func, select
    from sqlalchemy.orm import sessionmaker

    from app.core.enums import AuditAction
    from app.modules.audit.models import AuditLog
    from app.modules.imports_dry_run.staging_write_import_runner import (
        SqlAlchemyStagingWriteAdapter,
        StageResult,
    )

    _seed_staging_tenant_branch(db_session)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    adapter = SqlAlchemyStagingWriteAdapter(session_factory=factory, verify_target_db=False)
    config = _adapter_execute_config(local_tmp)

    def _fake_execute(db, cfg, _data, _stats):
        db.add(
            AuditLog(
                tenant_id=cfg.tenant_id,
                action=AuditAction.EXECUTE,
                entity_type="legacy_import_batch",
                summary=f"batch:{cfg.import_batch_id}",
                metadata_json={"import_batch_id": cfg.import_batch_id},
            )
        )
        return [StageResult("import_batch_audit_context", imported=1)]

    adapter._execute_import_order = _fake_execute  # type: ignore[method-assign]
    adapter.run(config, {})

    with factory() as verify:
        count = verify.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.tenant_id == UUID(_TENANT_ID),
                AuditLog.entity_type == "legacy_import_batch",
            )
        )
        assert count == 1


def test_sqlalchemy_adapter_write_transaction_rolls_back_on_stage_failure(db_engine, db_session, local_tmp):
    from sqlalchemy import func, select
    from sqlalchemy.orm import sessionmaker

    from app.core.enums import AuditAction
    from app.modules.audit.models import AuditLog
    from app.modules.imports_dry_run.staging_write_import_runner import (
        SqlAlchemyStagingWriteAdapter,
        StageResult,
    )

    _seed_staging_tenant_branch(db_session)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    adapter = SqlAlchemyStagingWriteAdapter(session_factory=factory, verify_target_db=False)
    config = _adapter_execute_config(local_tmp)

    def _failing_execute(db, cfg, _data, _stats):
        db.add(
            AuditLog(
                tenant_id=cfg.tenant_id,
                action=AuditAction.EXECUTE,
                entity_type="legacy_import_batch",
                summary=f"batch:{cfg.import_batch_id}",
                metadata_json={"import_batch_id": cfg.import_batch_id},
            )
        )
        db.flush()
        raise RuntimeError("simulated stage failure")

    adapter._execute_import_order = _failing_execute  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="simulated stage failure"):
        adapter.run(config, {})

    with factory() as verify:
        count = verify.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.tenant_id == UUID(_TENANT_ID),
                AuditLog.entity_type == "legacy_import_batch",
            )
        )
        assert count == 0


def test_resolve_consulting_staging_url_missing_fails_closed():
    from app.modules.imports_dry_run.staging_write_import_runner import (
        CONSULTING_STAGING_DATABASE_URL_ENV,
        resolve_consulting_staging_database_url,
    )

    with pytest.raises(StagingWriteImportPreflightError, match=CONSULTING_STAGING_DATABASE_URL_ENV):
        resolve_consulting_staging_database_url(environ={})


def test_resolve_consulting_staging_url_ignores_database_url_fallback():
    from app.modules.imports_dry_run.staging_write_import_runner import (
        CONSULTING_STAGING_DATABASE_URL_ENV,
        resolve_consulting_staging_database_url,
    )

    secret = "postgresql+psycopg://user:SuperSecretPass@localhost:5432/coreops"
    with pytest.raises(StagingWriteImportPreflightError, match=CONSULTING_STAGING_DATABASE_URL_ENV) as exc:
        resolve_consulting_staging_database_url(
            environ={"DATABASE_URL": secret},
        )
    assert "SuperSecretPass" not in str(exc.value)
    assert secret not in str(exc.value)


def test_redact_database_url_strips_credentials():
    from app.modules.imports_dry_run.staging_write_import_runner import _redact_database_url

    raw = "postgresql+psycopg://alice:hunter2@db.example:5432/coreops_staging_0013"
    redacted = _redact_database_url(raw)
    assert "hunter2" not in redacted
    assert "alice" not in redacted
    assert "***" in redacted


def test_assert_connected_database_mismatch_fails_closed():
    from types import SimpleNamespace

    from app.modules.imports_dry_run.staging_write_import_runner import (
        assert_connected_database_matches_target,
    )

    class _FakeBind:
        dialect = SimpleNamespace(name="postgresql")

    class _FakeSession:
        def get_bind(self):
            return _FakeBind()

        def execute(self, _stmt):
            return SimpleNamespace(scalar=lambda: "coreops")

    with pytest.raises(StagingWriteImportPreflightError, match="production-like|does not match"):
        assert_connected_database_matches_target(_FakeSession(), "coreops_staging_0013")


def test_assert_connected_database_name_mismatch_message_has_no_url():
    from types import SimpleNamespace

    from app.modules.imports_dry_run.staging_write_import_runner import (
        assert_connected_database_matches_target,
    )

    class _FakeBind:
        dialect = SimpleNamespace(name="postgresql")

    class _FakeSession:
        def get_bind(self):
            return _FakeBind()

        def execute(self, _stmt):
            return SimpleNamespace(scalar=lambda: "coreops_staging_other")

    with pytest.raises(StagingWriteImportPreflightError, match="does not match") as exc:
        assert_connected_database_matches_target(_FakeSession(), "coreops_staging_0013")
    message = str(exc.value)
    assert "postgresql" not in message.lower() or "://" not in message
    assert "password" not in message.lower()
    assert "@" not in message


def test_execute_mode_without_staging_url_fails_closed(local_tmp: Path, monkeypatch):
    db_path = build_production_gate_b_sqlite_fixture(local_tmp / "prod_like.sqlite")
    from app.modules.imports_dry_run.staging_write_import_runner import (
        CONSULTING_STAGING_DATABASE_URL_ENV,
        StagingWriteImportConfig,
        run_staging_write_import,
    )

    monkeypatch.delenv(CONSULTING_STAGING_DATABASE_URL_ENV, raising=False)
    secret = "postgresql+psycopg://user:LeakMeNot@localhost:5432/coreops"
    monkeypatch.setenv("DATABASE_URL", secret)

    config = StagingWriteImportConfig(
        source_db=db_path,
        backup_id=_BACKUP_ID,
        tenant_id=UUID(_TENANT_ID),
        default_branch_id=UUID(_BRANCH_ID),
        target_db="coreops_staging_0013",
        dry_run_report=local_tmp / "masked.json",
        import_batch_id=_BATCH_ID,
        output=local_tmp / "out.json",
        mode=STAGING_WRITE_EXECUTE_MODE,
    )
    from app.modules.imports_dry_run import sqlite_readonly

    original_guard = sqlite_readonly.assert_path_allowlisted_for_real_source
    sqlite_readonly.assert_path_allowlisted_for_real_source = lambda _p: Path(db_path)
    try:
        with pytest.raises(StagingWriteImportPreflightError, match=CONSULTING_STAGING_DATABASE_URL_ENV) as exc:
            run_staging_write_import(
                config,
                allow_execution=True,
                environ={"DATABASE_URL": secret},
            )
    finally:
        sqlite_readonly.assert_path_allowlisted_for_real_source = original_guard
    assert "LeakMeNot" not in str(exc.value)


def test_build_staging_engine_rejects_db_name_mismatch(monkeypatch):
    from types import SimpleNamespace

    from app.modules.imports_dry_run.staging_write_import_runner import (
        CONSULTING_STAGING_DATABASE_URL_ENV,
        build_consulting_staging_engine,
    )

    class _Result:
        def scalar(self):
            return "coreops"

    class _ConnSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def execute(self, _stmt):
            return _Result()

    class _Engine:
        def dispose(self):
            return None

    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.create_engine",
        lambda *_a, **_k: _Engine(),
    )
    monkeypatch.setattr(
        "app.modules.imports_dry_run.staging_write_import_runner.Session",
        lambda _engine: _ConnSession(),
    )
    with pytest.raises(StagingWriteImportPreflightError, match="production-like|does not match"):
        build_consulting_staging_engine(
            "coreops_staging_0013",
            environ={
                CONSULTING_STAGING_DATABASE_URL_ENV: (
                    "postgresql+psycopg://u:p@localhost:5432/coreops_staging_0013"
                )
            },
        )


def test_staging_url_database_name_mismatch_fails_before_connect():
    from app.modules.imports_dry_run.staging_write_import_runner import (
        CONSULTING_STAGING_DATABASE_URL_ENV,
        assert_staging_url_database_name_matches_target,
    )

    secret = "postgresql+psycopg://u:LeakPath@localhost:5432/coreops"
    with pytest.raises(StagingWriteImportPreflightError, match="production-like|does not match") as exc:
        assert_staging_url_database_name_matches_target(secret, "coreops_staging_0013")
    assert "LeakPath" not in str(exc.value)
    assert CONSULTING_STAGING_DATABASE_URL_ENV in str(exc.value) or "production-like" in str(exc.value)


def test_staging_url_path_must_match_target_db():
    from app.modules.imports_dry_run.staging_write_import_runner import (
        assert_staging_url_database_name_matches_target,
    )

    ok = assert_staging_url_database_name_matches_target(
        "postgresql+psycopg://u:p@localhost:5432/coreops_staging_0013",
        "coreops_staging_0013",
    )
    assert ok == "coreops_staging_0013"
    with pytest.raises(StagingWriteImportPreflightError, match="does not match"):
        assert_staging_url_database_name_matches_target(
            "postgresql+psycopg://u:p@localhost:5432/coreops_staging_other",
            "coreops_staging_0013",
        )


def test_ephemeral_postgres_current_database_gate():
    """Live current_database() check when local Postgres is reachable."""
    import os

    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    from app.core.config import get_settings
    from app.modules.imports_dry_run.staging_write_import_runner import (
        CONSULTING_STAGING_DATABASE_URL_ENV,
        assert_connected_database_matches_target,
        build_consulting_staging_engine,
    )

    base_url = os.environ.get(CONSULTING_STAGING_DATABASE_URL_ENV) or get_settings().database_url
    try:
        engine = create_engine(base_url, pool_pre_ping=True)
        with engine.connect() as conn:
            if conn.dialect.name != "postgresql":
                pytest.skip("PostgreSQL required for ephemeral current_database gate")
            current = conn.execute(text("SELECT current_database()")).scalar()
        engine.dispose()
    except OperationalError:
        pytest.skip("Local Postgres is required for ephemeral current_database gate")

    if current == "coreops_staging_0013":
        built = build_consulting_staging_engine(
            "coreops_staging_0013",
            environ={CONSULTING_STAGING_DATABASE_URL_ENV: base_url},
        )
        built.dispose()
        return

    # Connected DB is not the allowed staging name → fail closed.
    with Session(create_engine(base_url)) as session:
        with pytest.raises(StagingWriteImportPreflightError, match="production-like|does not match"):
            assert_connected_database_matches_target(session, "coreops_staging_0013")


def test_parser_help_separates_plan_and_execute():
    parser = build_parser()
    help_text = parser.format_help()
    assert "staging-write-import-plan" in help_text
    assert "staging-write-import-execute" in help_text
    assert "CONSULTING_STAGING_DATABASE_URL" in help_text
    assert "DATABASE_URL" in help_text
    assert "dry-run" in help_text.lower() or "Gate B" in help_text

