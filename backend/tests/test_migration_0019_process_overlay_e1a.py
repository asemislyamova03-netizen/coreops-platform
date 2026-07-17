"""Alembic migration tests for 0019_process_overlay_e1a."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")
REVISION_0019 = "0019_process_overlay_e1a"
REVISION_0020 = "0020_process_overlay_e1b"
DOWN_REVISION_0019 = "0015_marketing_cabinet_mvp"
MIGRATION_FILENAME = "20260717_0019_process_overlay_e1a.py"
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME

CRM_TABLES = ("pipelines", "pipeline_stages", "work_items")


def _database_url() -> str:
    return get_settings().database_url


def _postgres_available() -> bool:
    try:
        engine = create_engine(_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except OperationalError:
        return False


postgres_required = pytest.mark.skipif(
    not _postgres_available(),
    reason="Local Postgres is required for Alembic migration chain tests",
)


def _alembic_config() -> Config:
    database_url = _database_url()
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_0019", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _revision_is_ancestor(script: ScriptDirectory, ancestor: str, descendant: str) -> bool:
    """True if ancestor appears in the down_revision walk from descendant."""
    current = descendant
    seen: set[str] = set()
    while current is not None:
        if current == ancestor:
            return True
        if current in seen:
            return False
        seen.add(current)
        rev = script.get_revision(current)
        if rev is None:
            return False
        current = rev.down_revision
    return False


def test_0019_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev_0019 = script.get_revision(REVISION_0019)
    assert rev_0019 is not None
    assert rev_0019.down_revision == DOWN_REVISION_0019
    assert len(REVISION_0019) <= 32

    rev_0020 = script.get_revision(REVISION_0020)
    assert rev_0020 is not None
    assert rev_0020.down_revision == REVISION_0019
    assert len(REVISION_0020) <= 32

    heads = script.get_heads()
    assert len(heads) == 1
    head = heads[0]
    # Extensible: later migrations may advance the head beyond 0020.
    assert _revision_is_ancestor(script, REVISION_0019, head)
    assert _revision_is_ancestor(script, REVISION_0020, head)


def test_0019_migration_module_importable():
    module = _load_migration_module()
    assert module.revision == REVISION_0019
    assert module.down_revision == DOWN_REVISION_0019
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_no_second_alembic_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    assert len(script.get_heads()) == 1


@postgres_required
def test_0019_upgrade_downgrade_upgrade_preserves_crm_tables():
    cfg = _alembic_config()
    engine = create_engine(_database_url())

    command.upgrade(cfg, REVISION_0019)
    inspector = inspect(engine)
    overlay_tables = {
        "process_templates",
        "tenant_process_configurations",
        "process_definition_versions",
    }
    assert overlay_tables.issubset(set(inspector.get_table_names()))

    crm_counts_before_downgrade = {}
    with engine.connect() as conn:
        for table in CRM_TABLES:
            crm_counts_before_downgrade[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar_one()

    command.downgrade(cfg, DOWN_REVISION_0019)
    inspector = inspect(engine)
    remaining = set(inspector.get_table_names())
    assert not overlay_tables.intersection(remaining)

    with engine.connect() as conn:
        for table in CRM_TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            assert count == crm_counts_before_downgrade[table]

    command.upgrade(cfg, REVISION_0019)
    inspector = inspect(engine)
    assert overlay_tables.issubset(set(inspector.get_table_names()))
    engine.dispose()
