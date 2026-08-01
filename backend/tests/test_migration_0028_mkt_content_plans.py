"""M7.5-B Alembic revision checks for marketing content plans."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")

REVISION_0027 = "0027_mkt_guides_rubrics"
REVISION_0028 = "0028_mkt_content_plans"
REVISION_0029 = "0029_mkt_timestamp_defaults"
REVISION_0030 = "0030_client_onboarding_idem"
MIGRATION_FILENAME = "20260727_0028_mkt_content_plans.py"


def test_0028_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0028)
    assert rev is not None
    assert rev.down_revision == REVISION_0027
    assert len(REVISION_0028) <= 32

    rev_0030 = script.get_revision(REVISION_0030)
    assert rev_0030 is not None
    assert rev_0030.down_revision == REVISION_0029
    assert len(REVISION_0030) <= 32

    heads = script.get_heads()
    assert len(heads) == 1
    # Head advances with later additive revisions (timestamp hotfix 0029, onboarding 0030).
    assert heads[0] == REVISION_0030
    assert REVISION_0028 not in heads


def test_0028_migration_module_importable():
    import importlib.util

    migration_path = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("migration_0028", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == REVISION_0028
    assert module.down_revision == REVISION_0027
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    src = migration_path.read_text(encoding="utf-8")
    upgrade = src.split("upgrade")[1].split("downgrade")[0]
    assert "marketing_content_plans" in upgrade
    assert "marketing_content_plan_items" in upgrade
    assert "uq_marketing_content_plans_tenant_fingerprint" in upgrade
    assert "uq_marketing_content_plan_items_line_key" in upgrade
    assert "sort_order" in upgrade
    assert "plan_item_id" not in upgrade
    assert "marketing_publication_packs" not in upgrade


def test_0027_is_ancestor_not_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    assert REVISION_0027 not in script.get_heads()
    rev = script.get_revision(REVISION_0027)
    assert rev is not None
    assert rev.down_revision == "0026_mkt_publish_destinations"
