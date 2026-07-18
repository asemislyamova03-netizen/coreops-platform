"""Alembic migration tests for 0024_task_run_automation_key."""

from __future__ import annotations

import importlib.util
import json
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")
REVISION_0023 = "0023_mkt_storage_profiles"
REVISION_0024 = "0024_task_run_automation_key"
MIGRATION_FILENAME = "20260718_0024_task_run_automation_key.py"
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME


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


def _reconcile_stale_alembic_version(cfg: Config) -> None:
    """Some local DBs have 0021–0023 DDL while alembic_version lags behind.

    If storage-profile tables exist but version is older than 0023, stamp to 0023
    so 0024 up/down/up can run without replaying already-applied DDL.
    """
    engine = create_engine(_database_url())
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            has_0023 = conn.execute(
                text("SELECT to_regclass('public.marketing_storage_resource_profiles')")
            ).scalar()
            has_0024_col = False
            if conn.execute(text("SELECT to_regclass('public.tasks')")).scalar():
                cols = {
                    row[0]
                    for row in conn.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name = 'tasks'"
                        )
                    )
                }
                has_0024_col = "process_run_id" in cols
        if has_0024_col and version != REVISION_0024:
            command.stamp(cfg, REVISION_0024)
        elif has_0023 and version not in {REVISION_0023, REVISION_0024}:
            command.stamp(cfg, REVISION_0023)
    finally:
        engine.dispose()


def _prepare_postgres_at_0023(cfg: Config) -> None:
    _reconcile_stale_alembic_version(cfg)
    command.upgrade(cfg, REVISION_0023)



def _load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_0024", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _revision_is_ancestor(script: ScriptDirectory, ancestor: str, descendant: str) -> bool:
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


def test_0024_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev_0023 = script.get_revision(REVISION_0023)
    assert rev_0023 is not None

    rev_0024 = script.get_revision(REVISION_0024)
    assert rev_0024 is not None
    assert rev_0024.down_revision == REVISION_0023
    assert len(REVISION_0024) <= 32

    heads = script.get_heads()
    assert len(heads) == 1
    head = heads[0]
    assert head == REVISION_0024
    assert _revision_is_ancestor(script, REVISION_0023, head)
    assert _revision_is_ancestor(script, REVISION_0024, head)


def test_0024_migration_module_importable():
    module = _load_migration_module()
    assert module.revision == REVISION_0024
    assert module.down_revision == REVISION_0023
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    src = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "ck_tasks_process_run_automation_key_pair" in src
    assert "uq_tasks_tenant_process_run_automation_key" in src
    assert "fk_tasks_process_run_id" in src
    assert "postgresql_where" in src
    assert "sqlite_where" in src
    assert "ON DELETE RESTRICT" in src or 'ondelete="RESTRICT"' in src


def test_no_second_alembic_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    assert script.get_heads() == [REVISION_0024]


def _assert_tasks_automation_columns(engine) -> None:
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("tasks")}
    assert "process_run_id" in columns
    assert "automation_key" in columns
    assert columns["process_run_id"]["nullable"] is True
    assert columns["automation_key"]["nullable"] is True

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("tasks")}
    assert "fk_tasks_process_run_id" in fk_names
    fk = next(fk for fk in inspector.get_foreign_keys("tasks") if fk["name"] == "fk_tasks_process_run_id")
    assert fk["referred_table"] == "process_runs"
    assert fk["constrained_columns"] == ["process_run_id"]

    check_names = {ck["name"] for ck in inspector.get_check_constraints("tasks")}
    assert "ck_tasks_process_run_automation_key_pair" in check_names

    index_names = {idx["name"] for idx in inspector.get_indexes("tasks")}
    assert "uq_tasks_tenant_process_run_automation_key" in index_names
    assert "ix_tasks_process_run_id" in index_names


