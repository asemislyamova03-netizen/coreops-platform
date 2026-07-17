from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import ValidationError

from app.modules.audit.schemas import ImportBatchEntitySummary
from app.modules.catalog.schemas import CatalogItemCreate
from app.modules.documents.schemas import (
    DocumentImportCreate,
    LegacyContractImportInput,
    assess_legacy_contract_import,
)
from app.modules.finance.schemas import PaymentCreate, map_legacy_payment_type
from app.modules.imports_dry_run.schemas import (
    DryRunIssue,
    DryRunValidationReport,
    FinanceAggregateCheck,
    IssueSeverity,
    SyntheticDryRunContext,
    SyntheticDryRunResult,
    TenantBranchReadiness,
    build_batch_summary,
)
from app.modules.parties.schemas import PartyCreate
from app.modules.tenants.schemas import TenantCreate, TenantResponse
from app.modules.workflows.schemas import WorkItemCreate
from app.modules.workflows.service import map_legacy_order_status, map_legacy_stage_status


@dataclass
class TargetEndpointCheck:
    endpoint: str
    schema_name: str
    status: str  # ready / partial / missing
    note: str


class SyntheticSourceAdapter:
    def __init__(self, fixture: dict[str, list[dict]]):
        self.fixture = fixture

    def load(self) -> dict[str, list[dict]]:
        return self.fixture


class DryRunNoOpTargetAdapter:
    """
    No-op target adapter for C2a:
    - validates payloads against Core REST DTOs
    - does NOT call API
    - does NOT write DB
    """

    def __init__(self) -> None:
        self.endpoint_checks: list[TargetEndpointCheck] = []
        self.payload_counts: dict[str, int] = {}

    def validate_parties(self, payloads: list[dict]) -> None:
        self._validate_payloads("/api/v1/parties", PartyCreate, payloads, "ready")

    def validate_catalog_items(self, payloads: list[dict]) -> None:
        self._validate_payloads("/api/v1/catalog/items", CatalogItemCreate, payloads, "ready")

    def validate_work_items(self, payloads: list[dict]) -> None:
        self._validate_payloads("/api/v1/work-items", WorkItemCreate, payloads, "ready")

    def validate_documents(self, payloads: list[dict]) -> None:
        self._validate_payloads(
            "/api/v1/documents/import",
            DocumentImportCreate,
            payloads,
            "ready",
        )

    def validate_payments(self, payloads: list[dict]) -> None:
        self._validate_payloads(
            "/api/v1/finance/payments",
            PaymentCreate,
            payloads,
            "ready",
        )

    def validate_tenant_readiness(self, *, tenant_create_payload: dict, tenant_response_shape: dict) -> None:
        """Validate tenant bootstrap payloads against known Core REST schemas (no-op)."""
        TenantCreate.model_validate(tenant_create_payload)
        TenantResponse.model_validate(tenant_response_shape)
        self.payload_counts["/api/v1/tenants"] = 1
        self.endpoint_checks.append(
            TargetEndpointCheck(
                endpoint="/api/v1/tenants",
                schema_name="TenantCreate+TenantResponse",
                status="ready",
                note="Tenant create/response schemas validated; default_branch is provisioned by Core on create",
            )
        )

    def _validate_payloads(self, endpoint: str, schema, payloads: list[dict], status: str) -> None:
        ok = 0
        for payload in payloads:
            schema.model_validate(payload)
            ok += 1
        self.payload_counts[endpoint] = ok
        note = "DTO payloads validated in no-op mode"
        if status == "partial":
            note = "Partial Core API fit; see C1c readiness"
        self.endpoint_checks.append(
            TargetEndpointCheck(
                endpoint=endpoint,
                schema_name=schema.__name__,
                status=status,
                note=note,
            )
        )


