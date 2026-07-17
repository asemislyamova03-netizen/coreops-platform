"""Alembic revision metadata checks for M8-B publishing connections migration."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")

REVISION_0021 = "0021_mkt_publishing_conn"
DOWN_REVISION_0021 = "0020_process_overlay_e1b"
MIGRATION_FILENAME = "20260717_0021_mkt_publishing_conn.py"


def test_0021_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0021)
    assert rev is not None
    assert rev.down_revision == DOWN_REVISION_0021
    assert len(REVISION_0021) <= 32

    # 0021 remains in chain; head may advance to later revisions.
    assert script.get_revision(REVISION_0021) is not None
    heads = script.get_heads()
    assert len(heads) == 1


def test_0021_migration_module_importable():
    import importlib.util

    migration_path = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("migration_0021", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == REVISION_0021
    assert module.down_revision == DOWN_REVISION_0021
    assert len(module.revision) <= 32
    assert callable(module.upgrade)
    assert callable(module.downgrade)
