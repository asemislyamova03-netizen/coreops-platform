"""PostgreSQL + Alembic integration for M7.5 timestamp defaults hotfix.

Uses real migrations (not create_all). Skips when initdb/pg_ctl unavailable.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.deps import get_db
from app.main import app as fastapi_app

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")
EPHEMERAL_PG_DIR = BACKEND_ROOT / ".pytest_ephemeral_pg_m75_ts_api"

GUIDES = "/api/v1/marketing/guides"
RUBRICS = "/api/v1/marketing/rubrics"
PLANS = "/api/v1/marketing/content-plans"


def _find_pg_binary(name: str) -> str | None:
    return shutil.which(name)


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def pg_url():
    initdb = _find_pg_binary("initdb")
    pg_ctl = _find_pg_binary("pg_ctl")
    psql = _find_pg_binary("psql")
    if not initdb or not pg_ctl or not psql:
        pytest.skip("PostgreSQL binaries not available for ephemeral PG tests")

    pg_user = "ephemeral_pg_user"
    EPHEMERAL_PG_DIR.mkdir(parents=True, exist_ok=True)
    data_dir = EPHEMERAL_PG_DIR / "data"
    if data_dir.exists():
        subprocess.run(
            [pg_ctl, "-D", str(data_dir), "-m", "fast", "-w", "stop"],
            check=False,
        )
        shutil.rmtree(data_dir, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    port = _pick_free_port()
    subprocess.run([initdb, "-D", str(data_dir), "-U", pg_user, "-A", "trust"], check=True)
    conf = data_dir / "postgresql.conf"
    conf.write_text(
        conf.read_text(encoding="utf-8")
        + f"\nport = {port}\nlisten_addresses = '127.0.0.1'\n",
        encoding="utf-8",
    )
    (data_dir / "pg_hba.conf").write_text(
        "local all all trust\nhost all all 127.0.0.1/32 trust\nhost all all ::1/128 trust\n",
        encoding="utf-8",
    )
    subprocess.run(
        [pg_ctl, "-D", str(data_dir), "-l", str(EPHEMERAL_PG_DIR / "log.txt"), "-w", "start"],
        check=True,
    )
    db_name = "m75_ts_api"
    subprocess.run(
        [
            psql,
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            "-U",
            pg_user,
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            f"CREATE DATABASE {db_name};",
        ],
        check=True,
    )
    url = f"postgresql+psycopg://{pg_user}@127.0.0.1:{port}/{db_name}"
    yield url
    subprocess.run([pg_ctl, "-D", str(data_dir), "-m", "fast", "-w", "stop"], check=False)
    shutil.rmtree(EPHEMERAL_PG_DIR, ignore_errors=True)


@pytest.fixture(scope="module")
def pg_engine(pg_url):
    import os

    from app.core.config import get_settings
    from app.modules.industry_templates.service import IndustryTemplateService
    from app.modules.integrations.service import IntegrationService
    from app.modules.module_registry.service import ModuleRegistryService
    from app.modules.process_overlay.service import ProcessOverlayCatalogService
    from app.modules.subscriptions.service import SubscriptionService

    os.environ["DATABASE_URL"] = pg_url
    get_settings.cache_clear()

    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    engine = create_engine(pg_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    ModuleRegistryService(session).seed_definitions()
    SubscriptionService(session).seed_catalog()
    IndustryTemplateService(session).seed_templates()
    IntegrationService(session).seed_providers()
    ProcessOverlayCatalogService(session).seed_templates()
    session.commit()
    session.close()
    yield engine
    engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def pg_client(pg_url, pg_engine, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg_url)
    get_settings.cache_clear()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    session = SessionLocal()

    def override_get_db(request: Request):
        try:
            request.state.db = session
            yield session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client, session
    finally:
        session.rollback()
        session.close()
        fastapi_app.dependency_overrides.clear()
        get_settings.cache_clear()


_OWNER_EMAIL = "m75ts-owner@example.com"
_OWNER_PASSWORD = "securepass123"
_OWNER_BOOTSTRAPPED = False


def _setup(client: TestClient, *, suffix: str) -> dict[str, str]:
    global _OWNER_BOOTSTRAPPED
    if not _OWNER_BOOTSTRAPPED:
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": _OWNER_EMAIL,
                "password": _OWNER_PASSWORD,
                "full_name": "M75TS Owner",
                "company_name": "M75TS Owner Co",
                "company_slug": "m75ts-owner-co",
            },
        )
        assert reg.status_code == 201, reg.text
        _OWNER_BOOTSTRAPPED = True

    login = client.post(
        "/api/v1/auth/login",
        json={"email": _OWNER_EMAIL, "password": _OWNER_PASSWORD},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    tenant = client.post(
        "/api/v1/tenants",
        json={"name": f"M75TS Tenant {suffix}", "slug": f"m75ts-tenant-{suffix}"},
        headers=headers,
    )
    assert tenant.status_code == 201, tenant.text
    tenant_id = tenant.json()["id"]
    headers = {**headers, "X-Tenant-ID": tenant_id}
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers
        ).status_code
        == 200
    )
    return headers


def test_pg_alembic_guide_rubric_plan_item_timestamps_not_null(pg_client, pg_engine):
    client, _session = pg_client
    headers = _setup(client, suffix="create-ts")

    guide = client.post(
        GUIDES,
        headers=headers,
        json={
            "business_name": "Flexity",
            "business_summary": "summary",
            "products_services": "products",
            "audiences": "audiences",
            "goals": "goals",
            "channels": ["telegram"],
            "default_frequency": "weekly",
            "activate": False,
        },
    )
    assert guide.status_code == 201, guide.text
    assert guide.json()["created_at"]
    assert guide.json().get("created_at") is not None

    rubric = client.post(
        RUBRICS,
        headers=headers,
        json={"code": "offer", "name": "Offer", "sort_order": 1},
    )
    assert rubric.status_code == 201, rubric.text
    assert rubric.json()["created_at"]

    plan = client.post(
        PLANS,
        headers=headers,
        json={
            "title": "August",
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
        },
    )
    assert plan.status_code == 201, plan.text
    assert plan.json()["created_at"]

    item = client.post(
        f"{PLANS}/{plan.json()['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-05",
            "rubric_id": rubric.json()["id"],
            "working_title": "Line 1",
            "channels": ["telegram"],
        },
    )
    assert item.status_code == 201, item.text
    assert item.json()["created_at"]

    with pg_engine.connect() as conn:
        for table, row_id in (
            ("marketing_guides", guide.json()["id"]),
            ("marketing_rubrics", rubric.json()["id"]),
            ("marketing_content_plans", plan.json()["id"]),
            ("marketing_content_plan_items", item.json()["id"]),
        ):
            row = conn.execute(
                text(
                    f"SELECT created_at IS NOT NULL AS c_ok, "
                    f"updated_at IS NOT NULL AS u_ok FROM {table} WHERE id = :id"
                ),
                {"id": row_id},
            ).mappings().one()
            assert row["c_ok"] is True
            assert row["u_ok"] is True


def test_pg_rubric_duplicate_and_cross_tenant_ok(pg_client):
    client, _session = pg_client
    h1 = _setup(client, suffix="dup-a")
    h2 = _setup(client, suffix="dup-b")

    assert (
        client.post(
            RUBRICS, headers=h1, json={"code": "shared_code", "name": "A"}
        ).status_code
        == 201
    )
    dup = client.post(RUBRICS, headers=h1, json={"code": "shared_code", "name": "A2"})
    assert dup.status_code == 409
    assert dup.json()["detail"] == "marketing_rubric_duplicate"

    other = client.post(RUBRICS, headers=h2, json={"code": "shared_code", "name": "B"})
    assert other.status_code == 201, other.text


def test_pg_raw_insert_without_timestamps_uses_db_default(pg_engine, pg_client):
    """Exact stage failure mode: INSERT omits created_at/updated_at."""
    import uuid

    client, session = pg_client
    headers = _setup(client, suffix="raw-default")
    tenant_id = headers["X-Tenant-ID"]
    session.commit()
    guide_id = str(uuid.uuid4())

    with pg_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO marketing_guides (
                    id, tenant_id, version, status, business_name, business_summary,
                    products_services, audiences, goals, channels, default_frequency,
                    extra_json
                ) VALUES (
                    CAST(:gid AS uuid), CAST(:tid AS uuid), 99, 'draft',
                    'Raw', 's', 'p', 'a', 'g', '[]'::json, 'weekly', '{}'::json
                )
                """
            ),
            {"gid": guide_id, "tid": tenant_id},
        )
        row = conn.execute(
            text(
                """
                SELECT created_at IS NOT NULL AS c_ok, updated_at IS NOT NULL AS u_ok
                FROM marketing_guides
                WHERE id = CAST(:gid AS uuid)
                """
            ),
            {"gid": guide_id},
        ).mappings().one()
    assert row["c_ok"] is True
    assert row["u_ok"] is True
