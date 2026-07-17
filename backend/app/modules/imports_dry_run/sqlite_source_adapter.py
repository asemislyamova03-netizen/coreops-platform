"""Read-only SQLite source adapter for C2b (synthetic fixture and Gate B production profile)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from app.modules.imports_dry_run.production_schema_fingerprint import assert_production_gate_b_schema
from app.modules.imports_dry_run.schema_fingerprint import assert_schema_matches_expected
from app.modules.imports_dry_run.sqlite_readonly import (
    PathGuardMode,
    open_readonly_sqlite_uri,
)

DOMAIN_TABLES = (
    "users",
    "clients",
    "services",
    "orders",
    "order_stages",
    "order_items",
    "contracts",
    "payments",
)

SOURCE_SYSTEM = "legacy_consult_app"

SchemaProfile = Literal["synthetic", "production_gate_b"]

PRODUCTION_SELECT_SQL: dict[str, str] = {
    "users": "SELECT id, email, name FROM users ORDER BY id",
    "clients": "SELECT id, status, party_type, name, email FROM clients ORDER BY id",
    "services": "SELECT id, code, title, unit_price, program_name FROM services ORDER BY id",
    "orders": "SELECT id, number, client_id, status, total_amount FROM orders ORDER BY id",
    "order_stages": "SELECT id, order_id, template_id, status FROM order_stages ORDER BY id",
    "order_items": "SELECT id, order_id, service_id, qty, unit_price FROM order_items ORDER BY id",
    "contracts": (
        "SELECT id, number, client_id, order_id, status, amount FROM contracts ORDER BY id"
    ),
    "payments": "SELECT id, order_id, client_id, type, amount FROM payments ORDER BY id",
}


def _row_to_dict(row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _coerce_amount(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _coerce_decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Decimal(text)


def _coerce_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_synthetic_domain_row(table: str, raw: dict[str, Any]) -> dict[str, Any]:
    row = dict(raw)
    if table == "users":
        row["is_active"] = bool(row.get("is_active"))
    if table in {"order_items", "contracts", "payments"} and "amount" in row:
        row["amount"] = _coerce_amount(row.get("amount"))
    return row


def _normalize_production_domain_row(table: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Project production columns into C2a/C2b pipeline domain dict shape."""
    if table == "users":
        email = raw.get("email") or ""
        name = raw.get("name") or ""
        return {
            "id": _coerce_id(raw.get("id")),
            "login": email or name,
            "is_active": bool(raw.get("is_active", 1)),
        }
    if table == "clients":
        return {
            "id": _coerce_id(raw.get("id")),
            "status": raw.get("status") or "",
            "party_type": raw.get("party_type") or "",
            "display_name": raw.get("name") or raw.get("display_name") or "",
            "email": raw.get("email") or "",
        }
    if table == "services":
        service_id = _coerce_id(raw.get("id"))
        source_title = str(raw.get("title") or "").strip()
        source_code = str(raw.get("code") or "").strip()
        if source_title:
            mapped_name = source_title
        elif source_code:
            mapped_name = source_code
        else:
            mapped_name = f"Service {service_id or 'unknown'}"
        return {
            "id": service_id,
            "name": mapped_name,
            "source_title": source_title,
            "source_code": source_code,
            "unit_price": _coerce_decimal_or_none(raw.get("unit_price")),
            "program_name": str(raw.get("program_name") or "").strip(),
            "service_name_needs_review": not bool(source_title),
        }
    if table == "orders":
        return {
            "id": _coerce_id(raw.get("id")),
            "number": raw.get("number") or "",
            "client_id": _coerce_id(raw.get("client_id")),
            "status": raw.get("status") or "",
            "total_amount": _coerce_decimal_or_none(raw.get("total_amount")),
        }
    if table == "order_stages":
        template_id = raw.get("template_id")
        return {
            "id": _coerce_id(raw.get("id")),
            "order_id": _coerce_id(raw.get("order_id")),
            "template_id": _coerce_id(template_id) if template_id is not None else None,
            "status": raw.get("status") or "",
        }
    if table == "order_items":
        qty = _coerce_decimal_or_none(raw.get("qty"))
        unit_price = _coerce_decimal_or_none(raw.get("unit_price"))
        derived_amount: Decimal | None = None
        if qty is not None and unit_price is not None:
            derived_amount = qty * unit_price
        return {
            "id": _coerce_id(raw.get("id")),
            "order_id": _coerce_id(raw.get("order_id")),
            "service_id": _coerce_id(raw.get("service_id")),
            "qty": qty,
            "unit_price": unit_price,
            "amount": derived_amount if derived_amount is not None else Decimal("0"),
        }
    if table == "contracts":
        order_id = raw.get("order_id")
        return {
            "id": _coerce_id(raw.get("id")),
            "number": raw.get("number") or "",
            "client_id": _coerce_id(raw.get("client_id")),
            "order_id": _coerce_id(order_id) if order_id is not None else None,
            "status": raw.get("status") or "",
            "amount": _coerce_amount(raw.get("amount")),
        }
    if table == "payments":
        return {
            "id": _coerce_id(raw.get("id")),
            "order_id": _coerce_id(raw.get("order_id")),
            "client_id": _coerce_id(raw.get("client_id")),
            "type": raw.get("type") or "",
            "amount": _coerce_amount(raw.get("amount")),
        }
    raise ValueError(f"Unsupported domain table: {table}")


