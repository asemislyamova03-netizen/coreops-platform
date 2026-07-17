"""Schema fingerprint helpers for legacy SQLite source adapters."""

from __future__ import annotations

import hashlib
import sqlite3

# Domains aligned with C2a synthetic fixture keys.
EXPECTED_TABLES: dict[str, list[tuple[str, str]]] = {
    "users": [("id", "TEXT"), ("login", "TEXT"), ("is_active", "INTEGER")],
    "clients": [
        ("id", "TEXT"),
        ("status", "TEXT"),
        ("party_type", "TEXT"),
        ("display_name", "TEXT"),
        ("email", "TEXT"),
    ],
    "services": [("id", "TEXT"), ("name", "TEXT")],
    "orders": [
        ("id", "TEXT"),
        ("number", "TEXT"),
        ("client_id", "TEXT"),
        ("status", "TEXT"),
    ],
    "order_stages": [
        ("id", "TEXT"),
        ("order_id", "TEXT"),
        ("template_id", "TEXT"),
        ("status", "TEXT"),
    ],
    "order_items": [
        ("id", "TEXT"),
        ("order_id", "TEXT"),
        ("service_id", "TEXT"),
        ("amount", "TEXT"),
    ],
    "contracts": [
        ("id", "TEXT"),
        ("number", "TEXT"),
        ("client_id", "TEXT"),
        ("order_id", "TEXT"),
        ("status", "TEXT"),
        ("amount", "TEXT"),
    ],
    "payments": [
        ("id", "TEXT"),
        ("order_id", "TEXT"),
        ("client_id", "TEXT"),
        ("type", "TEXT"),
        ("amount", "TEXT"),
    ],
}


class SchemaMismatchError(RuntimeError):
    """Raised when SQLite schema fingerprint does not match expected baseline."""


def _normalize_type(declared: str | None) -> str:
    raw = (declared or "TEXT").upper().strip()
    if "INT" in raw:
        return "INTEGER"
    if "CHAR" in raw or "CLOB" in raw or "TEXT" in raw:
        return "TEXT"
    if "REAL" in raw or "FLOA" in raw or "DOUB" in raw:
        return "REAL"
    if "BLOB" in raw:
        return "BLOB"
    return "TEXT"


def fingerprint_from_spec(spec: dict[str, list[tuple[str, str]]]) -> str:
    lines: list[str] = []
    for table in sorted(spec):
        cols = ",".join(f"{name}:{_normalize_type(col_type)}" for name, col_type in spec[table])
        lines.append(f"{table}:{cols}")
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


EXPECTED_SCHEMA_FINGERPRINT = fingerprint_from_spec(EXPECTED_TABLES)


def read_schema_spec(conn: sqlite3.Connection) -> dict[str, list[tuple[str, str]]]:
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    spec: dict[str, list[tuple[str, str]]] = {}
    for table in tables:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        # cid, name, type, notnull, dflt_value, pk
        spec[table] = [(str(col[1]), _normalize_type(col[2])) for col in cols]
    return spec


def compute_schema_fingerprint(conn: sqlite3.Connection) -> str:
    return fingerprint_from_spec(read_schema_spec(conn))


def assert_schema_matches_expected(
    conn: sqlite3.Connection,
    *,
    expected_fingerprint: str = EXPECTED_SCHEMA_FINGERPRINT,
    allow_mismatch: bool = False,
) -> str:
    actual = compute_schema_fingerprint(conn)
    if actual != expected_fingerprint and not allow_mismatch:
        raise SchemaMismatchError(
            f"SQLite schema fingerprint mismatch: expected={expected_fingerprint[:12]}… "
            f"actual={actual[:12]}… (set allow_schema_mismatch only after explicit review)"
        )
    return actual