class SyntheticDryRunPipeline:
    def __init__(self, *, source, target: DryRunNoOpTargetAdapter):
        self.source = source
        self.target = target

    def run(self, context: SyntheticDryRunContext) -> SyntheticDryRunResult:
        data = self.source.load()
        issues: list[DryRunIssue] = []

        tenant_ready = context.tenant_id is not None
        default_branch_ready = context.default_branch_id is not None
        if not tenant_ready:
            issues.append(
                self._issue(
                    "tenant",
                    "missing_tenant_id",
                    "error",
                    "context",
                    "tenant_id required before import dry-run",
                )
            )
        if not default_branch_ready:
            issues.append(
                self._issue(
                    "tenant",
                    "missing_default_branch_id",
                    "error",
                    "context",
                    "default_branch_id required before import dry-run",
                )
            )
        tenant_branch_readiness = TenantBranchReadiness(
            tenant_ready=tenant_ready,
            default_branch_ready=default_branch_ready,
            tenant_id=context.tenant_id,
            default_branch_id=context.default_branch_id,
            passed=tenant_ready and default_branch_ready,
        )

        users = data.get("users", [])
        clients = data.get("clients", [])
        services = data.get("services", [])
        orders = data.get("orders", [])
        order_stages = data.get("order_stages", [])
        order_items = data.get("order_items", [])
        contracts = data.get("contracts", [])
        payments = data.get("payments", [])

        user_login_seen: set[str] = set()
        duplicate_warnings = 0
        for u in users:
            login = str(u.get("login") or "").strip().lower()
            if not login:
                issues.append(self._issue("users", "required_login", "error", u.get("id", "unknown"), "Missing login"))
            elif login in user_login_seen:
                duplicate_warnings += 1
                issues.append(
                    self._issue("users", "duplicate_login", "warning", u.get("id", "unknown"), "Duplicate synthetic login")
                )
            else:
                user_login_seen.add(login)

        client_ids = {row["id"] for row in clients if row.get("id")}
        service_ids = {row["id"] for row in services if row.get("id")}
        order_ids = {row["id"] for row in orders if row.get("id")}

        unknown_status_warnings = 0
        required_field_errors = 0
        orphan_warnings = 0

        party_payloads: list[dict] = []
        for c in clients:
            display_name = str(c.get("display_name") or "").strip()
            if not display_name:
                required_field_errors += 1
                issues.append(self._issue("clients", "required_display_name", "error", c.get("id", "unknown"), "Missing display_name"))
                continue
            email = c.get("email")
            contacts = []
            if email:
                contacts.append({"method_type": "email", "value": email, "is_primary": True})
            party_payloads.append(
                {
                    "party_type": "person" if str(c.get("party_type", "")).upper() == "PERSON" else "organization",
                    "display_name": display_name,
                    "status": "active" if str(c.get("status", "")).lower() in ("active", "new") else "inactive",
                    "contact_methods": contacts,
                    "metadata_json": {"synthetic_source_id": c.get("id")},
                }
            )

        catalog_payloads = [
            {
                "item_type": "service",
                "name": s.get("name", "Legacy service"),
                "sku": f"legacy-{s.get('id')}",
                "is_active": True,
            }
            for s in services
        ]

        work_item_payloads: list[dict] = []
        for o in orders:
            status, needs_review = map_legacy_order_status(o.get("status"))
            if needs_review:
                unknown_status_warnings += 1
                issues.append(
                    self._issue(
                        "orders",
                        "unknown_status",
                        "warning",
                        o.get("id", "unknown"),
                        f"Unknown order status {o.get('status')}",
                    )
                )
            if o.get("client_id") not in client_ids:
                orphan_warnings += 1
                issues.append(
                    self._issue(
                        "orders",
                        "orphan_client",
                        "warning",
                        o.get("id", "unknown"),
                        "Order references missing client",
                    )
                )
            work_item_payloads.append(
                {
                    "pipeline_id": uuid.uuid4(),
                    "stage_id": uuid.uuid4(),
                    "work_item_type": "order_case",
                    "title": f"Synthetic order {o.get('number')}",
                    "status": status.value,
                    "custom_fields": {
                        "legacy_order_id": o.get("id"),
                        "status_needs_review": needs_review,
                    },
                }
            )

        for st in order_stages:
            _, needs_review = map_legacy_stage_status(st.get("status"))
            if needs_review:
                unknown_status_warnings += 1
                issues.append(
                    self._issue(
                        "order_stages",
                        "unknown_stage_status",
                        "warning",
                        st.get("id", "unknown"),
                        f"Unknown stage status {st.get('status')}",
                    )
                )
            if st.get("template_id") is None:
                issues.append(
                    self._issue(
                        "order_stages",
                        "missing_template_id",
                        "warning",
                        st.get("id", "unknown"),
                        "template_id missing, fallback template required",
                    )
                )
            if st.get("order_id") not in order_ids:
                orphan_warnings += 1
                issues.append(
                    self._issue(
                        "order_stages",
                        "orphan_order",
                        "warning",
                        st.get("id", "unknown"),
                        "Stage references missing order",
                    )
                )

        for line in order_items:
            if line.get("order_id") not in order_ids:
                orphan_warnings += 1
                issues.append(
                    self._issue("order_items", "orphan_order", "warning", line.get("id", "unknown"), "Line references missing order")
                )
            if line.get("service_id") not in service_ids:
                orphan_warnings += 1
                issues.append(
                    self._issue("order_items", "orphan_service", "warning", line.get("id", "unknown"), "Line references missing service")
                )

        document_payloads: list[dict] = []
        for c in contracts:
            assessment = assess_legacy_contract_import(
                LegacyContractImportInput(
                    legacy_status=c.get("status"),
                    work_item_id=uuid.uuid4() if c.get("order_id") else None,
                    amount=Decimal(str(c.get("amount") or "0")),
                )
            )
            if assessment.status_needs_review:
                unknown_status_warnings += 1
            if assessment.link_needs_review:
                issues.append(
                    self._issue(
                        "contracts",
                        "null_order_link",
                        "warning",
                        c.get("id", "unknown"),
                        "contracts.order_id is NULL; review required",
                    )
                )
            if assessment.amount_needs_review:
                issues.append(
                    self._issue(
                        "contracts",
                        "zero_amount",
                        "warning",
                        c.get("id", "unknown"),
                        "contracts.amount is 0; policy review required",
                    )
                )
            document_payloads.append(
                {
                    "title": f"Synthetic contract {c.get('number')}",
                    "legacy_status": c.get("status"),
                    "amount": Decimal(str(c.get("amount") or "0")),
                    "work_item_id": uuid.uuid4() if c.get("order_id") else None,
                    "external_ref": f"legacy_contract:{c.get('id')}",
                    "source_system": "consult_app_synthetic",
                    "branch_id": context.default_branch_id,
                    "extra_context": {
                        "legacy_contract_number": str(c.get("number") or ""),
                    },
                }
            )

        payment_payloads: list[dict] = []
        source_payments_total = Decimal("0")
        mapped_payments_total = Decimal("0")
        for p in payments:
            amount = Decimal(str(p.get("amount") or "0"))
            source_payments_total += amount
            direction, mapped_status, needs_review = map_legacy_payment_type(p.get("type"))
            if needs_review:
                unknown_status_warnings += 1
                issues.append(
                    self._issue(
                        "payments",
                        "unknown_payment_type",
                        "warning",
                        p.get("id", "unknown"),
                        f"Unknown payment type {p.get('type')}",
                    )
                )
            if p.get("order_id") not in order_ids:
                orphan_warnings += 1
                issues.append(
                    self._issue(
                        "payments",
                        "orphan_order",
                        "warning",
                        p.get("id", "unknown"),
                        "Payment references missing order",
                    )
                )
            payment_payloads.append(
                {
                    "amount": amount,
                    "currency": "RUB",
                    "payment_date": "2026-01-01",
                    "status": mapped_status.value,
                    "direction": direction.value,
                    "legacy_payment_type": p.get("type"),
                }
            )
            mapped_payments_total += amount

        finance_check = FinanceAggregateCheck(
            source_payments_total=source_payments_total,
            mapped_payments_total=mapped_payments_total,
            difference=source_payments_total - mapped_payments_total,
            passed=(source_payments_total == mapped_payments_total),
        )
        if not finance_check.passed:
            issues.append(
                self._issue("payments", "finance_aggregate_mismatch", "error", "aggregate", "Payment aggregates mismatch")
            )

        # Validate against REST DTO schemas (no-op target). No API calls, no DB writes.
        validation_errors = 0
        try:
            now = datetime.now(UTC)
            self.target.validate_tenant_readiness(
                tenant_create_payload={
                    "name": "Synthetic Consulting Tenant",
                    "slug": "synthetic-consulting-tenant",
                    "status": "trial",
                },
                tenant_response_shape={
                    "id": context.tenant_id,
                    "provider_company_id": uuid.uuid4(),
                    "name": "Synthetic Consulting Tenant",
                    "slug": "synthetic-consulting-tenant",
                    "industry_template_id": None,
                    "default_branch_id": context.default_branch_id,
                    "status": "trial",
                    "created_at": now,
                    "updated_at": now,
                },
            )
        except ValidationError as exc:
            validation_errors += 1
            issues.append(
                self._issue(
                    "target_payload",
                    "dto_validation_error",
                    "error",
                    "tenant_schema",
                    str(exc),
                )
            )

        for fn, payloads in (
            (self.target.validate_parties, party_payloads),
            (self.target.validate_catalog_items, catalog_payloads),
            (self.target.validate_work_items, work_item_payloads),
            (self.target.validate_documents, document_payloads),
            (self.target.validate_payments, payment_payloads),
        ):
            try:
                fn(payloads)
            except ValidationError as exc:
                validation_errors += 1
                issues.append(self._issue("target_payload", "dto_validation_error", "error", "schema", str(exc)))

        tenant_errors = 0 if tenant_branch_readiness.passed else 1
        entity_summaries = [
            ImportBatchEntitySummary(
                entity="tenant_default_branch",
                source_count=1,
                imported_count=1 if tenant_branch_readiness.passed else 0,
                skipped_count=0 if tenant_branch_readiness.passed else 1,
                error_count=tenant_errors,
                review_count=0,
            ),
            ImportBatchEntitySummary(
                entity="users",
                source_count=len(users),
                imported_count=len(users) - validation_errors,
                skipped_count=0,
                error_count=required_field_errors,
                review_count=duplicate_warnings,
            ),
            ImportBatchEntitySummary(
                entity="parties",
                source_count=len(clients),
                imported_count=len(party_payloads),
                skipped_count=max(0, len(clients) - len(party_payloads)),
                error_count=required_field_errors,
                review_count=0,
            ),
            ImportBatchEntitySummary(
                entity="catalog_services",
                source_count=len(services),
                imported_count=len(catalog_payloads),
                skipped_count=0,
                error_count=0,
                review_count=0,
            ),
            ImportBatchEntitySummary(
                entity="work_items",
                source_count=len(orders),
                imported_count=len(work_item_payloads),
                skipped_count=0,
                error_count=0,
                review_count=unknown_status_warnings,
            ),
            ImportBatchEntitySummary(
                entity="documents_contracts",
                source_count=len(contracts),
                imported_count=len(document_payloads),
                skipped_count=0,
                error_count=0,
                review_count=sum(1 for i in issues if i.entity == "contracts"),
            ),
            ImportBatchEntitySummary(
                entity="finance_payments",
                source_count=len(payments),
                imported_count=len(payment_payloads),
                skipped_count=0,
                error_count=0 if finance_check.passed else 1,
                review_count=sum(1 for i in issues if i.entity == "payments"),
            ),
        ]

        report = DryRunValidationReport(
            issues=issues,
            duplicate_warnings=duplicate_warnings,
            orphan_warnings=orphan_warnings,
            unknown_status_warnings=unknown_status_warnings,
            required_field_errors=required_field_errors,
            finance_check=finance_check,
            tenant_branch_readiness=tenant_branch_readiness,
        )
        summary = build_batch_summary(
            context=context,
            entities=entity_summaries,
            status_mapping_warnings=unknown_status_warnings,
            review_count=report.duplicate_warnings + report.orphan_warnings + report.unknown_status_warnings,
            error_count=(
                report.required_field_errors
                + tenant_errors
                + (0 if finance_check.passed else 1)
                + validation_errors
            ),
            notes=f"C2a synthetic dry-run scenario={context.scenario_name}; REST no-op target only",
        )
        return SyntheticDryRunResult(summary=summary, report=report)

    @staticmethod
    def _issue(entity: str, code: str, severity: str, row_ref: str, message: str) -> DryRunIssue:
        return DryRunIssue(
            entity=entity,
            issue_code=code,
            severity=IssueSeverity(severity),
            row_ref=row_ref,
            message=message,
        )
