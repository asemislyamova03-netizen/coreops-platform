"""Production Gate B schema profile for real-source read-only dry-run."""

from __future__ import annotations

import hashlib
import sqlite3

from app.modules.imports_dry_run.schema_fingerprint import _normalize_type

# Wave-1 tables and minimum required columns (Gate A / Gate 3 first import wave).
GATE_B_WAVE1_REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": ("id", "email", "name"),
    "clients": ("id", "status", "party_type", "name", "email"),
    "services": ("id", "code", "title", "unit_price"),
    "orders": ("id", "number", "client_id", "status"),
    "order_stages": ("id", "order_id", "status"),
    "order_items": ("id", "order_id", "service_id", "qty", "unit_price"),
    "contracts": ("id", "number", "client_id", "order_id", "status", "amount"),
    "payments": ("id", "order_id", "client_id", "type", "amount"),
}

# Optional columns used when present (not required for schema pass).
GATE_B_WAVE1_OPTIONAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": ("is_active",),
    "order_stages": ("template_id",),
}


class ProductionSchemaError(RuntimeError):
    """Raised when production Gate B schema requirements are not met."""


def _table_columns(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1]): _normalize_type(row[2]) for row in rows}


def assert_production_gate_b_schema(conn: sqlite3.Connection) -> str:
    """
    Verify wave-1 tables exist with required columns.
    Extra production columns are allowed; missing required columns fail closed.
    Returns fingerprint hash of required column names+types per wave-1 table.
    """
    lines: list[str] = []
    for table in sorted(GATE_B_WAVE1_REQUIRED_COLUMNS):
        try:
            cols = _table_columns(conn, table)
        except sqlite3.Error as exc:
            raise ProductionSchemaError(f"Failed to read schema for table {table}: {exc}") from exc

        if not cols:
            raise ProductionSchemaError(f"Missing required table: {table}")

        required = GATE_B_WAVE1_REQUIRED_COLUMNS[table]
        missing = [name for name in required if name not in cols]
        if missing:
            raise ProductionSchemaError(
                f"Table {table} missing required columns: {', '.join(missing)}"
            )

        optional = GATE_B_WAVE1_OPTIONAL_COLUMNS.get(table, ())
        selected = required + tuple(name for name in optional if name in cols)
        col_sig = ",".join(f"{name}:{cols[name]}" for name in selected)
        lines.append(f"{table}:{col_sig}")

    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
