"""Alembic revision metadata checks for M8-B publishing connections migration."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")

REVISION_0016 = "0016_mkt_publishing_conn"
DOWN_REVISION_0016 = "0015_marketing_cabinet_mvp"
MIGRATION_FILENAME = "20260716_0016_mkt_publishing_conn.py"


def test_0016_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0016)
    assert rev is not None
    assert rev.down_revision == DOWN_REVISION_0016
    assert len(REVISION_0016) <= 32

    # 0016 remains in chain; head may advance to later revisions.
    assert script.get_revision(REVISION_0016) is not None
    heads = script.get_heads()
    assert len(heads) == 1


def test_0016_migration_module_importable():
    import importlib.util

    migration_path = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("migration_0016", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == REVISION_0016
    assert module.down_revision == DOWN_REVISION_0016
    assert len(module.revision) <= 32
    assert callable(module.upgrade)
    assert callable(module.downgrade)
