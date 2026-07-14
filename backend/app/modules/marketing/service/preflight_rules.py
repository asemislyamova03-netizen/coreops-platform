"""Marketing M7-C1 Preflight v2 rule helpers (no migration)."""

from __future__ import annotations

from typing import Any

from app.modules.marketing.enums import MarketingChannel
from app.modules.marketing.schemas import PreflightCheckItem, PreflightIssue
from app.modules.marketing.topic_metadata import extract_editorial_fields

PREFLIGHT_REPORT_VERSION = "m7-c1"

MIN_SOCIAL_TEXT_BLOCKER = 20
MIN_SOCIAL_TEXT_WARN = 40

SOCIAL_CHANNELS: tuple[MarketingChannel, ...] = (
    MarketingChannel.TELEGRAM,
    MarketingChannel.INSTAGRAM,
    MarketingChannel.THREADS,
)

CTA_FUNNEL_STAGES: frozenset[str] = frozenset(
    {
        "diagnosis",
        "consultation",
        "product_education",
        "objection_handling",
    }
)


def _filled(value: str | None) -> bool:
    return bool(value and str(value).strip())


def topic_context_summary_from_topic(topic: Any | None) -> dict[str, Any] | None:
    if topic is None:
        return None
    editorial = extract_editorial_fields(getattr(topic, "metadata_json", None))
    return {
        "topic_id": str(topic.id),
        "title": topic.title,
        "status": topic.status.value if hasattr(topic.status, "value") else str(topic.status),
        "audience": editorial["audience"],
        "pain": editorial["pain"],
        "insight": editorial["insight"],
        "source_ref": editorial["source_ref"],
        "cta": editorial["cta"],
        "funnel_stage": editorial["funnel_stage"],
        "notes": editorial["notes"],
        "planned_date": editorial["planned_date"],
        "has_audience": _filled(editorial["audience"]),
        "has_pain": _filled(editorial["pain"]),
        "has_insight": _filled(editorial["insight"]),
        "has_source_ref": _filled(editorial["source_ref"]),
        "has_cta": _filled(editorial["cta"]),
        "has_notes": _filled(editorial["notes"]),
        "has_planned_date": _filled(editorial["planned_date"]),
    }


def append_topic_context_rules(
    *,
    pack_topic_id: Any | None,
    topic: Any | None,
    errors: list[PreflightIssue],
    warnings: list[PreflightIssue],
    checks: list[PreflightCheckItem],
) -> dict[str, Any] | None:
    summary = topic_context_summary_from_topic(topic) if topic is not None else None

    if pack_topic_id is None:
        errors.append(
            PreflightIssue(
                code="topic_missing",
                message="Pack has no linked topic",
            )
        )
        checks.append(
            PreflightCheckItem(
                code="topic_linked",
                passed=False,
                message="topic_id is null",
            )
        )
        return None

    checks.append(PreflightCheckItem(code="topic_linked", passed=True))

    if topic is None:
        # Linked id but relation not loaded / missing row — treat as fail-safe.
        errors.append(
            PreflightIssue(
                code="topic_missing",
                message="Linked topic could not be loaded",
            )
        )
        return None

    editorial = extract_editorial_fields(topic.metadata_json)
    audience = editorial["audience"]
    pain = editorial["pain"]
    insight = editorial["insight"]
    source_ref = editorial["source_ref"]
    cta = editorial["cta"]
    funnel_stage = editorial["funnel_stage"]
    notes = editorial["notes"]
    planned_date = editorial["planned_date"]

    if not _filled(audience) and not _filled(pain) and not _filled(cta):
        errors.append(
            PreflightIssue(
                code="context_triple_missing",
                message="Audience, pain and CTA are all missing on the linked topic",
            )
        )
        checks.append(
            PreflightCheckItem(
                code="context_triple",
                passed=False,
                message="audience, pain and cta are empty",
            )
        )
    else:
        checks.append(PreflightCheckItem(code="context_triple", passed=True))

    if not _filled(insight):
        warnings.append(
            PreflightIssue(
                code="insight_missing",
                message="Topic insight is empty",
            )
        )
        checks.append(PreflightCheckItem(code="insight_present", passed=False))
    else:
        checks.append(PreflightCheckItem(code="insight_present", passed=True))

    if not _filled(source_ref):
        warnings.append(
            PreflightIssue(
                code="source_ref_missing",
                message="Topic source_ref is empty",
            )
        )
        checks.append(PreflightCheckItem(code="source_ref_present", passed=False))
    else:
        checks.append(PreflightCheckItem(code="source_ref_present", passed=True))

    if funnel_stage in CTA_FUNNEL_STAGES and not _filled(cta):
        warnings.append(
            PreflightIssue(
                code="cta_missing_for_funnel",
                message=f"CTA is empty for funnel_stage={funnel_stage}",
            )
        )
        checks.append(
            PreflightCheckItem(
                code="cta_for_funnel",
                passed=False,
                message=f"funnel {funnel_stage} expects CTA",
            )
        )
    else:
        checks.append(PreflightCheckItem(code="cta_for_funnel", passed=True))

    if not _filled(notes):
        warnings.append(
            PreflightIssue(
                code="notes_missing",
                message="Topic notes are empty",
            )
        )
        checks.append(PreflightCheckItem(code="notes_present", passed=False))
    else:
        checks.append(PreflightCheckItem(code="notes_present", passed=True))

    if not _filled(planned_date):
        warnings.append(
            PreflightIssue(
                code="topic_planned_date_missing",
                message="Topic planned_date is empty",
            )
        )
        checks.append(PreflightCheckItem(code="topic_planned_date_present", passed=False))
    else:
        checks.append(PreflightCheckItem(code="topic_planned_date_present", passed=True))

    return summary


