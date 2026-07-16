"""Alembic migration tests for 0014_core_branches_baseline."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import configure_mappers

from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")
TEST_SLUG_PREFIX = "migration-test-"


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


def _run_alembic(cfg: Config, revision: str) -> None:
    if revision.startswith("-"):
        command.downgrade(cfg, revision)
    else:
        command.upgrade(cfg, revision)


def _current_revision(cfg: Config) -> str | None:
    from alembic.runtime.migration import MigrationContext

    engine = create_engine(_database_url())
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current = context.get_current_revision()
    engine.dispose()
    if current is None:
        return None
    return current


def _go_to_revision(cfg: Config, revision: str) -> None:
    current = _current_revision(cfg)
    if current == revision:
        return

    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(cfg)
    if current:
        walk = script.get_revision(current)
        while walk is not None:
            if walk.revision == revision:
                command.downgrade(cfg, revision)
                return
            walk = (
                script.get_revision(walk.down_revision)
                if walk.down_revision is not None
                else None
            )

    command.upgrade(cfg, revision)


def _ensure_revision(cfg: Config, revision: str) -> None:
    _go_to_revision(cfg, revision)


def _cleanup_test_rows(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM tenants
                WHERE slug LIKE :slug_prefix
                """
            ),
            {"slug_prefix": f"{TEST_SLUG_PREFIX}%"},
        )
        conn.execute(
            text(
                """
                DELETE FROM provider_companies
                WHERE slug LIKE :slug_prefix
                """
            ),
            {"slug_prefix": f"{TEST_SLUG_PREFIX}%"},
        )


def _insert_provider_and_tenant(engine, *, slug_suffix: str) -> uuid.UUID:
    provider_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    now = datetime.now(UTC)
    slug = f"{TEST_SLUG_PREFIX}{slug_suffix}"
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO provider_companies (
                    id, name, slug, is_active, created_at, updated_at
                )
                VALUES (:id, :name, :slug, :is_active, :created_at, :updated_at)
                """
            ),
            {
                "id": provider_id,
                "name": f"Provider {slug_suffix}",
                "slug": f"{TEST_SLUG_PREFIX}provider-{slug_suffix}",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO tenants (
                    id, provider_company_id, name, slug, industry_template_id,
                    status, created_at, updated_at
                )
                VALUES (
                    :id, :provider_company_id, :name, :slug, NULL,
                    'trial', :created_at, :updated_at
                )
                """
            ),
            {
                "id": tenant_id,
                "provider_company_id": provider_id,
                "name": f"Tenant {slug_suffix}",
                "slug": slug,
                "created_at": now,
                "updated_at": now,
            },
        )
    return tenant_id


def _revision_ancestors(script, revision_id: str) -> set[str]:
    revisions: set[str] = set()
    walk = script.get_revision(revision_id)
    while walk is not None:
        revisions.add(walk.revision)
        walk = (
            script.get_revision(walk.down_revision)
            if walk.down_revision is not None
            else None
        )
    return revisions


@pytest.fixture
def migration_engine():
    cfg = _alembic_config()
    _ensure_revision(cfg, "0013_c1c_payment_direction")
    engine = create_engine(_database_url())
    _cleanup_test_rows(engine)
    try:
        yield engine, cfg
    finally:
        _cleanup_test_rows(engine)
        engine.dispose()


def test_migration_chain_includes_0014_branches_baseline():
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(_alembic_config())
    rev = script.get_revision("0014_core_branches_baseline")
    assert rev is not None
    assert rev.down_revision == "0013_c1c_payment_direction"

    rev_0013 = script.get_revision("0013_c1c_payment_direction")
    assert rev_0013.down_revision == "0012_booking_e1"

    heads = script.get_heads()
    assert heads, "Alembic chain must have at least one head"
    for head in heads:
        assert "0014_core_branches_baseline" in _revision_ancestors(script, head)


def test_orm_tenant_branch_relationships_configure_without_ambiguity():
    import app.modules.models  # noqa: F401

    configure_mappers()


