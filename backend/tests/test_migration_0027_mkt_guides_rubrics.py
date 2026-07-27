"""M7.5-A Alembic revision checks for marketing guides + rubrics."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")

REVISION_0026 = "0026_mkt_publish_destinations"
REVISION_0027 = "0027_mkt_guides_rubrics"
MIGRATION_FILENAME = "20260727_0027_mkt_guides_rubrics.py"


def test_0027_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0027)
    assert rev is not None
    assert rev.down_revision == REVISION_0026
    assert len(REVISION_0027) <= 32

    heads = script.get_heads()
    assert len(heads) == 1
    # Head advances with later additive revisions (M7.5-B 0028, timestamp hotfix 0029).
    assert heads[0] == "0029_mkt_timestamp_defaults"
    assert REVISION_0027 not in heads


def test_0027_migration_module_importable():
    import importlib.util

    migration_path = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("migration_0027", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == REVISION_0027
    assert module.down_revision == REVISION_0026
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    src = migration_path.read_text(encoding="utf-8")
    assert "marketing_guides" in src
    assert "marketing_rubrics" in src
    assert "uq_marketing_guides_tenant_active" in src
    assert "uq_marketing_rubrics_tenant_code" in src
    assert "marketing_content_topics" not in src.split("upgrade")[1].split("downgrade")[0]


def test_0026_is_ancestor_not_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    assert REVISION_0026 not in script.get_heads()
    rev = script.get_revision(REVISION_0026)
    assert rev is not None
    assert rev.down_revision == "0025_secret_envelope_versions"
