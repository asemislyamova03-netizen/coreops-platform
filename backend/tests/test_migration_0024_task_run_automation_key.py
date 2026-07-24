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


@pytest.fixture(autouse=True)
def seed_catalog(request):
    """Override global autouse seed: migration tests manage their own Postgres DDL."""
    yield


def _alembic_config() -> Config:
    database_url = _database_url()
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _tasks_hardened_0024_constraint_names(conn) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            WHERE n.nspname = 'public' AND t.relname = 'tasks'
            """
        )
    ).fetchall()
    return {row[0] for row in rows}


def _has_hardened_0024_schema(conn) -> bool:
    names = _tasks_hardened_0024_constraint_names(conn)
    return (
        "fk_tasks_tenant_process_run" in names
        and "ck_tasks_automation_key_nonempty" in names
        and "fk_tasks_process_run_id" not in names
    )


def _drop_legacy_0024_tasks_automation(conn) -> None:
    """Remove pre-hardening 0024 DDL so the updated revision can re-apply."""
    for stmt in (
        "DROP INDEX IF EXISTS uq_tasks_tenant_process_run_automation_key",
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_process_run_automation_key_pair",
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_automation_key_nonempty",
        "DROP INDEX IF EXISTS ix_tasks_process_run_id",
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS fk_tasks_tenant_process_run",
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS fk_tasks_process_run_id",
        "ALTER TABLE tasks DROP COLUMN IF EXISTS automation_key",
        "ALTER TABLE tasks DROP COLUMN IF EXISTS process_run_id",
        "ALTER TABLE process_runs DROP CONSTRAINT IF EXISTS uq_process_runs_tenant_id_id",
    ):
        conn.execute(text(stmt))
    conn.commit()


def _reconcile_stale_alembic_version(cfg: Config) -> None:
    """Align alembic_version with actual Postgres DDL before 0024 tests.

    Handles:
    - 0021–0023 DDL present but alembic_version lagging (stamp forward)
    - hardened 0024 present but alembic_version lagging (stamp to 0024)
    - legacy single-column 0024 applied while migration head expects composite FK
    """
    engine = create_engine(_database_url())
    try:
        with engine.begin() as conn:
            has_alembic = conn.execute(
                text("SELECT to_regclass('public.alembic_version')")
            ).scalar()
            if not has_alembic:
                return
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
                            "WHERE table_schema = 'public' AND table_name = 'tasks'"
                        )
                    )
                }
                has_0024_col = "process_run_id" in cols

            has_hardened = _has_hardened_0024_schema(conn) if has_0024_col else False

            if has_0024_col and not has_hardened:
                _drop_legacy_0024_tasks_automation(conn)
                command.stamp(cfg, REVISION_0023)
                return

            if has_0024_col and has_hardened and version != REVISION_0024:
                command.stamp(cfg, REVISION_0024)
            elif has_0023 and version not in {REVISION_0023, REVISION_0024}:
                command.stamp(cfg, REVISION_0023)
    finally:
        engine.dispose()


def _prepare_postgres_at_0023(cfg: Config) -> None:
    _reconcile_stale_alembic_version(cfg)
    command.downgrade(cfg, REVISION_0023)
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
    # Extensible: later migrations (e.g. 0025) may advance the head beyond 0024.
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
    assert "ck_tasks_automation_key_nonempty" in src
    assert "uq_tasks_tenant_process_run_automation_key" in src
    assert "fk_tasks_tenant_process_run" in src
    assert "uq_process_runs_tenant_id_id" in src
    assert "fk_tasks_process_run_id" not in src
    assert "postgresql_where" in src
    assert "sqlite_where" in src
    assert "ON DELETE RESTRICT" in src or 'ondelete="RESTRICT"' in src


def test_no_second_alembic_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    heads = script.get_heads()
    assert len(heads) == 1
    assert _revision_is_ancestor(script, REVISION_0024, heads[0])


def _assert_tasks_automation_columns(engine) -> None:
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("tasks")}
    assert "process_run_id" in columns
    assert "automation_key" in columns
    assert columns["process_run_id"]["nullable"] is True
    assert columns["automation_key"]["nullable"] is True

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("tasks")}
    assert "fk_tasks_tenant_process_run" in fk_names
    assert "fk_tasks_process_run_id" not in fk_names
    fk = next(
        fk for fk in inspector.get_foreign_keys("tasks") if fk["name"] == "fk_tasks_tenant_process_run"
    )
    assert fk["referred_table"] == "process_runs"
    assert fk["constrained_columns"] == ["tenant_id", "process_run_id"]
    assert fk["referred_columns"] == ["tenant_id", "id"]

    check_names = {ck["name"] for ck in inspector.get_check_constraints("tasks")}
    assert "ck_tasks_process_run_automation_key_pair" in check_names
    assert "ck_tasks_automation_key_nonempty" in check_names

    index_names = {idx["name"] for idx in inspector.get_indexes("tasks")}
    assert "uq_tasks_tenant_process_run_automation_key" in index_names
    assert "ix_tasks_process_run_id" in index_names

    process_run_uqs = {
        uq["name"] for uq in inspector.get_unique_constraints("process_runs")
    }
    assert "uq_process_runs_tenant_id_id" in process_run_uqs
    uq = next(
        uq
        for uq in inspector.get_unique_constraints("process_runs")
        if uq["name"] == "uq_process_runs_tenant_id_id"
    )
    assert uq["column_names"] == ["tenant_id", "id"]


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


def _seed_cross_tenant_task_graph(conn) -> dict[str, uuid.UUID]:
    """Tenant A work_item + tenant B process_run for composite FK cross-tenant tests."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    provider_a = uuid.uuid4()
    provider_b = uuid.uuid4()
    pipeline_a = uuid.uuid4()
    pipeline_b = uuid.uuid4()
    stage_a = uuid.uuid4()
    stage_b = uuid.uuid4()
    work_item_a = uuid.uuid4()
    work_item_b = uuid.uuid4()
    template_b = uuid.uuid4()
    config_b = uuid.uuid4()
    version_b = uuid.uuid4()
    process_run_b = uuid.uuid4()
    actor = uuid.uuid4()
    slug_a = f"c2b1-a-{uuid.uuid4().hex[:8]}"
    slug_b = f"c2b1-b-{uuid.uuid4().hex[:8]}"

    for provider_id, slug in ((provider_a, slug_a), (provider_b, slug_b)):
        conn.execute(
            text(
                """
                INSERT INTO provider_companies (id, name, slug, is_active)
                VALUES (:id, :name, :slug, true)
                """
            ),
            {"id": provider_id, "name": f"Prov {slug}", "slug": f"prov-{slug}"},
        )

    for tenant_id, provider_id, slug in (
        (tenant_a, provider_a, slug_a),
        (tenant_b, provider_b, slug_b),
    ):
        conn.execute(
            text(
                """
                INSERT INTO tenants (id, provider_company_id, name, slug, status)
                VALUES (:id, :provider_id, :name, :slug, 'active')
                """
            ),
            {
                "id": tenant_id,
                "provider_id": provider_id,
                "name": f"Tenant {slug}",
                "slug": slug,
            },
        )

    for pipeline_id, tenant_id, code in (
        (pipeline_a, tenant_a, "sales-a"),
        (pipeline_b, tenant_b, "sales-b"),
    ):
        conn.execute(
            text(
                """
                INSERT INTO pipelines (id, tenant_id, code, name, entity_type, is_default)
                VALUES (:id, :tenant_id, :code, :name, 'work_item', true)
                """
            ),
            {
                "id": pipeline_id,
                "tenant_id": tenant_id,
                "code": code,
                "name": code,
            },
        )

    for stage_id, pipeline_id in ((stage_a, pipeline_a), (stage_b, pipeline_b)):
        conn.execute(
            text(
                """
                INSERT INTO pipeline_stages (
                    id, pipeline_id, code, name, sort_order, is_terminal
                )
                VALUES (:id, :pipeline_id, 'new_lead', 'New', 10, false)
                """
            ),
            {"id": stage_id, "pipeline_id": pipeline_id},
        )

    conn.execute(
        text(
            """
            INSERT INTO work_items (
                id, tenant_id, pipeline_id, stage_id, work_item_type, title,
                status, custom_fields_json
            )
            VALUES (
                :id, :tenant_id, :pipeline_id, :stage_id, 'lead', 'tenant-a lead',
                'open', CAST(:custom AS json)
            )
            """
        ),
        {
            "id": work_item_a,
            "tenant_id": tenant_a,
            "pipeline_id": pipeline_a,
            "stage_id": stage_a,
            "custom": json.dumps({}),
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
            "id": template_b,
            "code": f"tpl_{slug_b}",
            "name": f"Template {slug_b}",
            "policy": json.dumps({}),
            "modules": json.dumps([]),
        },
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
            "id": config_b,
            "tenant_id": tenant_b,
            "template_id": template_b,
            "pipeline_id": pipeline_b,
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
                :pipeline_id, 'sales-b', CAST(:stages AS json), CAST(:policy AS json),
                CAST(:modules AS json), now(), :actor, 'cross-tenant seed'
            )
            """
        ),
        {
            "id": version_b,
            "tenant_id": tenant_b,
            "config_id": config_b,
            "pipeline_id": pipeline_b,
            "stages": json.dumps(["new_lead"]),
            "policy": json.dumps({"schema_version": 1}),
            "modules": json.dumps([]),
            "actor": actor,
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
                :id, :tenant_id, :pipeline_id, :stage_id, 'lead', 'tenant-b lead',
                'open', CAST(:custom AS json)
            )
            """
        ),
        {
            "id": work_item_b,
            "tenant_id": tenant_b,
            "pipeline_id": pipeline_b,
            "stage_id": stage_b,
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
            "id": process_run_b,
            "tenant_id": tenant_b,
            "config_id": config_b,
            "version_id": version_b,
            "work_item": work_item_b,
            "actor": actor,
        },
    )
    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "work_item_a": work_item_a,
        "process_run_b": process_run_b,
    }


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
def test_0024_cross_tenant_composite_fk_rejects_mismatch():
    cfg = _alembic_config()
    _prepare_postgres_at_0023(cfg)
    command.upgrade(cfg, REVISION_0024)
    engine = create_engine(_database_url())

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            ids = _seed_cross_tenant_task_graph(conn)
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        """
                        INSERT INTO tasks (
                            id, tenant_id, work_item_id, title, status,
                            process_run_id, automation_key
                        )
                        VALUES (
                            :id, :tenant_id, :work_item, 'cross-tenant', 'pending',
                            :process_run, 'consulting_first_contact'
                        )
                        """
                    ),
                    {
                        "id": uuid.uuid4(),
                        "tenant_id": ids["tenant_a"],
                        "work_item": ids["work_item_a"],
                        "process_run": ids["process_run_b"],
                    },
                )
        finally:
            trans.rollback()

    engine.dispose()


