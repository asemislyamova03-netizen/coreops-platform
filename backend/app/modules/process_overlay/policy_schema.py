from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.process_overlay.constants import MAX_STAGE_CODES, MAX_TRANSITIONS, POLICY_SCHEMA_VERSION
from app.modules.process_overlay.exceptions import ProcessOverlayValidationError

_FORBIDDEN_KEY_PATTERN = re.compile(
    r"(script|eval|exec|lambda|__import__|compile|expression|handler|template_engine)",
    re.IGNORECASE,
)


class TransitionConditionsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_fields: list[str] = Field(default_factory=list, max_length=50)
    required_roles: list[str] = Field(default_factory=list, max_length=20)
    requires_approval: bool = False
    required_task_codes: list[str] = Field(default_factory=list, max_length=50)
    required_document_types: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("required_fields", "required_roles", "required_task_codes", "required_document_types")
    @classmethod
    def _non_empty_strings(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(value):
            raise ValueError("entries must be non-empty strings")
        return cleaned


class PolicyTransitionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_stage_code: str = Field(min_length=1, max_length=64)
    to_stage_code: str = Field(min_length=1, max_length=64)
    conditions: TransitionConditionsV1 = Field(default_factory=TransitionConditionsV1)


class PolicySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    process_template_code: str = Field(min_length=1, max_length=64)
    pipeline_code: str = Field(min_length=1, max_length=64)
    stage_codes: list[str] = Field(min_length=1, max_length=MAX_STAGE_CODES)
    transitions: list[PolicyTransitionV1] = Field(default_factory=list, max_length=MAX_TRANSITIONS)
    module_requirements: list[str] = Field(default_factory=list, max_length=20)
    terminal_stage_codes: list[str] = Field(default_factory=list, max_length=MAX_STAGE_CODES)

    @field_validator("schema_version")
    @classmethod
    def _schema_version_must_match(cls, value: int) -> int:
        if value != POLICY_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {POLICY_SCHEMA_VERSION}")
        return value

    @field_validator("stage_codes", "terminal_stage_codes", "module_requirements")
    @classmethod
    def _unique_string_list(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("entries must be non-empty strings")
        if len(set(normalized)) != len(normalized):
            raise ValueError("entries must be unique")
        return normalized

    @model_validator(mode="after")
    def _validate_graph(self) -> PolicySnapshotV1:
        stage_set = set(self.stage_codes)
        if not stage_set:
            raise ValueError("stage_codes must not be empty")

        for terminal in self.terminal_stage_codes:
            if terminal not in stage_set:
                raise ValueError(f"terminal stage '{terminal}' is not in stage_codes")

        seen_edges: set[tuple[str, str]] = set()
        for transition in self.transitions:
            if transition.from_stage_code not in stage_set:
                raise ValueError(
                    f"transition from '{transition.from_stage_code}' is not in stage_codes"
                )
            if transition.to_stage_code not in stage_set:
                raise ValueError(
                    f"transition to '{transition.to_stage_code}' is not in stage_codes"
                )
            edge = (transition.from_stage_code, transition.to_stage_code)
            if edge in seen_edges:
                raise ValueError(f"duplicate transition {edge[0]} -> {edge[1]}")
            seen_edges.add(edge)

        return self


def reject_forbidden_policy_keys(payload: Any, *, path: str = "policy") -> None:
    """Additional denylist scan for executable or unknown dangerous keys."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if _FORBIDDEN_KEY_PATTERN.search(key):
                raise ProcessOverlayValidationError(
                    f"Forbidden policy key at {path}.{key}",
                    errors=[f"{path}.{key}"],
                )
            reject_forbidden_policy_keys(value, path=f"{path}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            reject_forbidden_policy_keys(item, path=f"{path}[{index}]")


def parse_policy_snapshot(payload: dict) -> PolicySnapshotV1:
    reject_forbidden_policy_keys(payload)
    try:
        return PolicySnapshotV1.model_validate(payload)
    except Exception as exc:
        raise ProcessOverlayValidationError(
            "Invalid policy snapshot",
            errors=[str(exc)],
        ) from exc


def validate_policy_against_pipeline(
    policy: PolicySnapshotV1,
    *,
    pipeline_code: str,
    pipeline_stage_codes: set[str],
    process_template_code: str,
) -> None:
    errors: list[str] = []

    if policy.pipeline_code != pipeline_code:
        errors.append(
            f"policy.pipeline_code '{policy.pipeline_code}' does not match pipeline '{pipeline_code}'"
        )
    if policy.process_template_code != process_template_code:
        errors.append(
            "policy.process_template_code does not match bound process template"
        )

    unknown_stages = sorted(set(policy.stage_codes) - pipeline_stage_codes)
    if unknown_stages:
        errors.append(f"unknown stage codes for pipeline: {', '.join(unknown_stages)}")

    if errors:
        raise ProcessOverlayValidationError("Policy pipeline validation failed", errors=errors)