def build_social_channel_checks(
    *,
    text_by_channel: dict[MarketingChannel, Any],
    errors: list[PreflightIssue],
    warnings: list[PreflightIssue],
    checks: list[PreflightCheckItem],
) -> list[dict[str, Any]]:
    channel_checks: list[dict[str, Any]] = []
    non_empty_social_lengths: list[int] = []

    for channel in SOCIAL_CHANNELS:
        row = text_by_channel.get(channel)
        text = (row.text.strip() if row and row.text else "") or ""
        length = len(text)
        present = length > 0
        if present:
            non_empty_social_lengths.append(length)

        short_warn = present and length < MIN_SOCIAL_TEXT_WARN
        entry = {
            "channel": channel.value,
            "present": present,
            "length": length,
            "short_warn": short_warn,
            "below_blocker_threshold": present and length < MIN_SOCIAL_TEXT_BLOCKER,
        }
        channel_checks.append(entry)

        checks.append(
            PreflightCheckItem(
                code=f"{channel.value}_social_length_ok",
                passed=not short_warn,
                channel=channel.value,
                message=None if not short_warn else f"text length {length} < {MIN_SOCIAL_TEXT_WARN}",
            )
        )
        if short_warn:
            warnings.append(
                PreflightIssue(
                    code="channel_text_short",
                    message=(
                        f"{channel.value} text is shorter than "
                        f"{MIN_SOCIAL_TEXT_WARN} characters ({length})"
                    ),
                    channel=channel.value,
                )
            )

    if non_empty_social_lengths and all(n < MIN_SOCIAL_TEXT_BLOCKER for n in non_empty_social_lengths):
        errors.append(
            PreflightIssue(
                code="all_texts_too_short",
                message=(
                    "All non-empty social channel texts are shorter than "
                    f"{MIN_SOCIAL_TEXT_BLOCKER} characters"
                ),
            )
        )
        checks.append(
            PreflightCheckItem(
                code="social_texts_min_length",
                passed=False,
                message=f"all social texts < {MIN_SOCIAL_TEXT_BLOCKER}",
            )
        )
    else:
        checks.append(PreflightCheckItem(code="social_texts_min_length", passed=True))

    return channel_checks


def build_media_checks(
    *,
    media: list[Any],
    warnings: list[PreflightIssue],
    checks: list[PreflightCheckItem],
) -> dict[str, Any]:
    count = len(media)
    missing = count == 0
    checks.append(
        PreflightCheckItem(
            code="media_present",
            passed=not missing,
            message=None if not missing else "no media metadata rows",
        )
    )
    if missing:
        warnings.append(
            PreflightIssue(
                code="media_missing",
                message="Pack has no media metadata",
            )
        )
    return {
        "count": count,
        "missing": missing,
    }
