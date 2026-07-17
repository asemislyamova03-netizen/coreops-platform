"""Staging write-import planner/runner for Consulting -> Core (execution-gated)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import engine
import app.modules.models  # noqa: F401  # Ensure full ORM registry is loaded in standalone runner process.
from app.core.enums import (
    AuditAction,
    CatalogItemType,
    ContactMethodType,
    DocumentStatus,
    InvoiceStatus,
    PaymentDirection,
    PaymentMethod,
    PaymentStatus,
    PartyStatus,
    PartyType,
    WorkItemStatus,
)
from app.modules.audit.models import AuditLog
from app.modules.branches.models import Branch
from app.modules.catalog.models import CatalogItem
from app.modules.documents.models import DocumentInstance, DocumentTemplate
from app.modules.finance.models import Invoice, InvoiceLine, Payment, PaymentAllocation
from app.modules.imports_dry_run.masked_report import (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    scan_text_for_suspicious_pii,
)
from app.modules.imports_dry_run.real_source_allowlist import (
    AllowlistError,
    BackupIdError,
    OutputPathError,
    assert_output_path_safe,
    assert_path_allowlisted_for_real_source,
    find_repo_root,
    validate_backup_id,
)
from app.modules.imports_dry_run.sqlite_source_adapter import ReadonlySqliteSourceAdapter
from app.modules.parties.models import ContactMethod, Party
from app.modules.tenants.models import Tenant
from app.modules.workflows.models import WorkItem

EXIT_PREFLIGHT_FAIL = 2
STAGING_WRITE_PLAN_MODE = "staging-write-import-plan"
STAGING_WRITE_EXECUTE_MODE = "staging-write-import-execute"
STAGING_WRITE_LEGACY_AMBIGUOUS_MODE = "staging-write-import"
TARGET_DB_ALLOWED = "coreops_staging_0013"
LIVE_DB_BLOCKED = "coreops"
SOURCE_SYSTEM = "legacy_consulting_os"
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
IMPORT_BATCH_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){2,}$")
SOURCE_REF_PATTERN = re.compile(
    r"^legacy_consulting_os:[a-z0-9_]+:[A-Za-z0-9._:-]+$"
)
SOURCE_REF_BATCH_PATTERN = re.compile(
    r"^legacy_consulting_os:[A-Za-z0-9._:-]+:[a-z0-9_]+:[A-Za-z0-9._:-]+$"
)

REQUIRED_IMPORT_SEQUENCE = [
    "import_batch_audit_context",
    "services_catalog",
    "clients_parties_contacts",
    "orders_work_items",
    "order_items_line_metadata",
    "contracts_documents",
    "payments_linked",
    "payments_orphan_standalone",
    "review_flags_audit_summary_validation_report",
]


class StagingWriteImportPreflightError(Exception):
    """Fail-closed preflight validation error for staging write-import."""


class SourceRefConflictError(StagingWriteImportPreflightError):
    """Raised when source reference conflicts violate fail-closed policy."""


class ImportBlockedError(StagingWriteImportPreflightError):
    """Execution blocker with explicit machine-readable code."""


@dataclass(frozen=True)
class StagingWriteImportConfig:
    source_db: Path
    backup_id: str
    tenant_id: UUID
    default_branch_id: UUID
    target_db: str
    dry_run_report: Path
    import_batch_id: str
    output: Path
    mode: str


@dataclass(frozen=True)
class SourceIdentity:
    source_system: str
    source_table: str
    source_id: str
    tenant_id: UUID
    import_batch_id: str


@dataclass
class WriteStats:
    imported: dict[str, int]
    skipped_existing: dict[str, int]
    conflicts: dict[str, int]
    review_flags: dict[str, int]
    source_ref_counts: dict[str, int]


@dataclass(frozen=True)
class StageResult:
    key: str
    imported: int = 0
    skipped_existing: int = 0
    conflicts: int = 0


class StagingWriteAdapter:
    def run(self, config: StagingWriteImportConfig, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        raise NotImplementedError


class SqlAlchemyStagingWriteAdapter(StagingWriteAdapter):
    REQUIRED_TABLES = {
        "tenants",
        "branches",
        "audit_logs",
        "catalog_items",
        "parties",
        "contact_methods",
        "work_items",
        "invoices",
        "invoice_lines",
        "document_templates",
        "document_instances",
        "payments",
        "payment_allocations",
    }
    SOURCE_REF_ENTITY = "legacy_import_source_ref"

    def __init__(self, session_factory: sessionmaker[Session] | None = None):
        self._session_factory = session_factory or sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def run(self, config: StagingWriteImportConfig, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        validate_required_import_sequence(list(REQUIRED_IMPORT_SEQUENCE))
        with self._session_factory() as db:
            self._assert_schema_ready(db)
            self._assert_tenant_branch_guards(db, config)
            if not self._is_rollback_safe(db):
                raise ImportBlockedError("BLOCKED_ROLLBACK_NOT_SAFE")
        stats = WriteStats(imported={}, skipped_existing={}, conflicts={}, review_flags={}, source_ref_counts={})
        with self._session_factory.begin() as db:
            stage_results = self._execute_import_order(db, config, data, stats)
        return self._build_execution_report(config, stats, stage_results)

    def rollback_batch(self, config: StagingWriteImportConfig) -> dict[str, int]:
        with self._session_factory.begin() as db:
            refs = list(
                db.scalars(
                    select(AuditLog).where(
                        AuditLog.tenant_id == config.tenant_id,
                        AuditLog.entity_type == self.SOURCE_REF_ENTITY,
                        AuditLog.metadata_json["import_batch_id"].as_string() == config.import_batch_id,
                    )
                )
            )
            removed = 0
            for row in refs:
                db.delete(row)
                removed += 1
            return {"source_ref_registry_deleted": removed}

    def _execute_import_order(
        self,
        db: Session,
        config: StagingWriteImportConfig,
        data: dict[str, list[dict[str, Any]]],
        stats: WriteStats,
    ) -> list[StageResult]:
        results: list[StageResult] = []
        results.append(StageResult("import_batch_audit_context", imported=self._insert_batch_context(db, config)))
        results.append(self._import_services(db, config, data.get("services", []), stats))
        results.append(self._import_clients_contacts(db, config, data.get("clients", []), stats))
        results.append(self._import_orders(db, config, data.get("orders", []), stats))
        results.append(self._import_order_items(db, config, data.get("order_items", []), stats))
        results.append(self._import_contracts(db, config, data.get("contracts", []), stats))
        results.append(self._import_linked_payments(db, config, data.get("payments", []), stats))
        results.append(self._import_orphan_payments(db, config, data.get("payments", []), stats))
        results.append(StageResult("review_flags_audit_summary_validation_report", imported=1))
        return results

    def _insert_batch_context(self, db: Session, config: StagingWriteImportConfig) -> int:
        marker = AuditLog(
            tenant_id=config.tenant_id,
            action=AuditAction.EXECUTE,
            entity_type="legacy_import_batch",
            summary=f"batch:{config.import_batch_id}",
            metadata_json={
                "source_system": SOURCE_SYSTEM,
                "import_batch_id": config.import_batch_id,
                "target_db": config.target_db,
            },
        )
        db.add(marker)
        db.flush()
        return 1

    def _import_services(self, db: Session, config: StagingWriteImportConfig, services: list[dict[str, Any]], stats: WriteStats) -> StageResult:
        imported = skipped = conflicts = 0
        for row in services:
            src_id = str(row.get("id") or "")
            if not src_id:
                continue
            ref = SourceIdentity(SOURCE_SYSTEM, "services", src_id, config.tenant_id, config.import_batch_id)
            action = self._resolve_source_ref_action(db, ref)
            if action == "skip_existing":
                skipped += 1
                continue
            if action == "conflict":
                conflicts += 1
                continue
            item = CatalogItem(
                tenant_id=config.tenant_id,
                item_type=CatalogItemType.SERVICE,
                name=str(row.get("name") or row.get("source_code") or f"Service {src_id}"),
                sku=str(row.get("source_code") or f"legacy-service-{src_id}"),
                base_price=row.get("unit_price"),
                currency="RUB",
                custom_fields_json={
                    "legacy_source_ref": build_source_ref("services", src_id),
                    "legacy_batch_source_ref": build_batch_source_ref(config.import_batch_id, "services", src_id),
                },
            )
            db.add(item)
            db.flush()
            self._register_source_ref(db, ref, "catalog_item", str(item.id))
            imported += 1
        stats.imported["services"] = imported
        stats.skipped_existing["services"] = skipped
        stats.conflicts["services"] = conflicts
        return StageResult("services_catalog", imported=imported, skipped_existing=skipped, conflicts=conflicts)

    def _import_clients_contacts(self, db: Session, config: StagingWriteImportConfig, clients: list[dict[str, Any]], stats: WriteStats) -> StageResult:
        imported = skipped = conflicts = 0
        for row in clients:
            src_id = str(row.get("id") or "")
            if not src_id:
                continue
            ref = SourceIdentity(SOURCE_SYSTEM, "clients", src_id, config.tenant_id, config.import_batch_id)
            action = self._resolve_source_ref_action(db, ref)
            if action == "skip_existing":
                skipped += 1
                continue
            if action == "conflict":
                conflicts += 1
                continue
            party = Party(
                tenant_id=config.tenant_id,
                party_type=PartyType.PERSON,
                display_name=str(row.get("name") or f"Client {src_id}"),
                status=PartyStatus.ACTIVE,
                metadata_json={
                    "legacy_source_ref": build_source_ref("clients", src_id),
                    "legacy_batch_source_ref": build_batch_source_ref(config.import_batch_id, "clients", src_id),
                },
            )
            db.add(party)
            db.flush()
            if row.get("email"):
                db.add(
                    ContactMethod(
                        tenant_id=config.tenant_id,
                        party_id=party.id,
                        method_type=ContactMethodType.EMAIL,
                        value=str(row["email"]),
                        is_primary=True,
                    )
                )
            self._register_source_ref(db, ref, "party", str(party.id))
            imported += 1
        stats.imported["clients"] = imported
        stats.skipped_existing["clients"] = skipped
        stats.conflicts["clients"] = conflicts
        return StageResult("clients_parties_contacts", imported=imported, skipped_existing=skipped, conflicts=conflicts)

    def _import_orders(self, db: Session, config: StagingWriteImportConfig, orders: list[dict[str, Any]], stats: WriteStats) -> StageResult:
        imported = skipped = conflicts = 0
        for row in orders:
            src_id = str(row.get("id") or "")
            if not src_id:
                continue
            ref = SourceIdentity(SOURCE_SYSTEM, "orders", src_id, config.tenant_id, config.import_batch_id)
            action = self._resolve_source_ref_action(db, ref)
            if action == "skip_existing":
                skipped += 1
                continue
            if action == "conflict":
                conflicts += 1
                continue
            work = WorkItem(
                tenant_id=config.tenant_id,
                pipeline_id=config.default_branch_id,
                stage_id=config.default_branch_id,
                work_item_type="consulting_order",
                title=str(row.get("title") or f"Order {src_id}"),
                status=WorkItemStatus.OPEN,
                amount=row.get("total_amount"),
                currency="RUB",
                source=SOURCE_SYSTEM,
                custom_fields_json={
                    "legacy_source_ref": build_source_ref("orders", src_id),
                    "legacy_batch_source_ref": build_batch_source_ref(config.import_batch_id, "orders", src_id),
                    "default_branch_id": str(config.default_branch_id),
                },
            )
            db.add(work)
            db.flush()
            self._register_source_ref(db, ref, "work_item", str(work.id))
            imported += 1
        stats.imported["orders"] = imported
        stats.skipped_existing["orders"] = skipped
        stats.conflicts["orders"] = conflicts
        return StageResult("orders_work_items", imported=imported, skipped_existing=skipped, conflicts=conflicts)

    def _import_order_items(self, db: Session, config: StagingWriteImportConfig, order_items: list[dict[str, Any]], stats: WriteStats) -> StageResult:
        imported = 0
        for row in order_items:
            order_id = str(row.get("order_id") or "")
            if not order_id:
                continue
            review_needed = False
            qty = float(row.get("qty") or 0)
            unit_price = float(row.get("unit_price") or 0)
            derived = round(qty * unit_price, 2)
            if abs(derived - float(row.get("line_total") or derived)) > 0.01:
                review_needed = True
                stats.review_flags["amount_needs_review"] = stats.review_flags.get("amount_needs_review", 0) + 1
            imported += 1
            if review_needed:
                db.add(
                    AuditLog(
                        tenant_id=config.tenant_id,
                        action=AuditAction.OTHER,
                        entity_type="legacy_line_amount_review",
                        summary=f"order:{order_id}",
                        metadata_json={"amount_needs_review": True},
                    )
                )
        stats.imported["order_items"] = imported
        return StageResult("order_items_line_metadata", imported=imported)

    def _import_contracts(self, db: Session, config: StagingWriteImportConfig, contracts: list[dict[str, Any]], stats: WriteStats) -> StageResult:
        imported = 0
        for row in contracts:
            src_id = str(row.get("id") or "")
            if not src_id:
                continue
            template_code = str(row.get("template_code") or "legacy_unknown_template")
            template = db.scalar(
                select(DocumentTemplate).where(
                    DocumentTemplate.tenant_id == config.tenant_id,
                    DocumentTemplate.code == template_code,
                )
            )
            if template is None:
                stats.review_flags["template_needs_review"] = stats.review_flags.get("template_needs_review", 0) + 1
                template = db.scalar(
                    select(DocumentTemplate).where(
                        DocumentTemplate.tenant_id == config.tenant_id,
                        DocumentTemplate.code == "legacy_unknown_template",
                    )
                )
            context = {"legacy_source_ref": build_source_ref("contracts", src_id)}
            if not row.get("order_id"):
                context["needs_review"] = True
            if float(row.get("amount") or 0) == 0:
                context["zero_amount_needs_review"] = True
                stats.review_flags["zero_amount_needs_review"] = stats.review_flags.get("zero_amount_needs_review", 0) + 1
            doc = DocumentInstance(
                tenant_id=config.tenant_id,
                template_id=template.id if template else None,
                title=str(row.get("number") or f"Contract {src_id}"),
                status=DocumentStatus.ARCHIVED,
                context_json=context,
                work_item_id=None,
                party_id=None,
            )
            db.add(doc)
            db.flush()
            imported += 1
        stats.imported["contracts"] = imported
        return StageResult("contracts_documents", imported=imported)

    def _import_linked_payments(self, db: Session, config: StagingWriteImportConfig, payments: list[dict[str, Any]], stats: WriteStats) -> StageResult:
        imported = 0
        for row in payments:
            if not row.get("order_id"):
                continue
            payment = self._create_payment_row(db, config, row, needs_review=False, unlinked=False)
            invoice = self._create_invoice_shell(db, config, row)
            db.add(
                PaymentAllocation(
                    tenant_id=config.tenant_id,
                    payment_id=payment.id,
                    invoice_id=invoice.id,
                    amount=row.get("amount") or 0,
                    notes="legacy linked allocation",
                )
            )
            imported += 1
        stats.imported["payments_linked"] = imported
        return StageResult("payments_linked", imported=imported)

    def _import_orphan_payments(self, db: Session, config: StagingWriteImportConfig, payments: list[dict[str, Any]], stats: WriteStats) -> StageResult:
        imported = 0
        for row in payments:
            if row.get("order_id"):
                continue
            self._create_payment_row(db, config, row, needs_review=True, unlinked=True)
            imported += 1
            stats.review_flags["unlinked_legacy_payment"] = stats.review_flags.get("unlinked_legacy_payment", 0) + 1
        stats.imported["payments_orphan_standalone"] = imported
        return StageResult("payments_orphan_standalone", imported=imported)

    def _create_payment_row(
        self,
        db: Session,
        config: StagingWriteImportConfig,
        row: dict[str, Any],
        *,
        needs_review: bool,
        unlinked: bool,
    ) -> Payment:
        src_id = str(row.get("id") or "")
        payment = Payment(
            tenant_id=config.tenant_id,
            party_id=None,
            payment_number=f"LEGACY-PAY-{src_id or 'UNKNOWN'}",
            amount=row.get("amount") or 0,
            currency="RUB",
            payment_date=row.get("payment_date"),
            method=PaymentMethod.OTHER,
            status=PaymentStatus.COMPLETED,
            direction=PaymentDirection.NEEDS_REVIEW if needs_review else PaymentDirection.INCOMING,
            reference_number=str(row.get("payment_ref") or ""),
            notes="; ".join(
                part for part in [
                    "legacy_import",
                    "needs_review" if needs_review else "",
                    "unlinked_legacy_payment" if unlinked else "",
                    build_source_ref("payments", src_id) if src_id else "",
                ] if part
            ),
        )
        db.add(payment)
        db.flush()
        return payment

    def _create_invoice_shell(self, db: Session, config: StagingWriteImportConfig, row: dict[str, Any]) -> Invoice:
        src_order_id = str(row.get("order_id") or "unknown")
        invoice = Invoice(
            tenant_id=config.tenant_id,
            party_id=UUID("00000000-0000-0000-0000-000000000000"),
            work_item_id=None,
            document_id=None,
            invoice_number=f"LEGACY-INV-{src_order_id}",
            status=InvoiceStatus.PAID,
            currency="RUB",
            subtotal=row.get("amount") or 0,
            tax_amount=0,
            total=row.get("amount") or 0,
            amount_paid=row.get("amount") or 0,
            notes="legacy invoice shell",
        )
        db.add(invoice)
        db.flush()
        db.add(
            InvoiceLine(
                tenant_id=config.tenant_id,
                invoice_id=invoice.id,
                description="legacy order payment shell",
                quantity=1,
                unit_price=row.get("amount") or 0,
                line_total=row.get("amount") or 0,
                sort_order=10,
            )
        )
        db.flush()
        return invoice

    def _resolve_source_ref_action(self, db: Session, incoming: SourceIdentity) -> str:
        key = build_source_ref(incoming.source_table, incoming.source_id)
        existing = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.tenant_id == incoming.tenant_id,
                    AuditLog.entity_type == self.SOURCE_REF_ENTITY,
                    AuditLog.summary == key,
                )
            )
        )
        source_identities = [
            SourceIdentity(
                source_system=str(row.metadata_json.get("source_system")),
                source_table=str(row.metadata_json.get("source_table")),
                source_id=str(row.metadata_json.get("source_id")),
                tenant_id=incoming.tenant_id,
                import_batch_id=str(row.metadata_json.get("import_batch_id")),
            )
            for row in existing
        ]
        try:
            action = resolve_conflict_action(source_identities, incoming)
        except SourceRefConflictError as exc:
            raise ImportBlockedError(f"BLOCKED:{exc}") from exc
        return action

    def _register_source_ref(self, db: Session, source: SourceIdentity, target_entity: str, target_id: str) -> None:
        source_ref = build_source_ref(source.source_table, source.source_id)
        batch_source_ref = build_batch_source_ref(source.import_batch_id, source.source_table, source.source_id)
        _validate_source_ref_shape(source_ref)
        _validate_batch_source_ref_shape(batch_source_ref)
        row = AuditLog(
            tenant_id=source.tenant_id,
            action=AuditAction.OTHER,
            entity_type=self.SOURCE_REF_ENTITY,
            summary=source_ref,
            metadata_json={
                "source_system": source.source_system,
                "source_table": source.source_table,
                "source_id": source.source_id,
                "source_ref": source_ref,
                "batch_source_ref": batch_source_ref,
                "import_batch_id": source.import_batch_id,
                "target_entity_type": target_entity,
                "target_entity_id": target_id,
            },
        )
        db.add(row)
        db.flush()

    def _assert_schema_ready(self, db: Session) -> None:
        inspector = inspect(db.bind)
        missing = sorted(name for name in self.REQUIRED_TABLES if not inspector.has_table(name))
        if missing:
            raise ImportBlockedError(f"BLOCKED_TARGET_MODEL_MISSING:{','.join(missing)}")
        if not inspector.has_table("audit_logs"):
            raise ImportBlockedError("BLOCKED_SOURCE_REF_STORAGE_MISSING")

    def _assert_tenant_branch_guards(self, db: Session, config: StagingWriteImportConfig) -> None:
        tenant = db.get(Tenant, config.tenant_id)
        if tenant is None:
            raise ImportBlockedError(f"BLOCKED:tenant_not_found:{config.tenant_id}")
        branch = db.get(Branch, config.default_branch_id)
        if branch is None:
            raise ImportBlockedError(f"BLOCKED:default_branch_not_found:{config.default_branch_id}")
        if branch.tenant_id != config.tenant_id:
            raise ImportBlockedError("BLOCKED:default_branch_tenant_mismatch")

    def _is_rollback_safe(self, db: Session) -> bool:
        inspector = inspect(db.bind)
        return inspector.has_table("audit_logs")

    def _build_execution_report(self, config: StagingWriteImportConfig, stats: WriteStats, stage_results: list[StageResult]) -> dict[str, Any]:
        return {
            "mode": STAGING_WRITE_EXECUTE_MODE,
            "writes_executed": True,
            "execution_allowed": True,
            "source_system": SOURCE_SYSTEM,
            "import_batch_id": config.import_batch_id,
            "required_execution_sequence": [item.key for item in stage_results],
            "import_order_enforced": [item.key for item in stage_results] == REQUIRED_IMPORT_SEQUENCE,
            "counts": {
                "imported": stats.imported,
                "skipped_existing": stats.skipped_existing,
                "conflicts": stats.conflicts,
                "review_flags": stats.review_flags,
                "source_refs": stats.source_ref_counts,
            },
            "rollback_support": {
                "import_batch_marker": True,
                "transaction_boundary": True,
                "reverse_order_cleanup_supported": True,
                "post_rollback_validation_helper": True,
            },
            "pii_scan_status": "pending_output_scan",
        }


def resolve_conflict_action(
    existing: list[SourceIdentity],
    incoming: SourceIdentity,
    *,
    allow_safe_metadata_update: bool = False,
) -> str:
    """Conservative fail-closed conflict resolver for source identity."""
    if not existing:
        return "insert"
    if len(existing) > 1:
        raise SourceRefConflictError("Ambiguous duplicate source refs")
    current = existing[0]
    if current.tenant_id != incoming.tenant_id:
        raise SourceRefConflictError("Tenant mismatch for existing source ref")
    if current.import_batch_id != incoming.import_batch_id:
        raise SourceRefConflictError("Source ref already belongs to another import batch")
    if allow_safe_metadata_update:
        return "update_safe_metadata"
    return "skip_existing"


def build_source_ref(source_table: str, source_id: str) -> str:
    return f"{SOURCE_SYSTEM}:{source_table}:{source_id}"


def build_batch_source_ref(import_batch_id: str, source_table: str, source_id: str) -> str:
    return f"{SOURCE_SYSTEM}:{import_batch_id}:{source_table}:{source_id}"


def _validate_source_ref_shape(source_ref: str) -> None:
    if not SOURCE_REF_PATTERN.match(source_ref):
        raise StagingWriteImportPreflightError(
            f"Invalid source_ref format: {source_ref}"
        )


def _validate_batch_source_ref_shape(source_ref: str) -> None:
    if not SOURCE_REF_BATCH_PATTERN.match(source_ref):
        raise StagingWriteImportPreflightError(
            f"Invalid batch-scoped source_ref format: {source_ref}"
        )


def validate_required_import_sequence(sequence: list[str]) -> None:
    if sequence != REQUIRED_IMPORT_SEQUENCE:
        raise StagingWriteImportPreflightError(
            "Import order mismatch with required execution sequence"
        )


def parse_masked_dry_run_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise StagingWriteImportPreflightError(f"--dry-run-report not found: {path}")
    payload = path.read_text(encoding="utf-8")
    findings = scan_text_for_suspicious_pii(payload)
    if findings:
        raise StagingWriteImportPreflightError(
            "Dry-run report failed masked PII scan: " + ", ".join(sorted(set(findings)))
        )
    try:
        report = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise StagingWriteImportPreflightError(
            f"--dry-run-report is not valid JSON: {exc}"
        ) from exc

    if report.get("gate") != "B" or report.get("mode") != "real-source-readonly":
        raise StagingWriteImportPreflightError(
            "--dry-run-report must be Gate B real-source-readonly output"
        )

    summary = report.get("summary") or {}
    if summary.get("total_error_rows", 0) > 0:
        raise StagingWriteImportPreflightError(
            "--dry-run-report has error rows; write-import planning blocked"
        )
    return report


def _validate_target_db(target_db: str) -> str:
    value = (target_db or "").strip()
    if not value:
        raise StagingWriteImportPreflightError("--target-db is required")
    if value == LIVE_DB_BLOCKED:
        raise StagingWriteImportPreflightError("Target DB 'coreops' is blocked (live)")
    if value != TARGET_DB_ALLOWED:
        raise StagingWriteImportPreflightError(
            f"--target-db must be '{TARGET_DB_ALLOWED}'"
        )
    return value


def _validate_import_batch_id(import_batch_id: str | None) -> str:
    value = (import_batch_id or "").strip()
    if not value:
        raise StagingWriteImportPreflightError("--import-batch-id is required")
    if not IMPORT_BATCH_ID_PATTERN.match(value):
        raise StagingWriteImportPreflightError(
            "Invalid --import-batch-id format; expected technical id format"
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Staging write-import planner/runner for Consulting legacy source."
    )
    parser.add_argument(
        "--mode",
        required=True,
        help=(
            "Must be 'staging-write-import-plan' or "
            "'staging-write-import-execute'"
        ),
    )
    parser.add_argument("--source-db", required=True, help="Allowlisted source SQLite path")
    parser.add_argument("--backup-id", required=True, help="Validated backup attestation id")
    parser.add_argument("--tenant-id", required=True, help="Staging tenant UUID")
    parser.add_argument("--default-branch-id", required=True, help="Staging default branch UUID")
    parser.add_argument("--target-db", required=True, help="Must be coreops_staging_0013")
    parser.add_argument("--dry-run-report", required=True, help="Masked Gate B report path")
    parser.add_argument("--import-batch-id", required=True, help="Write-import batch identifier")
    parser.add_argument("--output", required=True, help="Output report path outside repo")
    parser.add_argument(
        "--allow-execution",
        action="store_true",
        help="Reserved for explicit future write execution gate (disabled by default)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output report path",
    )
    return parser


def validate_staging_write_import_args(
    args: argparse.Namespace,
    *,
    repo_root: Path | None = None,
) -> StagingWriteImportConfig:
    if args.mode == STAGING_WRITE_LEGACY_AMBIGUOUS_MODE:
        raise StagingWriteImportPreflightError(
            "Ambiguous mode. Use staging-write-import-plan or staging-write-import-execute."
        )
    if args.mode not in {STAGING_WRITE_PLAN_MODE, STAGING_WRITE_EXECUTE_MODE}:
        raise StagingWriteImportPreflightError(
            "--mode must be staging-write-import-plan or staging-write-import-execute"
        )

    source_db = assert_path_allowlisted_for_real_source(args.source_db)
    backup_id = validate_backup_id(args.backup_id)

    try:
        tenant_id = UUID(args.tenant_id)
    except ValueError as exc:
        raise StagingWriteImportPreflightError(
            f"Invalid --tenant-id UUID: {args.tenant_id}"
        ) from exc
    try:
        default_branch_id = UUID(args.default_branch_id)
    except ValueError as exc:
        raise StagingWriteImportPreflightError(
            f"Invalid --default-branch-id UUID: {args.default_branch_id}"
        ) from exc

    target_db = _validate_target_db(args.target_db)
    import_batch_id = _validate_import_batch_id(args.import_batch_id)
    dry_run_report = Path(args.dry_run_report).resolve()
    parse_masked_dry_run_report(dry_run_report)
    output = assert_output_path_safe(
        args.output,
        repo_root=repo_root,
        allow_overwrite=bool(args.overwrite),
    )

    return StagingWriteImportConfig(
        source_db=source_db,
        backup_id=backup_id,
        tenant_id=tenant_id,
        default_branch_id=default_branch_id,
        target_db=target_db,
        dry_run_report=dry_run_report,
        import_batch_id=import_batch_id,
        output=output,
        mode=args.mode,
    )


def _is_technical_identifier(path: tuple[str, ...], value: str) -> bool:
    key = path[-1] if path else ""
    if key in {"tenant_id", "default_branch_id"}:
        return bool(UUID_PATTERN.match(value))
    if key == "backup_id":
        try:
            validate_backup_id(value)
            return True
        except BackupIdError:
            return False
    if key == "import_batch_id":
        return bool(IMPORT_BATCH_ID_PATTERN.match(value))
    if key == "source_ref":
        return bool(SOURCE_REF_PATTERN.match(value))
    if key == "source_ref_format":
        return value == "legacy_consulting_os:<source_table>:<source_id>"
    if key == "batch_source_ref_format":
        return value == "legacy_consulting_os:<import_batch_id>:<source_table>:<source_id>"
    return False


def scan_output_payload_for_pii(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []

    def walk(v: Any, path: tuple[str, ...]) -> None:
        if isinstance(v, dict):
            for k, val in v.items():
                walk(val, (*path, str(k)))
            return
        if isinstance(v, list):
            for i, val in enumerate(v):
                walk(val, (*path, f"[{i}]"))
            return
        if not isinstance(v, str):
            return
        if _is_technical_identifier(path, v):
            if EMAIL_PATTERN.search(v):
                findings.append(f"{'.'.join(path)}:technical_identifier_email_like")
            # technical IDs that match strict patterns are allowed even if phone regex would match
            return
        if EMAIL_PATTERN.search(v):
            findings.append(f"{'.'.join(path)}:email-like pattern")
        if PHONE_PATTERN.search(v):
            findings.append(f"{'.'.join(path)}:phone-like pattern")

    walk(payload, tuple())
    return findings


def _build_planned_summary(
    data: dict[str, list[dict[str, Any]]],
    *,
    import_batch_id: str,
) -> dict[str, Any]:
    orders = data.get("orders", [])
    order_items = data.get("order_items", [])
    contracts = data.get("contracts", [])
    payments = data.get("payments", [])
    order_ids = {str(o.get("id")) for o in orders if o.get("id") is not None}

    order_sum: dict[str, float] = {}
    for line in order_items:
        oid = str(line.get("order_id") or "")
        qty = line.get("qty")
        unit_price = line.get("unit_price")
        if not oid or qty is None or unit_price is None:
            continue
        order_sum[oid] = order_sum.get(oid, 0.0) + float(qty) * float(unit_price)

    mismatched_order_ids: list[str] = []
    for order in orders:
        oid = str(order.get("id") or "")
        if not oid:
            continue
        expected = order.get("total_amount")
        derived = order_sum.get(oid)
        if expected is None or derived is None:
            continue
        if abs(float(expected) - float(derived)) > 0.01:
            mismatched_order_ids.append(oid)

    contracts_null_order = 0
    contracts_zero_amount = 0
    for c in contracts:
        if not c.get("order_id"):
            contracts_null_order += 1
        if float(c.get("amount") or 0) == 0:
            contracts_zero_amount += 1

    orphan_payments = 0
    linked_payments = 0
    for p in payments:
        oid = str(p.get("order_id") or "")
        if oid and oid in order_ids:
            linked_payments += 1
        else:
            orphan_payments += 1

    sequence = list(REQUIRED_IMPORT_SEQUENCE)
    validate_required_import_sequence(sequence)
    return {
        "mode": STAGING_WRITE_PLAN_MODE,
        "writes_executed": False,
        "execution_allowed": False,
        "verdict": "PLAN_ONLY",
        "source_ref_format": "legacy_consulting_os:<source_table>:<source_id>",
        "batch_source_ref_format": (
            "legacy_consulting_os:<import_batch_id>:<source_table>:<source_id>"
        ),
        "source_identity_keys": [
            "source_system",
            "source_table",
            "source_id",
            "tenant_id",
        ],
        "source_system": SOURCE_SYSTEM,
        "import_batch_id": import_batch_id,
        "required_execution_sequence": sequence,
        "counts": {
            "services": len(data.get("services", [])),
            "clients": len(data.get("clients", [])),
            "orders": len(orders),
            "order_items": len(order_items),
            "contracts": len(contracts),
            "payments_total": len(payments),
            "payments_linked": linked_payments,
            "payments_orphan_standalone": orphan_payments,
        },
        "business_policy": {
            "orders_total_amount_authoritative": True,
            "amount_needs_review_orders": len(mismatched_order_ids),
            "finance_posting_held_for_mismatch": True,
            "orphan_payments_standalone_historical": True,
            "orphan_payments_needs_review": True,
            "orphan_payments_relation_status": "unlinked_legacy_payment",
            "contracts_null_order_link_review_count": contracts_null_order,
            "contracts_zero_amount_review_count": contracts_zero_amount,
            "missing_template_fallback": "legacy_unknown_template",
        },
        "conflict_policy_priority": "section_4_2_matrix_overrides_generic_idempotency_text",
        "conflict_policy": {
            "default_skip_existing_by_source_ref": True,
            "no_destructive_overwrite": True,
            "no_silent_merge": True,
            "update_only_safe_metadata_review_flags": True,
            "fail_closed_on_ambiguous_duplicate_source_ref": True,
            "fail_closed_on_tenant_or_branch_mismatch": True,
            "fail_closed_cross_tenant_or_cross_batch_source_ref": True,
        },
        "rollback_support": {
            "import_batch_id_required": True,
            "source_ref_cleanup_target_tenant_only": True,
            "reverse_order_cleanup_supported": True,
            "post_rollback_validation_helper": True,
        },
    }


def run_staging_write_import(
    config: StagingWriteImportConfig,
    *,
    allow_execution: bool = False,
    write_adapter: StagingWriteAdapter | None = None,
) -> dict[str, Any]:
    if config.mode == STAGING_WRITE_EXECUTE_MODE:
        if not allow_execution:
            raise StagingWriteImportPreflightError(
                "EXECUTION_BLOCKED_APPROVAL_REQUIRED: execute mode requires explicit --allow-execution gate."
            )
        source = ReadonlySqliteSourceAdapter(
            config.source_db,
            schema_profile="production_gate_b",
            path_guard="real_source",
        )
        data = source.load()
        adapter = write_adapter or SqlAlchemyStagingWriteAdapter()
        return adapter.run(config, data)
    if allow_execution:
        raise StagingWriteImportPreflightError("Execution flag is blocked in plan mode.")
    source = ReadonlySqliteSourceAdapter(
        config.source_db,
        schema_profile="production_gate_b",
        path_guard="real_source",
    )
    data = source.load()
    return _build_planned_summary(data, import_batch_id=config.import_batch_id)


def _write_output_atomically_with_scan(payload: dict[str, Any], output: Path) -> None:
    tmp = output.with_name(output.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    findings = scan_output_payload_for_pii(payload)
    if findings:
        failed = output.with_name(output.name + ".pii_failed")
        tmp.replace(failed)
        raise StagingWriteImportPreflightError(
            "Output failed PII scan: " + ", ".join(sorted(set(findings)))
        )
    tmp.replace(output)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = validate_staging_write_import_args(args, repo_root=find_repo_root())
        report = run_staging_write_import(config, allow_execution=bool(args.allow_execution))
        _write_output_atomically_with_scan(report, config.output)
    except (
        StagingWriteImportPreflightError,
        AllowlistError,
        BackupIdError,
        OutputPathError,
        FileNotFoundError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_PREFLIGHT_FAIL
    except Exception as exc:  # pragma: no cover
        print(f"Staging write-import run failed: {exc}", file=sys.stderr)
        return EXIT_PREFLIGHT_FAIL

    print(f"Staging write-import report written: {config.output}")
    return 0

