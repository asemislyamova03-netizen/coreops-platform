"""Shared m7.5.plan.v1 schema + canonical fingerprint helpers (M7.5-C).

Prompt export and JSON importer MUST use this module so contracts stay aligned.
JSON field `date` maps to DB `planned_date`.
API/JSON `line_key` maps to DB `external_line_key`.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "m7.5.plan.v1"

ALLOWED_CHANNELS: frozenset[str] = frozenset(
    {"telegram", "instagram", "threads", "insights"}
)

# Security / payload limits (documented in implementation report + tests).
MAX_JSON_BYTES = 256_000
MAX_ITEMS = 200
MAX_TITLE_LEN = 512
MAX_LINE_KEY_LEN = 128
MAX_WORKING_TITLE_LEN = 512
MAX_TEXT_FIELD_LEN = 4_000
MAX_CHANNELS_PER_ITEM = 8
MAX_MAPPING_ENTRIES = 100
MAX_ADDITIONAL_INSTRUCTIONS_LEN = 4_000
MAX_TARGET_ITEM_COUNT = 366
MAX_RUBRIC_FILTER = 100

_SECRETISH = re.compile(
    r"(secret|token|password|api[_-]?key|bearer|credential)",
    re.IGNORECASE,
)


class PlanItemDocument(BaseModel):
    """One line in m7.5.plan.v1 JSON (`date` → DB planned_date)."""

    model_config = ConfigDict(extra="forbid")

    line_key: str = Field(min_length=1, max_length=MAX_LINE_KEY_LEN)
    date: date
    rubric_code: str = Field(min_length=1, max_length=64)
    working_title: str = Field(min_length=1, max_length=MAX_WORKING_TITLE_LEN)
    angle: str | None = Field(default=None, max_length=MAX_TEXT_FIELD_LEN)
    channels: list[str] = Field(default_factory=list, max_length=MAX_CHANNELS_PER_ITEM)
    format: str | None = Field(default=None, max_length=64)
    goal: str | None = Field(default=None, max_length=MAX_TEXT_FIELD_LEN)
    audience: str | None = Field(default=None, max_length=MAX_TEXT_FIELD_LEN)
    cta: str | None = Field(default=None, max_length=MAX_TEXT_FIELD_LEN)
    pain: str | None = Field(default=None, max_length=MAX_TEXT_FIELD_LEN)
    insight: str | None = Field(default=None, max_length=MAX_TEXT_FIELD_LEN)
    funnel_stage: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=MAX_TEXT_FIELD_LEN)

    @field_validator("line_key", "rubric_code", "working_title", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "angle",
        "format",
        "goal",
        "audience",
        "cta",
        "pain",
        "insight",
        "funnel_stage",
        "notes",
        mode="before",
    )
    @classmethod
    def _strip_optional(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("channels", mode="before")
    @classmethod
    def _normalize_channels(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("channels_must_be_list")
        out: list[str] = []
        for raw in value:
            ch = str(raw).strip().lower()
            if not ch:
                continue
            if ch not in ALLOWED_CHANNELS:
                raise ValueError(f"unsupported_channel:{ch}")
            if ch not in out:
                out.append(ch)
        if len(out) > MAX_CHANNELS_PER_ITEM:
            raise ValueError("too_many_channels")
        return out


class PlanDocument(BaseModel):
    """Root m7.5.plan.v1 document (period_start/period_end = period)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    period_start: date
    period_end: date
    title: str = Field(min_length=1, max_length=MAX_TITLE_LEN)
    items: list[PlanItemDocument] = Field(min_length=1, max_length=MAX_ITEMS)

    @field_validator("schema_version")
    @classmethod
    def _schema_version(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError("unsupported_schema_version")
        return value

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _period_and_keys(self) -> PlanDocument:
        if self.period_start > self.period_end:
            raise ValueError("invalid_period")
        keys = [item.line_key for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate_line_key")
        for item in self.items:
            if item.date < self.period_start or item.date > self.period_end:
                raise ValueError("planned_date_out_of_period")
        return self


def assert_json_size(raw: bytes | str) -> None:
    size = len(raw.encode("utf-8") if isinstance(raw, str) else raw)
    if size > MAX_JSON_BYTES:
        raise ValueError("json_too_large")


def parse_plan_document(raw: dict[str, Any] | str | bytes) -> PlanDocument:
    if isinstance(raw, (bytes, bytearray)):
        assert_json_size(raw)
        try:
            raw = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("malformed_json") from exc
    elif isinstance(raw, str):
        assert_json_size(raw)
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed_json") from exc
    if not isinstance(raw, dict):
        raise ValueError("plan_must_be_object")
    return PlanDocument.model_validate(raw)


def plan_json_schema() -> dict[str, Any]:
    """JSON Schema fragment embedded in prompt export (not OpenAPI)."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "FlexityMarketingContentPlan",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "period_start", "period_end", "title", "items"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "period_start": {"type": "string", "format": "date"},
            "period_end": {"type": "string", "format": "date"},
            "title": {"type": "string", "minLength": 1, "maxLength": MAX_TITLE_LEN},
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_ITEMS,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "line_key",
                        "date",
                        "rubric_code",
                        "working_title",
                        "channels",
                    ],
                    "properties": {
                        "line_key": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_LINE_KEY_LEN,
                        },
                        "date": {"type": "string", "format": "date"},
                        "rubric_code": {"type": "string", "minLength": 1, "maxLength": 64},
                        "working_title": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_WORKING_TITLE_LEN,
                        },
                        "angle": {"type": ["string", "null"]},
                        "channels": {
                            "type": "array",
                            "items": {"enum": sorted(ALLOWED_CHANNELS)},
                            "uniqueItems": True,
                            "maxItems": MAX_CHANNELS_PER_ITEM,
                        },
                        "format": {"type": ["string", "null"]},
                        "goal": {"type": ["string", "null"]},
                        "audience": {"type": ["string", "null"]},
                        "cta": {"type": ["string", "null"]},
                        "pain": {"type": ["string", "null"]},
                        "insight": {"type": ["string", "null"]},
                        "funnel_stage": {"type": ["string", "null"]},
                        "notes": {"type": ["string", "null"]},
                    },
                },
            },
        },
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def canonical_plan_dict(doc: PlanDocument) -> dict[str, Any]:
    """Order-insensitive canonical form for fingerprinting."""
    items = []
    for item in sorted(doc.items, key=lambda row: row.line_key):
        payload = {
            "line_key": item.line_key,
            "date": item.date.isoformat(),
            "rubric_code": item.rubric_code,
            "working_title": item.working_title,
            "angle": item.angle,
            "channels": sorted(item.channels),
            "format": item.format,
            "goal": item.goal,
            "audience": item.audience,
            "cta": item.cta,
            "pain": item.pain,
            "insight": item.insight,
            "funnel_stage": item.funnel_stage,
            "notes": item.notes,
        }
        items.append(payload)
    return {
        "schema_version": doc.schema_version,
        "period_start": doc.period_start.isoformat(),
        "period_end": doc.period_end.isoformat(),
        "title": doc.title,
        "items": items,
    }


def compute_import_fingerprint(tenant_id: Any, doc: PlanDocument) -> str:
    """Server-only fingerprint. Tenant is part of the idempotency scope."""
    canonical = {
        "tenant_id": str(tenant_id),
        "plan": canonical_plan_dict(doc),
    }
    encoded = json.dumps(
        _jsonable(canonical),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assert_no_secretish_keys(obj: Any) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if _SECRETISH.search(str(key)):
                raise ValueError("forbidden_secretish_key")
            assert_no_secretish_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            assert_no_secretish_keys(item)
