"""Alembic revision metadata checks for M8-D1 marketing_publish_destinations."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")

REVISION_0025 = "0025_secret_envelope_versions"
REVISION_0026 = "0026_mkt_publish_destinations"
DOWN_REVISION_0026 = REVISION_0025
MIGRATION_FILENAME = "20260723_0026_marketing_publish_destinations.py"


def test_0026_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0026)
    assert rev is not None
    assert rev.down_revision == DOWN_REVISION_0026
    assert len(REVISION_0026) <= 32

    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == REVISION_0026


def test_0026_migration_module_importable():
    import importlib.util

    migration_path = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("migration_0026", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == REVISION_0026
    assert module.down_revision == DOWN_REVISION_0026
    assert len(module.revision) <= 32
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    src = migration_path.read_text(encoding="utf-8")
    assert "marketing_publish_destinations" in src
    assert "uq_mkt_publish_dest_active_identity" in src
    assert "uq_marketing_publishing_conn_tenant_id_id" in src
    assert "fk_mkt_publish_dest_tenant_connection" in src
    assert "fk_mkt_publish_dest_tenant" in src
    assert "identity_locked_at" in src
    assert 'ondelete="RESTRICT"' in src
    assert 'ondelete="CASCADE"' not in src
    assert "postgresql_where" in src
    assert "sqlite_where" in src
    assert "secret_ref" not in src
    assert "0025_secret_envelope_versions" in src
    # Composite FK is the connection SoT (no lone single-column connection FK).
    assert (
        '["tenant_id", "publishing_connection_id"]' in src
        or "['tenant_id', 'publishing_connection_id']" in src
    )
    assert "ix_marketing_publish_destinations_connection" not in src

def test_no_second_alembic_head_after_0026():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    assert script.get_heads() == [REVISION_0026]


def test_0025_still_points_at_0024_and_is_not_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0025)
    assert rev is not None
    assert rev.down_revision == "0024_task_run_automation_key"
    assert REVISION_0025 not in script.get_heads()
