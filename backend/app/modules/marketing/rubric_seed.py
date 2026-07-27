"""Editable default rubric catalog for explicit per-tenant seed (M7.5-A).

Not applied globally. Seed endpoint inserts missing codes only unless force=True.
"""

from __future__ import annotations

from typing import TypedDict


class RubricSeedRow(TypedDict):
    code: str
    name: str
    description: str
    content_instructions: str
    sort_order: int


# Same codes as former FE MARKETING_RUBRIC_OPTIONS — data, not UI SoT.
DEFAULT_RUBRIC_SEED: tuple[RubricSeedRow, ...] = (
    {
        "code": "asem_column",
        "name": "Авторская колонка Асем",
        "description": "Founder-led essays and reflections",
        "content_instructions": "Calm founder voice; not hype.",
        "sort_order": 10,
    },
    {
        "code": "digital_organism",
        "name": "Flexity как цифровой организм",
        "description": "Platform-as-organism metaphor and architecture narrative",
        "content_instructions": "Explain structure without overselling readiness.",
        "sort_order": 20,
    },
    {
        "code": "erp_crm_future",
        "name": "ERP/CRM будущего",
        "description": "Future of ERP/CRM for service businesses",
        "content_instructions": "Practical, honest about gaps.",
        "sort_order": 30,
    },
    {
        "code": "ai_employees",
        "name": "AI-сотрудники",
        "description": "AI employees / assistants as product direction",
        "content_instructions": "No fake production claims.",
        "sort_order": 40,
    },
    {
        "code": "business_diagnosis",
        "name": "Бизнес-диагностика",
        "description": "Diagnosis and process discovery",
        "content_instructions": "Owner language; soft CTA to diagnosis.",
        "sort_order": 50,
    },
    {
        "code": "sales_inbox_review",
        "name": "Разбор заявок и продаж",
        "description": "Inbox / sales review scenarios",
        "content_instructions": "Concrete operational examples.",
        "sort_order": 60,
    },
    {
        "code": "client_journey",
        "name": "Кейсы / путь клиента",
        "description": "Client journey and case narratives",
        "content_instructions": "Anonymize clients; no private data.",
        "sort_order": 70,
    },
    {
        "code": "marketing_contentops",
        "name": "Marketing / ContentOps",
        "description": "Content operations and Marketing Cabinet",
        "content_instructions": "Dogfood Flexity Marketing Cabinet honestly.",
        "sort_order": 80,
    },
    {
        "code": "industry_modules",
        "name": "Clinic / Booking / отраслевые модули",
        "description": "Industry modules and templates",
        "content_instructions": "Do not claim unreleased modules as live.",
        "sort_order": 90,
    },
    {
        "code": "founder_notes",
        "name": "Founder notes / за кадром",
        "description": "Behind-the-scenes founder notes",
        "content_instructions": "Human layer without oversharing.",
        "sort_order": 100,
    },
)
