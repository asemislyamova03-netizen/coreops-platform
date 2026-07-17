"""Build production-shaped Gate B SQLite fixture (synthetic data only, for tests)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.modules.imports_dry_run.synthetic_fixtures import build_consulting_synthetic_fixture

# Production-like DDL: INTEGER ids, users.email/name, clients.name (not display_name).
PRODUCTION_GATE_B_DDL = {
    "users": """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT,
            name TEXT,
            is_active INTEGER DEFAULT 1,
            password_hash TEXT
        )
    """,
    "clients": """
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY,
            status TEXT,
            party_type TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            iin_bin TEXT,
            address TEXT,
            note TEXT
        )
    """,
    "services": """
        CREATE TABLE services (
            id INTEGER PRIMARY KEY,
            code TEXT,
            title TEXT,
            unit_price TEXT,
            program_name TEXT
        )
    """,
    "orders": """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            number TEXT,
            client_id INTEGER,
            status TEXT,
            total_amount TEXT
        )
    """,
    "order_stages": """
        CREATE TABLE order_stages (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            template_id INTEGER,
            status TEXT
        )
    """,
    "order_items": """
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            service_id INTEGER,
            qty INTEGER,
            unit_price TEXT
        )
    """,
    "contracts": """
        CREATE TABLE contracts (
            id INTEGER PRIMARY KEY,
            number TEXT,
            client_id INTEGER,
            order_id INTEGER,
            status TEXT,
            amount TEXT
        )
    """,
    "payments": """
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            client_id INTEGER,
            type TEXT,
            amount TEXT,
            counterparty_name TEXT,
            purpose TEXT
        )
    """,
    # Extra table to simulate production DB having more than wave-1 (52-table inventory).
    "roles": """
        CREATE TABLE roles (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """,
}


def _synthetic_id_to_int(synthetic_id: str) -> int:
    digits = "".join(ch for ch in synthetic_id if ch.isdigit())
    return int(digits) if digits else abs(hash(synthetic_id)) % 10_000


def build_production_gate_b_sqlite_fixture(db_path: str | Path) -> Path:
    """
    Create a production-shaped SQLite file using only fictional synthetic fixture data.
    No real client PII. For local tests only.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    fixture = build_consulting_synthetic_fixture()
    conn = sqlite3.connect(path)
    try:
        for ddl in PRODUCTION_GATE_B_DDL.values():
            conn.execute(ddl)

        def _bool_int(value) -> int:
            return 1 if value else 0

        for row in fixture["users"]:
            uid = _synthetic_id_to_int(row["id"])
            conn.execute(
                "INSERT INTO users(id, email, name, is_active, password_hash) VALUES (?, ?, ?, ?, ?)",
                (uid, f"{row['login']}@synthetic.local", f"User {uid}", _bool_int(row.get("is_active")), "hash"),
            )
        for row in fixture["clients"]:
            cid = _synthetic_id_to_int(row["id"])
            conn.execute(
                "INSERT INTO clients(id, status, party_type, name, email, phone, iin_bin, address, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    cid,
                    row["status"],
                    row["party_type"],
                    row["display_name"],
                    row["email"],
                    "+70000000000",
                    "000000000000",
                    "Synthetic Address",
                    "synthetic note",
                ),
            )
        for row in fixture["services"]:
            sid = _synthetic_id_to_int(row["id"])
            conn.execute(
                "INSERT INTO services(id, code, title, unit_price, program_name) VALUES (?, ?, ?, ?, ?)",
                (
                    sid,
                    f"SVC-{sid}",
                    row["name"],
                    str(row.get("amount", "0")),
                    "Synthetic Program",
                ),
            )
        for row in fixture["orders"]:
            oid = _synthetic_id_to_int(row["id"])
            cid = _synthetic_id_to_int(row["client_id"]) if row["client_id"] != "c-404" else 9999
            conn.execute(
                "INSERT INTO orders(id, number, client_id, status, total_amount) VALUES (?, ?, ?, ?, ?)",
                (oid, row["number"], cid, row["status"], "0"),
            )
        for row in fixture["order_stages"]:
            osid = _synthetic_id_to_int(row["id"])
            oid = _synthetic_id_to_int(row["order_id"]) if row["order_id"] != "o-x" else 9998
            tid = _synthetic_id_to_int(row["template_id"]) if row.get("template_id") else None
            conn.execute(
                "INSERT INTO order_stages(id, order_id, template_id, status) VALUES (?, ?, ?, ?)",
                (osid, oid, tid, row["status"]),
            )
        for row in fixture["order_items"]:
            oiid = _synthetic_id_to_int(row["id"])
            oid = _synthetic_id_to_int(row["order_id"]) if row["order_id"] != "o-x" else 9998
            sid = _synthetic_id_to_int(row["service_id"]) if row["service_id"] != "s-x" else 9997
            conn.execute(
                "INSERT INTO order_items(id, order_id, service_id, qty, unit_price) VALUES (?, ?, ?, ?, ?)",
                (oiid, oid, sid, 1, str(row["amount"])),
            )
        # Add deterministic order totals for reconciliation tests:
        # two match, one mismatch.
        conn.execute("UPDATE orders SET total_amount='10000' WHERE id=1")
        conn.execute("UPDATE orders SET total_amount='5000' WHERE id=2")
        conn.execute("UPDATE orders SET total_amount='9999' WHERE id=3")
        for row in fixture["contracts"]:
            ctid = _synthetic_id_to_int(row["id"])
            cid = _synthetic_id_to_int(row["client_id"])
            oid = _synthetic_id_to_int(row["order_id"]) if row.get("order_id") else None
            conn.execute(
                "INSERT INTO contracts(id, number, client_id, order_id, status, amount) VALUES (?, ?, ?, ?, ?, ?)",
                (ctid, row["number"], cid, oid, row["status"], str(row["amount"])),
            )
        for row in fixture["payments"]:
            pid = _synthetic_id_to_int(row["id"])
            oid = _synthetic_id_to_int(row["order_id"]) if row["order_id"] != "o-x" else 9998
            cid = _synthetic_id_to_int(row["client_id"])
            conn.execute(
                "INSERT INTO payments(id, order_id, client_id, type, amount, counterparty_name, purpose) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, oid, cid, row["type"], str(row["amount"]), "Synthetic Counterparty", "synthetic purpose"),
            )
        conn.execute("INSERT INTO roles(id, name) VALUES (1, 'owner')")
        conn.commit()
    finally:
        conn.close()
    return path.resolve()