@postgres_required
def test_upgrade_0014_creates_branches_and_default_branch_column(migration_engine):
    engine, cfg = migration_engine
    tenant_id = _insert_provider_and_tenant(engine, slug_suffix="schema")

    _run_alembic(cfg, "0014_core_branches_baseline")

    inspector = inspect(engine)
    assert "branches" in inspector.get_table_names()
    branch_columns = {col["name"] for col in inspector.get_columns("branches")}
    assert branch_columns == {
        "id",
        "tenant_id",
        "code",
        "name",
        "is_active",
        "is_default",
        "created_at",
        "updated_at",
    }

    tenant_columns = {col["name"] for col in inspector.get_columns("tenants")}
    assert "default_branch_id" in tenant_columns

    branch_indexes = {idx["name"] for idx in inspector.get_indexes("branches")}
    assert "ix_branches_tenant_id" in branch_indexes

    tenant_indexes = {idx["name"] for idx in inspector.get_indexes("tenants")}
    assert "ix_tenants_default_branch_id" in tenant_indexes

    branch_uniques = {uc["name"] for uc in inspector.get_unique_constraints("branches")}
    assert "uq_branch_tenant_code" in branch_uniques

    tenant_fks = {fk["name"] for fk in inspector.get_foreign_keys("tenants")}
    assert "fk_tenants_default_branch_id_branches" in tenant_fks

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT t.default_branch_id, b.code, b.name, b.is_default, b.is_active
                FROM tenants t
                LEFT JOIN branches b ON b.id = t.default_branch_id
                WHERE t.id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        ).one()
    assert row.default_branch_id is not None
    assert row.code == "main"
    assert row.name == "Main branch"
    assert row.is_default is True
    assert row.is_active is True

    _go_to_revision(cfg, "0013_c1c_payment_direction")


@postgres_required
def test_upgrade_0014_backfills_existing_tenant_without_branch(migration_engine):
    engine, cfg = migration_engine
    tenant_id = _insert_provider_and_tenant(engine, slug_suffix="backfill")

    _run_alembic(cfg, "0014_core_branches_baseline")

    with engine.connect() as conn:
        tenant_row = conn.execute(
            text("SELECT default_branch_id FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id},
        ).one()
        branch_count = conn.execute(
            text("SELECT COUNT(*) FROM branches WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        ).scalar_one()

    assert tenant_row.default_branch_id is not None
    assert branch_count == 1

    _go_to_revision(cfg, "0013_c1c_payment_direction")


@postgres_required
def test_downgrade_0014_removes_branch_schema(migration_engine):
    engine, cfg = migration_engine
    _insert_provider_and_tenant(engine, slug_suffix="downgrade")

    _run_alembic(cfg, "0014_core_branches_baseline")
    _go_to_revision(cfg, "0013_c1c_payment_direction")

    inspector = inspect(engine)
    assert "branches" not in inspector.get_table_names()
    tenant_columns = {col["name"] for col in inspector.get_columns("tenants")}
    assert "default_branch_id" not in tenant_columns


@postgres_required
def test_upgrade_downgrade_upgrade_cycle_is_idempotent_for_backfill(migration_engine):
    engine, cfg = migration_engine
    tenant_id = _insert_provider_and_tenant(engine, slug_suffix="cycle")

    _run_alembic(cfg, "0014_core_branches_baseline")
    with engine.connect() as conn:
        first_branch_id = conn.execute(
            text("SELECT default_branch_id FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id},
        ).scalar_one()

    _go_to_revision(cfg, "0013_c1c_payment_direction")
    _run_alembic(cfg, "0014_core_branches_baseline")

    with engine.connect() as conn:
        second_branch_id = conn.execute(
            text("SELECT default_branch_id FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id},
        ).scalar_one()
        branch_count = conn.execute(
            text("SELECT COUNT(*) FROM branches WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        ).scalar_one()

    assert second_branch_id is not None
    assert branch_count == 1
    assert first_branch_id != second_branch_id

    _go_to_revision(cfg, "0013_c1c_payment_direction")