@postgres_required
def test_0024_same_tenant_valid_pair_insert_passes():
    cfg = _alembic_config()
    _prepare_postgres_at_0023(cfg)
    command.upgrade(cfg, REVISION_0024)
    engine = create_engine(_database_url())

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            ids = _seed_minimal_task_graph(conn)
            conn.execute(
                text(
                    """
                    INSERT INTO tasks (
                        id, tenant_id, work_item_id, title, status,
                        process_run_id, automation_key
                    )
                    VALUES (
                        :id, :tenant_id, :work_item, 'valid pair', 'pending',
                        :process_run, 'consulting_first_contact'
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
def test_0024_whitespace_automation_key_rejected():
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
                            :id, :tenant_id, :work_item, 'blank key', 'pending',
                            :process_run, '   '
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
def test_0024_legacy_null_null_task_passes():
    cfg = _alembic_config()
    _prepare_postgres_at_0023(cfg)
    command.upgrade(cfg, REVISION_0024)
    engine = create_engine(_database_url())

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            ids = _seed_minimal_task_graph(conn)
            conn.execute(
                text(
                    """
                    INSERT INTO tasks (
                        id, tenant_id, work_item_id, title, status
                    )
                    VALUES (
                        :id, :tenant_id, :work_item, 'legacy manual', 'pending'
                    )
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "tenant_id": ids["tenant"],
                    "work_item": ids["work_item"],
                },
            )
        finally:
            trans.rollback()

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
