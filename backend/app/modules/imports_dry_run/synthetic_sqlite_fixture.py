"""Build synthetic consulting legacy-shaped SQLite DB (no real personal data)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.modules.imports_dry_run.schema_fingerprint import EXPECTED_TABLES
from app.modules.imports_dry_run.synthetic_fixtures import build_consulting_synthetic_fixture

DDL = {
    "users": """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            login TEXT,
            is_active INTEGER
        )
    """,
    "clients": """
        CREATE TABLE clients (
            id TEXT PRIMARY KEY,
            status TEXT,
            party_type TEXT,
            display_name TEXT,
            email TEXT
        )
    """,
    "services": """
        CREATE TABLE services (
            id TEXT PRIMARY KEY,
            name TEXT
        )
    """,
    "orders": """
        CREATE TABLE orders (
            id TEXT PRIMARY KEY,
            number TEXT,
            client_id TEXT,
            status TEXT
        )
    """,
    "order_stages": """
        CREATE TABLE order_stages (
            id TEXT PRIMARY KEY,
            order_id TEXT,
            template_id TEXT,
            status TEXT
        )
    """,
    "order_items": """
        CREATE TABLE order_items (
            id TEXT PRIMARY KEY,
            order_id TEXT,
            service_id TEXT,
            amount TEXT
        )
    """,
    "contracts": """
        CREATE TABLE contracts (
            id TEXT PRIMARY KEY,
            number TEXT,
            client_id TEXT,
            order_id TEXT,
            status TEXT,
            amount TEXT
        )
    """,
    "payments": """
        CREATE TABLE payments (
            id TEXT PRIMARY KEY,
            order_id TEXT,
            client_id TEXT,
            type TEXT,
            amount TEXT
        )
    """,
}


def build_synthetic_sqlite_fixture(db_path: str | Path) -> Path:
    """
    Create/overwrite a synthetic SQLite file with C2a-compatible legacy tables.
    Uses only fictional local emails/names — no production data.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    # Assert DDL covers expected fingerprint tables.
    assert set(DDL) == set(EXPECTED_TABLES)

    fixture = build_consulting_synthetic_fixture()
    conn = sqlite3.connect(path)
    try:
        for table in EXPECTED_TABLES:
            conn.execute(DDL[table])

        def _bool_int(value) -> int:
            return 1 if value else 0

        for row in fixture["users"]:
            conn.execute(
                "INSERT INTO users(id, login, is_active) VALUES (?, ?, ?)",
                (row["id"], row["login"], _bool_int(row.get("is_active"))),
            )
        for row in fixture["clients"]:
            conn.execute(
                "INSERT INTO clients(id, status, party_type, display_name, email) VALUES (?, ?, ?, ?, ?)",
                (
                    row["id"],
                    row["status"],
                    row["party_type"],
                    row["display_name"],
                    row["email"],
                ),
            )
        for row in fixture["services"]:
            conn.execute(
                "INSERT INTO services(id, name) VALUES (?, ?)",
                (row["id"], row["name"]),
            )
        for row in fixture["orders"]:
            conn.execute(
                "INSERT INTO orders(id, number, client_id, status) VALUES (?, ?, ?, ?)",
                (row["id"], row["number"], row["client_id"], row["status"]),
            )
        for row in fixture["order_stages"]:
            conn.execute(
                "INSERT INTO order_stages(id, order_id, template_id, status) VALUES (?, ?, ?, ?)",
                (row["id"], row["order_id"], row["template_id"], row["status"]),
            )
        for row in fixture["order_items"]:
            conn.execute(
                "INSERT INTO order_items(id, order_id, service_id, amount) VALUES (?, ?, ?, ?)",
                (row["id"], row["order_id"], row["service_id"], str(row["amount"])),
            )
        for row in fixture["contracts"]:
            conn.execute(
                "INSERT INTO contracts(id, number, client_id, order_id, status, amount) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row["id"],
                    row["number"],
                    row["client_id"],
                    row["order_id"],
                    row["status"],
                    str(row["amount"]),
                ),
            )
        for row in fixture["payments"]:
            conn.execute(
                "INSERT INTO payments(id, order_id, client_id, type, amount) VALUES (?, ?, ?, ?, ?)",
                (
                    row["id"],
                    row["order_id"],
                    row["client_id"],
                    row["type"],
                    str(row["amount"]),
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return path.resolve()
