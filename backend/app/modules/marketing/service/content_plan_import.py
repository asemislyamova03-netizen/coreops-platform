"""M7.5-C content plan JSON preview + commit import."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.modules.audit.recorder import AuditRecorder
from app.modules.auth.models import User
from app.modules.marketing.content_plan_schema import (
    MAX_MAPPING_ENTRIES,
    PlanDocument,
    compute_import_fingerprint,
    parse_plan_document,
)
from app.modules.marketing.enums import (
    MarketingContentPlanItemStatus,
    MarketingContentPlanSource,
    MarketingContentPlanStatus,
    MarketingRubricStatus,
)
from app.modules.marketing.exceptions import (
    MarketingContentPlanValidationError,
    MarketingRubricNotFoundError,
)
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import (
    ContentPlanImportCommitRequest,
    ContentPlanImportCommitResponse,
    ContentPlanImportPreviewRequest,
    ContentPlanImportPreviewResponse,
    ContentPlanImportResolvedItem,
    ContentPlanImportIssue,
    ContentPlanResponse,
)


class MarketingContentPlanImportService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def preview(
        self,
        payload: ContentPlanImportPreviewRequest,
    ) -> ContentPlanImportPreviewResponse:
        doc, parse_errors = self._parse_document(payload.plan)
        mapping = self._normalize_mapping(payload.rubric_code_map)
        if doc is None:
            return ContentPlanImportPreviewResponse(
                valid=False,
                errors=parse_errors,
                warnings=[],
                unknown_rubric_codes=[],
                resolved_items=[],
                import_fingerprint=None,
                fingerprint_already_imported=False,
                existing_plan_id=None,
            )

        fingerprint = compute_import_fingerprint(self.tenant_id, doc)
        existing = self.repo.get_content_plan_by_fingerprint(self.tenant_id, fingerprint)
        errors: list[ContentPlanImportIssue] = []
        warnings: list[ContentPlanImportIssue] = []
        unknown: list[str] = []
        resolved_items: list[ContentPlanImportResolvedItem] = []

        for idx, item in enumerate(doc.items):
            path = f"items[{idx}]"
            rubric_id, issue, is_unknown = self._resolve_rubric_code(
                item.rubric_code,
                mapping,
                path=path,
            )
            if issue is not None:
                if is_unknown:
                    unknown.append(item.rubric_code)
                    warnings.append(issue)
                else:
                    errors.append(issue)
            resolved_items.append(
                ContentPlanImportResolvedItem(
                    line_key=item.line_key,
                    date=item.date,
                    rubric_code=item.rubric_code,
                    rubric_id=rubric_id,
                    working_title=item.working_title,
                    channels=list(item.channels),
                    resolved=rubric_id is not None,
                )
            )

        if existing is not None:
            warnings.append(
                ContentPlanImportIssue(
                    code="fingerprint_already_imported",
                    path="import_fingerprint",
                    message=f"Plan {existing.id} already imported with this fingerprint",
                )
            )

        for i, item in enumerate(resolved_items):
            if item.resolved:
                continue
            path = f"items[{i}].rubric_code"
            if any(err.path == path for err in errors):
                continue
            errors.append(
                ContentPlanImportIssue(
                    code="unresolved_rubric",
                    path=path,
                    message=f"Unresolved rubric_code={item.rubric_code}",
                )
            )

        valid = len(errors) == 0
        return ContentPlanImportPreviewResponse(
            valid=valid,
            errors=errors,
            warnings=warnings,
            unknown_rubric_codes=sorted(set(unknown)),
            resolved_items=resolved_items,
            import_fingerprint=fingerprint,
            fingerprint_already_imported=existing is not None,
            existing_plan_id=existing.id if existing else None,
        )

    def commit(
        self,
        user: User,
        payload: ContentPlanImportCommitRequest,
    ) -> ContentPlanImportCommitResponse:
        doc, parse_errors = self._parse_document(payload.plan)
        if doc is None:
            detail = parse_errors[0].code if parse_errors else "invalid_plan"
            raise MarketingContentPlanValidationError(detail)

        mapping = self._normalize_mapping(payload.rubric_code_map)
        fingerprint = compute_import_fingerprint(self.tenant_id, doc)
        existing = self.repo.get_content_plan_by_fingerprint(self.tenant_id, fingerprint)
        if existing is not None:
            AuditRecorder(self.db).audit_log(
                action=AuditAction.EXECUTE,
                summary="Marketing content plan import replay",
                tenant_id=self.tenant_id,
                user_id=user.id,
                entity_type="marketing_content_plan",
                entity_id=existing.id,
                changes_json={
                    "replayed": True,
                    "import_fingerprint": fingerprint,
                    "item_count": len(doc.items),
                },
            )
            return ContentPlanImportCommitResponse(
                plan=ContentPlanResponse.model_validate(existing),
                item_count=len(
                    self.repo.list_content_plan_items(self.tenant_id, existing.id)
                ),
                replayed=True,
                import_fingerprint=fingerprint,
            )

        resolved: list[tuple[Any, uuid.UUID]] = []
        for idx, item in enumerate(doc.items):
            rubric_id, issue, _unknown = self._resolve_rubric_code(
                item.rubric_code,
                mapping,
                path=f"items[{idx}]",
            )
            if rubric_id is None:
                raise MarketingContentPlanValidationError(
                    issue.code if issue else "unresolved_rubric"
                )
            resolved.append((item, rubric_id))

        guide = self.repo.get_active_guide(self.tenant_id)
        plan = self.repo.create_content_plan(
            tenant_id=self.tenant_id,
            title=doc.title,
            period_start=doc.period_start,
            period_end=doc.period_end,
            status=MarketingContentPlanStatus.DRAFT,
            guide_id=guide.id if guide else None,
            guide_version=guide.version if guide else None,
            source=MarketingContentPlanSource.JSON_IMPORT,
            import_fingerprint=fingerprint,
            metadata_json={"schema_version": doc.schema_version},
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        for sort_order, (item, rubric_id) in enumerate(resolved):
            self.repo.create_content_plan_item(
                tenant_id=self.tenant_id,
                plan_id=plan.id,
                planned_date=item.date,
                rubric_id=rubric_id,
                working_title=item.working_title,
                angle=item.angle,
                channels=list(item.channels),
                format=item.format,
                goal=item.goal,
                audience=item.audience,
                cta=item.cta,
                pain=item.pain,
                insight=item.insight,
                funnel_stage=item.funnel_stage,
                notes=item.notes,
                status=MarketingContentPlanItemStatus.DRAFT,
                topic_id=None,
                external_line_key=item.line_key,
                sort_order=sort_order,
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
            )

        AuditRecorder(self.db).audit_log(
            action=AuditAction.CREATE,
            summary="Marketing content plan imported from JSON",
            tenant_id=self.tenant_id,
            user_id=user.id,
            entity_type="marketing_content_plan",
            entity_id=plan.id,
            changes_json={
                "replayed": False,
                "import_fingerprint": fingerprint,
                "item_count": len(resolved),
                "source": MarketingContentPlanSource.JSON_IMPORT.value,
            },
        )
        self.db.flush()
        return ContentPlanImportCommitResponse(
            plan=ContentPlanResponse.model_validate(plan),
            item_count=len(resolved),
            replayed=False,
            import_fingerprint=fingerprint,
        )

    def _parse_document(
        self,
        plan: dict[str, Any] | str,
    ) -> tuple[PlanDocument | None, list[ContentPlanImportIssue]]:
        try:
            if isinstance(plan, str):
                doc = parse_plan_document(plan)
            else:
                doc = parse_plan_document(plan)
            return doc, []
        except ValidationError as exc:
            issues = [
                ContentPlanImportIssue(
                    code="schema_validation_error",
                    path=".".join(str(p) for p in err.get("loc", [])) or "plan",
                    message=str(err.get("msg")),
                )
                for err in exc.errors()
            ]
            return None, issues or [
                ContentPlanImportIssue(
                    code="schema_validation_error",
                    path="plan",
                    message="invalid_plan",
                )
            ]
        except ValueError as exc:
            code = str(exc) or "invalid_plan"
            return None, [
                ContentPlanImportIssue(code=code, path="plan", message=code)
            ]
        except Exception:
            return None, [
                ContentPlanImportIssue(
                    code="malformed_json",
                    path="plan",
                    message="malformed_json",
                )
            ]

    def _normalize_mapping(
        self,
        raw: dict[str, uuid.UUID] | None,
    ) -> dict[str, uuid.UUID]:
        if not raw:
            return {}
        if len(raw) > MAX_MAPPING_ENTRIES:
            raise MarketingContentPlanValidationError("too_many_rubric_mappings")
        out: dict[str, uuid.UUID] = {}
        for code, rubric_id in raw.items():
            key = str(code).strip()
            if not key:
                raise MarketingContentPlanValidationError("empty_rubric_mapping_code")
            out[key] = rubric_id
        return out

    def _resolve_rubric_code(
        self,
        rubric_code: str,
        mapping: dict[str, uuid.UUID],
        *,
        path: str,
    ) -> tuple[uuid.UUID | None, ContentPlanImportIssue | None, bool]:
        if rubric_code in mapping:
            rubric_id = mapping[rubric_code]
            row = self.repo.get_rubric(self.tenant_id, rubric_id)
            if row is None:
                # Cross-tenant / missing → fail closed as not found.
                raise MarketingRubricNotFoundError()
            if row.status != MarketingRubricStatus.ACTIVE:
                return (
                    None,
                    ContentPlanImportIssue(
                        code="rubric_not_active",
                        path=f"{path}.rubric_code",
                        message=f"Mapped rubric {rubric_id} is not active",
                    ),
                    False,
                )
            return row.id, None, False

        row = self.repo.get_rubric_by_code(self.tenant_id, rubric_code)
        if row is None:
            return (
                None,
                ContentPlanImportIssue(
                    code="unknown_rubric",
                    path=f"{path}.rubric_code",
                    message=f"Unknown rubric_code={rubric_code}",
                ),
                True,
            )
        if row.status != MarketingRubricStatus.ACTIVE:
            return (
                None,
                ContentPlanImportIssue(
                    code="rubric_not_active",
                    path=f"{path}.rubric_code",
                    message=f"Rubric {rubric_code} is not active",
                ),
                False,
            )
        return row.id, None, False