def _seed_minimal_task_graph(conn) -> dict[str, uuid.UUID]:
    """Minimal tenant/pipeline/work_item/process_run for constraint tests."""
    ids = {
        "provider": uuid.uuid4(),
        "tenant": uuid.uuid4(),
        "template": uuid.uuid4(),
        "pipeline": uuid.uuid4(),
        "stage": uuid.uuid4(),
        "config": uuid.uuid4(),
        "version": uuid.uuid4(),
        "work_item": uuid.uuid4(),
        "process_run": uuid.uuid4(),
        "actor": uuid.uuid4(),
    }
    slug = f"c2b1-mig-{uuid.uuid4().hex[:8]}"

    conn.execute(
        text(
            """
            INSERT INTO provider_companies (id, name, slug, is_active)
            VALUES (:id, :name, :slug, true)
            """
        ),
        {"id": ids["provider"], "name": f"Prov {slug}", "slug": f"prov-{slug}"},
    )
    conn.execute(
        text(
            """
            INSERT INTO tenants (id, provider_company_id, name, slug, status)
            VALUES (:id, :provider_id, :name, :slug, 'active')
            """
        ),
        {
            "id": ids["tenant"],
            "provider_id": ids["provider"],
            "name": f"Tenant {slug}",
            "slug": slug,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO process_templates (
                id, code, name, default_pipeline_code,
                default_policy_blueprint_json, required_module_codes_json, is_active
            )
            VALUES (
                :id, :code, :name, 'flexity_sales',
                CAST(:policy AS json), CAST(:modules AS json), true
            )
            """
        ),
        {
            "id": ids["template"],
            "code": f"tpl_{slug}",
            "name": f"Template {slug}",
            "policy": json.dumps({}),
            "modules": json.dumps([]),
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO pipelines (id, tenant_id, code, name, entity_type, is_default)
            VALUES (:id, :tenant_id, :code, :name, 'work_item', true)
            """
        ),
        {
            "id": ids["pipeline"],
            "tenant_id": ids["tenant"],
            "code": "sales",
            "name": "Sales",
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO pipeline_stages (
                id, pipeline_id, code, name, sort_order, is_terminal
            )
            VALUES (:id, :pipeline_id, 'new_lead', 'New', 10, false)
            """
        ),
        {"id": ids["stage"], "pipeline_id": ids["pipeline"]},
    )
    conn.execute(
        text(
            """
            INSERT INTO tenant_process_configurations (
                id, tenant_id, process_template_id, pipeline_id, activation_state
            )
            VALUES (:id, :tenant_id, :template_id, :pipeline_id, 'inactive')
            """
        ),
        {
            "id": ids["config"],
            "tenant_id": ids["tenant"],
            "template_id": ids["template"],
            "pipeline_id": ids["pipeline"],
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO process_definition_versions (
                id, tenant_id, tenant_process_configuration_id, version_number,
                pipeline_id, pipeline_code, stage_codes_json, policy_snapshot_json,
                module_requirements_json, published_at, published_by_user_id, publish_reason
            )
            VALUES (
                :id, :tenant_id, :config_id, 1,
                :pipeline_id, 'sales', CAST(:stages AS json), CAST(:policy AS json),
                CAST(:modules AS json), now(), :actor, 'mig seed'
            )
            """
        ),
        {
            "id": ids["version"],
            "tenant_id": ids["tenant"],
            "config_id": ids["config"],
            "pipeline_id": ids["pipeline"],
            "stages": json.dumps(["new_lead"]),
            "policy": json.dumps({"schema_version": 1}),
            "modules": json.dumps([]),
            "actor": ids["actor"],
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO work_items (
                id, tenant_id, pipeline_id, stage_id, work_item_type, title,
                status, custom_fields_json
            )
            VALUES (
                :id, :tenant_id, :pipeline_id, :stage_id, 'lead', 'mig lead',
                'open', CAST(:custom AS json)
            )
            """
        ),
        {
            "id": ids["work_item"],
            "tenant_id": ids["tenant"],
            "pipeline_id": ids["pipeline"],
            "stage_id": ids["stage"],
            "custom": json.dumps({}),
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO process_runs (
                id, tenant_id, tenant_process_configuration_id,
                process_definition_version_id, work_item_id,
                run_state, started_at, started_by_user_id
            )
            VALUES (
                :id, :tenant_id, :config_id, :version_id, :work_item,
                'active', now(), :actor
            )
            """
        ),
        {
            "id": ids["process_run"],
            "tenant_id": ids["tenant"],
            "config_id": ids["config"],
            "version_id": ids["version"],
            "work_item": ids["work_item"],
            "actor": ids["actor"],
        },
    )
    return ids


@postgres_required
def test_0024_upgrade_downgrade_upgrade():
    cfg = _alembic_config()
    engine = create_engine(_database_url())
    _prepare_postgres_at_0023(cfg)

    command.upgrade(cfg, REVISION_0024)
    _assert_tasks_automation_columns(engine)

    command.downgrade(cfg, REVISION_0023)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("tasks")}
    assert "process_run_id" not in columns
    assert "automation_key" not in columns

    command.upgrade(cfg, REVISION_0024)
    _assert_tasks_automation_columns(engine)
    engine.dispose()


@postgres_required
def test_0024_check_rejects_partial_pair():
    cfg = _alembic_config()
    _prepare_postgres_at_0023(cfg)
    command.upgrade(cfg, REVISION_0024)
    engine = create_engine(_database_url())

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            ids = _seed_minimal_task_graph(conn)
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        """
                        INSERT INTO tasks (
                            id, tenant_id, work_item_id, title, status,
                            process_run_id, automation_key
                        )
                        VALUES (
                            :id, :tenant_id, :work_item, 'bad', 'pending',
                            :process_run, NULL
                        )
                        """
                    ),
                    {
                        "id": uuid.uuid4(),
                        "tenant_id": ids["tenant"],
                        "work_item": ids["work_item"],
                        "process_run": ids["process_run"],
                    },
                )
        finally:
            trans.rollback()

    engine.dispose()


@postgres_required
def test_0024_partial_unique_rejects_duplicate_automation_key():
    cfg = _alembic_config()
    _prepare_postgres_at_0023(cfg)
    command.upgrade(cfg, REVISION_0024)
    engine = create_engine(_database_url())

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            ids = _seed_minimal_task_graph(conn)
            params = {
                "tenant_id": ids["tenant"],
                "work_item": ids["work_item"],
                "process_run": ids["process_run"],
            }
            conn.execute(
                text(
                    """
                    INSERT INTO tasks (
                        id, tenant_id, work_item_id, title, status,
                        process_run_id, automation_key
                    )
                    VALUES (
                        :id, :tenant_id, :work_item, 'first', 'pending',
                        :process_run, 'consulting_first_contact'
                    )
                    """
                ),
                {**params, "id": uuid.uuid4()},
            )
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        """
                        INSERT INTO tasks (
                            id, tenant_id, work_item_id, title, status,
                            process_run_id, automation_key
                        )
                        VALUES (
                            :id, :tenant_id, :work_item, 'second', 'pending',
                            :process_run, 'consulting_first_contact'
                        )
                        """
                    ),
                    {**params, "id": uuid.uuid4()},
                )
        finally:
            trans.rollback()

    engine.dispose()
