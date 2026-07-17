"""Alembic migration tests for 0020_process_overlay_e1b."""

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
REVISION_0019 = "0019_process_overlay_e1a"
REVISION_0020 = "0020_process_overlay_e1b"
MIGRATION_FILENAME = "20260717_0020_process_overlay_e1b.py"
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME

CRM_TABLES = ("pipelines", "pipeline_stages", "work_items")
E1A_TABLES = (
    "process_templates",
    "tenant_process_configurations",
    "process_definition_versions",
)


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
    spec = importlib.util.spec_from_file_location("migration_0020", MIGRATION_PATH)
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


def test_0020_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev_0019 = script.get_revision(REVISION_0019)
    assert rev_0019 is not None

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


def test_0020_migration_module_importable():
    module = _load_migration_module()
    assert module.revision == REVISION_0020
    assert module.down_revision == REVISION_0019
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    assert "fk_process_run_config_version" in MIGRATION_PATH.read_text(encoding="utf-8")
    assert "ck_process_run_state_valid" in MIGRATION_PATH.read_text(encoding="utf-8")
    assert "uq_process_def_version_config_id" in MIGRATION_PATH.read_text(encoding="utf-8")


def test_no_second_alembic_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    assert len(script.get_heads()) == 1


def _assert_process_runs_hardened_constraints(engine) -> None:
    inspector = inspect(engine)
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("process_runs")}
    assert "fk_process_run_config_version" in fk_names

    composite = next(
        fk for fk in inspector.get_foreign_keys("process_runs") if fk["name"] == "fk_process_run_config_version"
    )
    assert composite["referred_table"] == "process_definition_versions"
    assert composite["constrained_columns"] == [
        "tenant_process_configuration_id",
        "process_definition_version_id",
    ]
    assert composite["referred_columns"] == [
        "tenant_process_configuration_id",
        "id",
    ]

    check_names = {ck["name"] for ck in inspector.get_check_constraints("process_runs")}
    assert "ck_process_run_state_valid" in check_names

    # Ownership is composite-only (no simple FKs to config.id / version.id).
    simple_targets = {
        (tuple(fk["constrained_columns"]), fk["referred_table"])
        for fk in inspector.get_foreign_keys("process_runs")
    }
    assert (("tenant_process_configuration_id",), "tenant_process_configurations") not in simple_targets
    assert (("process_definition_version_id",), "process_definition_versions") not in simple_targets
    assert (("tenant_id",), "tenants") in simple_targets
    assert (("work_item_id",), "work_items") in simple_targets


