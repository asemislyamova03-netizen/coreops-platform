from app.modules.industry_templates.lead_sources import (
    FLEXITY_SALES_LEAD_SOURCES,
    active_lead_sources,
    extract_lead_sources_from_settings_schema,
    resolve_lead_source_label,
)


def test_flexity_sales_lead_sources_seed_count():
    assert len(FLEXITY_SALES_LEAD_SOURCES) == 9
    codes = [item["code"] for item in FLEXITY_SALES_LEAD_SOURCES]
    assert codes == [
        "website_demo",
        "instagram_dm",
        "telegram_dm",
        "whatsapp_manual",
        "insights_article",
        "referral",
        "phone_call",
        "manual",
        "other",
    ]


def test_extract_lead_sources_from_settings_schema():
    settings = {"type": "object", "lead_sources": FLEXITY_SALES_LEAD_SOURCES}
    extracted = extract_lead_sources_from_settings_schema(settings)
    assert len(extracted) == 9
    assert extracted[0]["code"] == "website_demo"


def test_active_lead_sources_filters_inactive():
    raw = [
        {"code": "manual", "label_ru": "Ручной", "channel": "other", "active": True, "sort_order": 1},
        {"code": "hidden", "label_ru": "Hidden", "channel": "other", "active": False, "sort_order": 2},
    ]
    active = active_lead_sources(raw)
    assert [item["code"] for item in active] == ["manual"]


def test_resolve_lead_source_label_legacy_alias():
    sources = extract_lead_sources_from_settings_schema(
        {"lead_sources": FLEXITY_SALES_LEAD_SOURCES}
    )
    assert resolve_lead_source_label(sources, "public_demo_form") == "Сайт / демо-заявка"
    assert resolve_lead_source_label(sources, "manual") == "Внесено вручную"
