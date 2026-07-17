"""Lead source dictionary helpers — config in template settings_schema / tenant industry_config_json."""

from __future__ import annotations

from typing import Any

LEGACY_SOURCE_ALIASES: dict[str, str] = {
    "public_demo_form": "website_demo",
}

FLEXITY_SALES_LEAD_SOURCES: list[dict[str, Any]] = [
    {
        "code": "website_demo",
        "label_ru": "Сайт / демо-заявка",
        "channel": "web",
        "active": True,
        "sort_order": 10,
    },
    {
        "code": "instagram_dm",
        "label_ru": "Instagram Direct",
        "channel": "social",
        "active": True,
        "sort_order": 20,
    },
    {
        "code": "telegram_dm",
        "label_ru": "Telegram",
        "channel": "social",
        "active": True,
        "sort_order": 30,
    },
    {
        "code": "whatsapp_manual",
        "label_ru": "WhatsApp",
        "channel": "messenger",
        "active": True,
        "sort_order": 40,
    },
    {
        "code": "insights_article",
        "label_ru": "Insights / статья",
        "channel": "content",
        "active": True,
        "sort_order": 50,
    },
    {
        "code": "referral",
        "label_ru": "Рекомендация",
        "channel": "referral",
        "active": True,
        "sort_order": 60,
    },
    {
        "code": "phone_call",
        "label_ru": "Звонок",
        "channel": "phone",
        "active": True,
        "sort_order": 70,
    },
    {
        "code": "manual",
        "label_ru": "Внесено вручную",
        "channel": "other",
        "active": True,
        "sort_order": 80,
    },
    {
        "code": "other",
        "label_ru": "Другое",
        "channel": "other",
        "active": True,
        "sort_order": 90,
    },
]


def extract_lead_sources_from_settings_schema(settings_schema: dict | None) -> list[dict[str, Any]]:
    if not settings_schema:
        return []
    raw = settings_schema.get("lead_sources")
    if not isinstance(raw, list):
        return []
    return normalize_lead_sources(raw)


def normalize_lead_sources(raw: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        label_ru = item.get("label_ru")
        if not isinstance(code, str) or not code.strip():
            continue
        if not isinstance(label_ru, str) or not label_ru.strip():
            continue
        normalized.append(
            {
                "code": code.strip(),
                "label_ru": label_ru.strip(),
                "channel": str(item.get("channel") or "other"),
                "active": bool(item.get("active", True)),
                "sort_order": int(item.get("sort_order") or 0),
            }
        )
    normalized.sort(key=lambda row: (row["sort_order"], row["code"]))
    return normalized


def active_lead_sources(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in normalize_lead_sources(raw) if item["active"]]


def resolve_lead_source_label(
    sources: list[dict[str, Any]],
    code: str | None,
) -> str | None:
    if not code:
        return None
    canonical = LEGACY_SOURCE_ALIASES.get(code, code)
    for item in sources:
        if item["code"] == canonical:
            return item["label_ru"]
    return code
