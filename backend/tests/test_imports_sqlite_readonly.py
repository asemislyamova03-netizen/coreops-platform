import shutil
import sqlite3
import uuid
from pathlib import Path

import pytest

from app.modules.imports_dry_run.masking import assert_no_raw_pii, mask_row_for_log, mask_value
from app.modules.imports_dry_run.pipeline import DryRunNoOpTargetAdapter, SyntheticDryRunPipeline
from app.modules.imports_dry_run.schema_fingerprint import (
    EXPECTED_SCHEMA_FINGERPRINT,
    SchemaMismatchError,
    assert_schema_matches_expected,
    compute_schema_fingerprint,
)
from app.modules.imports_dry_run.schemas import SyntheticDryRunContext
from app.modules.imports_dry_run.sqlite_readonly import (
    BlockedSqlitePathError,
    SqliteWriteAttemptError,
    assert_connection_is_readonly,
    open_readonly_sqlite,
)
from app.modules.imports_dry_run.sqlite_source_adapter import ReadonlySqliteSourceAdapter
from app.modules.imports_dry_run.synthetic_fixtures import build_consulting_synthetic_fixture
from app.modules.imports_dry_run.synthetic_sqlite_fixture import build_synthetic_sqlite_fixture

# Avoid pytest tmp_path on Windows when Temp path has restricted unicode user folders.
_LOCAL_TMP_ROOT = Path(__file__).resolve().parent / "_c2b_tmp"


@pytest.fixture()
def local_tmp() -> Path:
    _LOCAL_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    case_dir = _LOCAL_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=True)
    yield case_dir
    shutil.rmtree(case_dir, ignore_errors=True)


@pytest.fixture()
def synthetic_sqlite(local_tmp: Path) -> Path:
    path = local_tmp / "consulting_legacy_min.sqlite"
    return build_synthetic_sqlite_fixture(path)


def test_build_fixture_fingerprint_matches_expected(synthetic_sqlite: Path):
    conn = sqlite3.connect(synthetic_sqlite)
    try:
        assert compute_schema_fingerprint(conn) == EXPECTED_SCHEMA_FINGERPRINT
        assert_schema_matches_expected(conn)
    finally:
        conn.close()


def test_readonly_connection_rejects_writes(synthetic_sqlite: Path):
    conn = open_readonly_sqlite(synthetic_sqlite)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO users(id, login, is_active) VALUES ('x', 'y', 1)")
        assert_connection_is_readonly(conn)
    finally:
        conn.close()


def test_writable_connection_fails_readonly_assert(local_tmp: Path):
    path = local_tmp / "writable.sqlite"
    build_synthetic_sqlite_fixture(path)
    conn = sqlite3.connect(path)
    try:
        with pytest.raises(SqliteWriteAttemptError):
            assert_connection_is_readonly(conn)
    finally:
        conn.close()


def test_blocks_production_path_pattern(local_tmp: Path):
    fake = local_tmp / "consulting_os.db"
    fake.write_bytes(b"")
    with pytest.raises(BlockedSqlitePathError):
        open_readonly_sqlite(fake)


def test_adapter_output_matches_synthetic_domains(synthetic_sqlite: Path):
    adapter = ReadonlySqliteSourceAdapter(synthetic_sqlite)
    data = adapter.load()
    expected = build_consulting_synthetic_fixture()
    assert set(data) == set(expected)
    assert adapter.source_system == "legacy_consult_app"
    assert data["users"][0]["login"] == expected["users"][0]["login"]
    assert data["payments"][0]["amount"] == expected["payments"][0]["amount"]
    assert adapter.last_schema_fingerprint == EXPECTED_SCHEMA_FINGERPRINT


def test_adapter_feeds_c2a_pipeline_without_core_writes(synthetic_sqlite: Path):
    source = ReadonlySqliteSourceAdapter(synthetic_sqlite)
    pipeline = SyntheticDryRunPipeline(source=source, target=DryRunNoOpTargetAdapter())
    result = pipeline.run(
        SyntheticDryRunContext(
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000301"),
            default_branch_id=uuid.UUID("00000000-0000-0000-0000-000000000302"),
            source_system="legacy_consult_app",
            scenario_name="c2b_pytest",
        )
    )
    assert result.summary.source_system == "legacy_consult_app"
    assert result.summary.total_source_rows > 0
    assert result.report.finance_check.passed is True
    endpoints = {item.endpoint for item in pipeline.target.endpoint_checks}
    assert "/api/v1/parties" in endpoints
    assert pipeline.target.payload_counts["/api/v1/parties"] >= 1


def test_batching_max_rows_per_table(synthetic_sqlite: Path):
    adapter = ReadonlySqliteSourceAdapter(synthetic_sqlite, max_rows_per_table=1)
    data = adapter.load()
    for table, rows in data.items():
        assert len(rows) <= 1, table
    assert adapter.last_row_counts["users"] == 1
    assert adapter.last_row_counts["payments"] == 1


def test_schema_mismatch_raises(local_tmp: Path, synthetic_sqlite: Path):
    mismatch_path = local_tmp / "mismatched.sqlite"
    shutil.copyfile(synthetic_sqlite, mismatch_path)
    conn = sqlite3.connect(mismatch_path)
    try:
        conn.execute("ALTER TABLE clients ADD COLUMN secret_note TEXT")
        conn.commit()
    finally:
        conn.close()

    adapter = ReadonlySqliteSourceAdapter(mismatch_path)
    with pytest.raises(SchemaMismatchError):
        adapter.load()


def test_schema_mismatch_can_be_explicitly_allowed(local_tmp: Path, synthetic_sqlite: Path):
    mismatch_path = local_tmp / "mismatched_allowed.sqlite"
    shutil.copyfile(synthetic_sqlite, mismatch_path)
    conn = sqlite3.connect(mismatch_path)
    try:
        conn.execute("ALTER TABLE clients ADD COLUMN secret_note TEXT")
        conn.commit()
    finally:
        conn.close()

    adapter = ReadonlySqliteSourceAdapter(mismatch_path, allow_schema_mismatch=True)
    data = adapter.load()
    assert "clients" in data
    assert adapter.last_schema_fingerprint != EXPECTED_SCHEMA_FINGERPRINT


def test_masking_hides_sensitive_fields():
    row = {
        "id": "c-1",
        "display_name": "Synthetic Client A",
        "email": "client-a@synthetic.local",
        "notes": "private note",
        "status": "active",
    }
    masked = mask_row_for_log(row)
    assert masked["id"] == "c-1"
    assert masked["status"] == "active"
    assert masked["display_name"] != row["display_name"]
    assert "Synthetic Client A" not in masked["display_name"]
    assert "client-a@synthetic.local" not in masked["email"]
    assert "@synthetic.local" in masked["email"]
    assert mask_value("ab") == "***"
    assert_no_raw_pii(masked, ["Synthetic Client A", "client-a@synthetic.local", "private note"])
