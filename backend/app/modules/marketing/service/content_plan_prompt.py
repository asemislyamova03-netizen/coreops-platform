"""M7.5-C prompt export — no AI / network calls, no DB writes."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.modules.marketing.content_plan_schema import (
    ALLOWED_CHANNELS,
    MAX_ADDITIONAL_INSTRUCTIONS_LEN,
    MAX_RUBRIC_FILTER,
    MAX_TARGET_ITEM_COUNT,
    SCHEMA_VERSION,
    plan_json_schema,
)
from app.modules.marketing.enums import MarketingRubricStatus
from app.modules.marketing.exceptions import (
    MarketingContentPlanValidationError,
    MarketingGuideNotFoundError,
    MarketingRubricNotFoundError,
)
from app.modules.marketing.models import MarketingGuide, MarketingRubric
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import (
    ContentPlanPromptExportRequest,
    ContentPlanPromptExportResponse,
)


class MarketingContentPlanPromptService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def export_prompt(
        self,
        payload: ContentPlanPromptExportRequest,
    ) -> ContentPlanPromptExportResponse:
        if payload.period_start > payload.period_end:
            raise MarketingContentPlanValidationError("invalid_period")
        if payload.target_item_count is not None and (
            payload.target_item_count < 1 or payload.target_item_count > MAX_TARGET_ITEM_COUNT
        ):
            raise MarketingContentPlanValidationError("invalid_target_item_count")
        if payload.additional_instructions and len(payload.additional_instructions) > (
            MAX_ADDITIONAL_INSTRUCTIONS_LEN
        ):
            raise MarketingContentPlanValidationError("additional_instructions_too_long")

        guide = self.repo.get_active_guide(self.tenant_id)
        if guide is None:
            raise MarketingGuideNotFoundError()

        rubrics = self._resolve_rubrics(payload.rubric_ids)
        if not rubrics:
            raise MarketingContentPlanValidationError("no_active_rubrics")

        channels = self._normalize_channels(payload.channels)
        language = (payload.language or "ru").strip() or "ru"
        prompt_text = self._build_prompt(
            guide=guide,
            rubrics=rubrics,
            period_start=payload.period_start,
            period_end=payload.period_end,
            channels=channels,
            target_item_count=payload.target_item_count,
            frequency=payload.frequency,
            additional_instructions=payload.additional_instructions,
            language=language,
        )
        return ContentPlanPromptExportResponse(
            schema_version=SCHEMA_VERSION,
            prompt_text=prompt_text,
            json_schema=plan_json_schema(),
            guide_id=guide.id,
            guide_version=guide.version,
            rubric_ids=[row.id for row in rubrics],
            rubric_codes=[row.code for row in rubrics],
            period_start=payload.period_start,
            period_end=payload.period_end,
            channels=channels,
            target_item_count=payload.target_item_count,
            frequency=(payload.frequency.strip() if payload.frequency else None),
            language=language,
            generated_at=datetime.now(UTC),
        )

    def _resolve_rubrics(
        self,
        rubric_ids: list[uuid.UUID] | None,
    ) -> list[MarketingRubric]:
        if rubric_ids is None:
            return self.repo.list_rubrics(
                self.tenant_id,
                status=MarketingRubricStatus.ACTIVE,
            )
        if len(rubric_ids) > MAX_RUBRIC_FILTER:
            raise MarketingContentPlanValidationError("too_many_rubric_ids")
        if len(set(rubric_ids)) != len(rubric_ids):
            raise MarketingContentPlanValidationError("duplicate_rubric_ids")
        resolved: list[MarketingRubric] = []
        for rubric_id in rubric_ids:
            row = self.repo.get_rubric(self.tenant_id, rubric_id)
            if row is None:
                raise MarketingRubricNotFoundError()
            if row.status != MarketingRubricStatus.ACTIVE:
                raise MarketingContentPlanValidationError("rubric_not_active")
            resolved.append(row)
        return resolved

    def _normalize_channels(self, channels: list[str] | None) -> list[str]:
        if not channels:
            return sorted(ALLOWED_CHANNELS)
        out: list[str] = []
        for raw in channels:
            ch = str(raw).strip().lower()
            if ch not in ALLOWED_CHANNELS:
                raise MarketingContentPlanValidationError(f"unsupported_channel:{ch}")
            if ch not in out:
                out.append(ch)
        return out

    def _build_prompt(
        self,
        *,
        guide: MarketingGuide,
        rubrics: list[MarketingRubric],
        period_start: date,
        period_end: date,
        channels: list[str],
        target_item_count: int | None,
        frequency: str | None,
        additional_instructions: str | None,
        language: str,
    ) -> str:
        rubric_block = "\n".join(
            (
                f"- code=`{row.code}` | name={row.name}"
                + (f" | instructions={row.content_instructions}" if row.content_instructions else "")
            )
            for row in rubrics
        )
        count_line = (
            f"- Target item count: {target_item_count}"
            if target_item_count is not None
            else f"- Frequency hint: {frequency or guide.default_frequency}"
        )
        extra = (
            f"\n## Additional operator instructions\n{additional_instructions.strip()}\n"
            if additional_instructions and additional_instructions.strip()
            else ""
        )
        schema_text = json.dumps(plan_json_schema(), ensure_ascii=False, indent=2)
        return f"""You are preparing a Flexity Marketing content plan.
Return ONLY valid JSON matching schema_version `{SCHEMA_VERSION}`.
No markdown fences. No commentary. No secrets/tokens/API keys.

## Language
Primary language for titles and editorial fields: {language}

## Period
- period_start: {period_start.isoformat()}
- period_end: {period_end.isoformat()}
{count_line}
- Channels (subset allowed): {", ".join(channels)}

## Active Marketing Guide (v{guide.version})
- Business: {guide.business_name}
- Summary: {guide.business_summary}
- Products/services: {guide.products_services}
- Audiences: {guide.audiences}
- Goals: {guide.goals}
- Tone rules: {guide.tone_rules or "—"}
- Constraints (fail-closed): {guide.constraints or "—"}
- Guide channels: {", ".join(guide.channels or [])}

## Allowed active rubrics (use rubric_code exactly)
{rubric_block}

Hard rules:
1. Every item.date must be inside the period.
2. Every item.rubric_code must be one of the allowed codes above. Do NOT invent new codes.
3. line_key must be unique within the plan.
4. channels must be a subset of: {", ".join(sorted(ALLOWED_CHANNELS))}.
5. Do not include secrets, tokens, passwords, or API keys.
{extra}
## JSON Schema
{schema_text}
"""
