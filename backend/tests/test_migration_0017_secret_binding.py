"""Alembic revision metadata checks for M8-C1a secret binding migration."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")

REVISION_0017 = "0017_mkt_secret_binding"
DOWN_REVISION_0017 = "0016_mkt_publishing_conn"
MIGRATION_FILENAME = "20260716_0017_mkt_secret_binding.py"


def test_0017_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0017)
    assert rev is not None
    assert rev.down_revision == DOWN_REVISION_0017
    assert len(REVISION_0017) <= 32

    head = script.get_current_head()
    assert head == REVISION_0017
    assert script.get_heads() == [REVISION_0017]


def test_0017_migration_module_importable():
    import importlib.util

    migration_path = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("migration_0017", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == REVISION_0017
    assert module.down_revision == DOWN_REVISION_0017
    assert len(module.revision) <= 32
    assert callable(module.upgrade)
    assert callable(module.downgrade)
