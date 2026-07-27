"""M7.5 timestamp-default hotfix: Alembic 0029 revision checks + PG defaults."""

from __future__ import annotations

import importlib.util
import shutil
import socket
import subprocess
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")
REVISION_0028 = "0028_mkt_content_plans"
REVISION_0029 = "0029_mkt_timestamp_defaults"
MIGRATION_FILENAME = "20260728_0029_mkt_timestamp_defaults.py"
EPHEMERAL_PG_DIR = BACKEND_ROOT / ".pytest_ephemeral_pg_m75_0029"

_TABLES = (
    "marketing_guides",
    "marketing_rubrics",
    "marketing_content_plans",
    "marketing_content_plan_items",
)
_COLUMNS = ("created_at", "updated_at")


def _load_migration_module():
    migration_path = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME
    spec = importlib.util.spec_from_file_location("migration_0029", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_0029_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0029)
    assert rev is not None
    assert rev.down_revision == REVISION_0028
    assert len(REVISION_0029) <= 32

    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == REVISION_0029


def test_0029_migration_module_importable():
    module = _load_migration_module()
    assert module.revision == REVISION_0029
    assert module.down_revision == REVISION_0028
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    src = (BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME).read_text(
        encoding="utf-8"
    )
    for table in _TABLES:
        assert table in src
    assert "SET DEFAULT now()" in src
    assert "DROP DEFAULT" in src
    assert "DROP TABLE" not in src.split("def downgrade", 1)[1]
    assert "DELETE FROM" not in src.split("def downgrade", 1)[1]


def test_0028_is_ancestor_not_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    assert REVISION_0028 not in script.get_heads()
    rev = script.get_revision(REVISION_0028)
    assert rev is not None
    assert rev.down_revision == "0027_mkt_guides_rubrics"


def _find_pg_binary(name: str) -> str | None:
    return shutil.which(name)


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _column_defaults(engine) -> dict[tuple[str, str], str | None]:
    out: dict[tuple[str, str], str | None] = {}
    with engine.connect() as conn:
        for table in _TABLES:
            for column in _COLUMNS:
                value = conn.execute(
                    text(
                        """
                        SELECT column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = :table_name
                          AND column_name = :column_name
                        """
                    ),
                    {"table_name": table, "column_name": column},
                ).scalar_one_or_none()
                out[(table, column)] = value
    return out


def _has_now_default(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return "now()" in lowered or "current_timestamp" in lowered


@pytest.fixture(scope="module")
def ephemeral_postgres_url_0029():
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
    db_name = "m75_ts_defaults_0029"
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


def test_0029_upgrade_sets_defaults_and_downgrade_drops_only(
    ephemeral_postgres_url_0029, monkeypatch
):
    from app.core.config import get_settings

    monkeypatch.setenv("DATABASE_URL", ephemeral_postgres_url_0029)
    get_settings.cache_clear()

    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", ephemeral_postgres_url_0029)
    command.upgrade(cfg, REVISION_0028)

    engine = create_engine(ephemeral_postgres_url_0029)
    try:
        before = _column_defaults(engine)
        for table in _TABLES:
            for column in _COLUMNS:
                assert not _has_now_default(before.get((table, column))), (
                    table,
                    column,
                    before.get((table, column)),
                )

        # Probe row proves downgrade does not delete data.
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE m75_ts_probe (id integer PRIMARY KEY)"))
            conn.execute(text("INSERT INTO m75_ts_probe (id) VALUES (1)"))

        command.upgrade(cfg, REVISION_0029)
        after_up = _column_defaults(engine)
        for table in _TABLES:
            for column in _COLUMNS:
                assert _has_now_default(after_up.get((table, column))), (
                    table,
                    column,
                    after_up.get((table, column)),
                )

        with engine.connect() as conn:
            probe = conn.execute(text("SELECT count(*) FROM m75_ts_probe")).scalar_one()
        assert probe == 1

        command.downgrade(cfg, REVISION_0028)
        after_down = _column_defaults(engine)
        for table in _TABLES:
            for column in _COLUMNS:
                assert not _has_now_default(after_down.get((table, column))), (
                    table,
                    column,
                    after_down.get((table, column)),
                )

        with engine.connect() as conn:
            probe = conn.execute(text("SELECT count(*) FROM m75_ts_probe")).scalar_one()
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert probe == 1
        assert version == REVISION_0028
    finally:
        engine.dispose()
        get_settings.cache_clear()