def _seed_two_configs_and_work_item(conn) -> dict[str, uuid.UUID]:
    """Minimal graph for composite FK / CHECK rejection tests. Caller owns txn."""
    ids = {
        "provider": uuid.uuid4(),
        "tenant": uuid.uuid4(),
        "template_a": uuid.uuid4(),
        "template_b": uuid.uuid4(),
        "pipeline_a": uuid.uuid4(),
        "pipeline_b": uuid.uuid4(),
        "stage_a": uuid.uuid4(),
        "config_a": uuid.uuid4(),
        "config_b": uuid.uuid4(),
        "version_a": uuid.uuid4(),
        "version_b": uuid.uuid4(),
        "work_item": uuid.uuid4(),
        "actor": uuid.uuid4(),
    }
    slug = f"e1b-mig-{uuid.uuid4().hex[:8]}"

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
    for key, code in (("template_a", f"tpl_a_{slug}"), ("template_b", f"tpl_b_{slug}")):
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
                "id": ids[key],
                "code": code,
                "name": code,
                "policy": json.dumps({}),
                "modules": json.dumps([]),
            },
        )
    for pipe_key, code, is_default in (
        ("pipeline_a", f"pipe_a_{slug}", True),
        ("pipeline_b", f"pipe_b_{slug}", False),
    ):
        conn.execute(
            text(
                """
                INSERT INTO pipelines (id, tenant_id, code, name, entity_type, is_default)
                VALUES (:id, :tenant_id, :code, :name, 'work_item', :is_default)
                """
            ),
            {
                "id": ids[pipe_key],
                "tenant_id": ids["tenant"],
                "code": code,
                "name": code,
                "is_default": is_default,
            },
        )
    conn.execute(
        text(
            """
            INSERT INTO pipeline_stages (id, pipeline_id, code, name, sort_order, is_terminal)
            VALUES (:id, :pipeline_id, 'new_lead', 'new_lead', 10, false)
            """
        ),
        {"id": ids["stage_a"], "pipeline_id": ids["pipeline_a"]},
    )
    for cfg_key, tpl_key, pipe_key in (
        ("config_a", "template_a", "pipeline_a"),
        ("config_b", "template_b", "pipeline_b"),
    ):
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
                "id": ids[cfg_key],
                "tenant_id": ids["tenant"],
                "template_id": ids[tpl_key],
                "pipeline_id": ids[pipe_key],
            },
        )
    for ver_key, cfg_key, pipe_key in (
        ("version_a", "config_a", "pipeline_a"),
        ("version_b", "config_b", "pipeline_b"),
    ):
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
                    :pipeline_id, 'flexity_sales', CAST(:stages AS json), CAST(:policy AS json),
                    CAST(:modules AS json), now(), :actor, 'mig seed'
                )
                """
            ),
            {
                "id": ids[ver_key],
                "tenant_id": ids["tenant"],
                "config_id": ids[cfg_key],
                "pipeline_id": ids[pipe_key],
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
            "pipeline_id": ids["pipeline_a"],
            "stage_id": ids["stage_a"],
            "custom": json.dumps({}),
        },
    )
    return ids


@postgres_required
def test_0020_upgrade_downgrade_upgrade_preserves_e1a_and_crm():
    cfg = _alembic_config()
    engine = create_engine(_database_url())

    command.upgrade(cfg, REVISION_0020)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "process_runs" in tables
    assert set(E1A_TABLES).issubset(tables)
    assert set(CRM_TABLES).issubset(tables)

    index_names = {idx["name"] for idx in inspector.get_indexes("process_runs")}
    assert "uq_process_run_one_active_per_work_item" in index_names
    _assert_process_runs_hardened_constraints(engine)

    crm_and_e1a_counts = {}
    with engine.connect() as conn:
        for table in (*CRM_TABLES, *E1A_TABLES):
            crm_and_e1a_counts[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar_one()

    command.downgrade(cfg, REVISION_0019)
    inspector = inspect(engine)
    remaining = set(inspector.get_table_names())
    assert "process_runs" not in remaining
    assert set(E1A_TABLES).issubset(remaining)
    assert set(CRM_TABLES).issubset(remaining)

    with engine.connect() as conn:
        for table in (*CRM_TABLES, *E1A_TABLES):
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            assert count == crm_and_e1a_counts[table]

    command.upgrade(cfg, REVISION_0020)
    inspector = inspect(engine)
    assert "process_runs" in set(inspector.get_table_names())
    assert set(E1A_TABLES).issubset(set(inspector.get_table_names()))
    _assert_process_runs_hardened_constraints(engine)
    engine.dispose()


@postgres_required
def test_0020_composite_fk_rejects_mismatched_config_version():
    cfg = _alembic_config()
    # Force recreate so amend-hardened 0020 DDL is applied (not a stale prior 0020).
    command.upgrade(cfg, REVISION_0020)
    command.downgrade(cfg, REVISION_0019)
    command.upgrade(cfg, REVISION_0020)
    engine = create_engine(_database_url())

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            ids = _seed_two_configs_and_work_item(conn)
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        """
                        INSERT INTO process_runs (
                            id, tenant_id, tenant_process_configuration_id,
                            process_definition_version_id, work_item_id,
                            run_state, started_at, started_by_user_id
                        )
                        VALUES (
                            :id, :tenant_id, :config_a, :version_b, :work_item,
                            'active', now(), :actor
                        )
                        """
                    ),
                    {
                        "id": uuid.uuid4(),
                        "tenant_id": ids["tenant"],
                        "config_a": ids["config_a"],
                        "version_b": ids["version_b"],
                        "work_item": ids["work_item"],
                        "actor": ids["actor"],
                    },
                )
        finally:
            trans.rollback()

    engine.dispose()


@postgres_required
def test_0020_check_rejects_uppercase_run_state():
    cfg = _alembic_config()
    command.upgrade(cfg, REVISION_0020)
    command.downgrade(cfg, REVISION_0019)
    command.upgrade(cfg, REVISION_0020)
    engine = create_engine(_database_url())

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            ids = _seed_two_configs_and_work_item(conn)
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        """
                        INSERT INTO process_runs (
                            id, tenant_id, tenant_process_configuration_id,
                            process_definition_version_id, work_item_id,
                            run_state, started_at, started_by_user_id
                        )
                        VALUES (
                            :id, :tenant_id, :config_a, :version_a, :work_item,
                            'ACTIVE', now(), :actor
                        )
                        """
                    ),
                    {
                        "id": uuid.uuid4(),
                        "tenant_id": ids["tenant"],
                        "config_a": ids["config_a"],
                        "version_a": ids["version_a"],
                        "work_item": ids["work_item"],
                        "actor": ids["actor"],
                    },
                )
        finally:
            trans.rollback()

    engine.dispose()