class ReadonlySqliteSourceAdapter:
    """
    Loads legacy-shaped domain dicts from a local SQLite file in read-only mode.
    Output contract matches SyntheticSourceAdapter.load().
    Does not call mapper/validator; does not write Core.
    """

    def __init__(
        self,
        db_path: str | Path,
        *,
        schema_profile: SchemaProfile = "synthetic",
        path_guard: PathGuardMode | None = None,
        max_rows_per_table: int | None = None,
        allow_schema_mismatch: bool = False,
        source_system: str = SOURCE_SYSTEM,
    ):
        self.db_path = Path(db_path)
        self.schema_profile = schema_profile
        if path_guard is None:
            path_guard = "real_source" if schema_profile == "production_gate_b" else "synthetic"
        self.path_guard = path_guard
        self.max_rows_per_table = max_rows_per_table
        self.allow_schema_mismatch = allow_schema_mismatch
        self.source_system = source_system
        self.last_schema_fingerprint: str | None = None
        self.last_row_counts: dict[str, int] = {}
        self.last_amount_reconciliation_summary: dict[str, int | str] = {}
        self.last_services_mapping_summary: dict[str, int] = {}

    def load(self) -> dict[str, list[dict]]:
        conn = open_readonly_sqlite_uri(self.db_path, path_guard=self.path_guard)
        try:
            if self.schema_profile == "synthetic":
                self.last_schema_fingerprint = assert_schema_matches_expected(
                    conn,
                    allow_mismatch=self.allow_schema_mismatch,
                )
            else:
                self.last_schema_fingerprint = assert_production_gate_b_schema(conn)

            data: dict[str, list[dict]] = {}
            for table in DOMAIN_TABLES:
                rows = self._read_table(conn, table)
                data[table] = rows
                self.last_row_counts[table] = len(rows)
            if self.schema_profile == "production_gate_b":
                self.last_amount_reconciliation_summary = self._compute_amount_reconciliation(data)
                self.last_services_mapping_summary = self._compute_services_mapping_summary(data)
            return data
        finally:
            conn.close()

    def _compute_services_mapping_summary(self, data: dict[str, list[dict]]) -> dict[str, int]:
        services = data.get("services", [])
        services_count = len(services)
        title_present_count = 0
        title_missing_count = 0
        code_present_count = 0
        name_fallback_count = 0
        name_generated_count = 0

        for service in services:
            source_title = str(service.get("source_title") or "").strip()
            source_code = str(service.get("source_code") or "").strip()
            mapped_name = str(service.get("name") or "").strip()
            if source_title:
                title_present_count += 1
            else:
                title_missing_count += 1
            if source_code:
                code_present_count += 1
            if not source_title and source_code and mapped_name == source_code:
                name_fallback_count += 1
            if not source_title and not source_code and mapped_name.startswith("Service "):
                name_generated_count += 1

        return {
            "services_count": int(services_count),
            "services_title_present_count": int(title_present_count),
            "services_title_missing_count": int(title_missing_count),
            "services_code_present_count": int(code_present_count),
            "services_name_fallback_count": int(name_fallback_count),
            "services_name_generated_count": int(name_generated_count),
        }

    def _compute_amount_reconciliation(self, data: dict[str, list[dict]]) -> dict[str, int | str]:
        order_items = data.get("order_items", [])
        orders = data.get("orders", [])

        derived_line_amount_count = 0
        order_sum_by_id: dict[str, Decimal] = {}
        for line in order_items:
            order_id = str(line.get("order_id") or "")
            qty = line.get("qty")
            unit_price = line.get("unit_price")
            if not order_id:
                continue
            if qty is None or unit_price is None:
                continue
            derived = Decimal(str(qty)) * Decimal(str(unit_price))
            derived_line_amount_count += 1
            order_sum_by_id[order_id] = order_sum_by_id.get(order_id, Decimal("0")) + derived

        match_count = 0
        mismatch_count = 0
        missing_count = 0
        tolerance = Decimal("0.01")
        for order in orders:
            order_id = str(order.get("id") or "")
            order_total = order.get("total_amount")
            derived_total = order_sum_by_id.get(order_id)
            if order_total is None or derived_total is None:
                missing_count += 1
                continue
            if abs(Decimal(str(order_total)) - derived_total) <= tolerance:
                match_count += 1
            else:
                mismatch_count += 1

        checked_count = match_count + mismatch_count
        if mismatch_count > 0:
            status = "has_mismatch"
        elif checked_count > 0:
            status = "all_match"
        else:
            status = "insufficient_data"
        return {
            "derived_line_amount_count": int(derived_line_amount_count),
            "order_total_match_count": int(match_count),
            "order_total_mismatch_count": int(mismatch_count),
            "order_total_missing_count": int(missing_count),
            "order_total_reconciliation_checked_count": int(checked_count),
            "amount_reconciliation_status": status,
        }

    def _read_table(self, conn, table: str) -> list[dict]:
        if table not in DOMAIN_TABLES:
            raise ValueError(f"Unsupported domain table: {table}")

        if self.schema_profile == "production_gate_b":
            sql = PRODUCTION_SELECT_SQL[table]
            normalize = _normalize_production_domain_row
        else:
            sql = f"SELECT * FROM {table} ORDER BY id"
            normalize = _normalize_synthetic_domain_row

        params: tuple[Any, ...] = ()
        if self.max_rows_per_table is not None:
            sql += " LIMIT ?"
            params = (int(self.max_rows_per_table),)

        cursor = conn.execute(sql, params)
        return [normalize(table, _row_to_dict(row)) for row in cursor.fetchall()]
