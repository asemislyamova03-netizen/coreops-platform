"""Industry template seed data — configuration only, no industry-specific code paths."""

KINDERGARTEN_BASIC = {
    "code": "kindergarten_basic",
    "name": "Детский сад (базовый)",
    "description": "Воронка поступления, родители, договоры и оплата обучения",
    "default_modules": [
        "parties",
        "crm",
        "documents",
        "finance",
        "catalog",
    ],
    "default_roles": [
        {"code": "tenant_owner", "name": "Администратор"},
        {"code": "tenant_admin", "name": "Заведующий"},
        {"code": "member", "name": "Воспитатель"},
    ],
    "default_pipelines": [
        {
            "code": "enrollment",
            "name": "Воронка поступления",
            "entity_type": "work_item",
            "is_default": True,
            "stages": [
                {"code": "new_lead", "name": "Новая заявка", "sort_order": 10},
                {"code": "first_contact", "name": "Первичный контакт", "sort_order": 20},
                {"code": "tour", "name": "Экскурсия / консультация", "sort_order": 30},
                {"code": "awaiting_documents", "name": "Ожидаем документы", "sort_order": 40},
                {"code": "contract_draft", "name": "Договор сформирован", "sort_order": 50},
                {"code": "contract_signed", "name": "Договор подписан", "sort_order": 60},
                {"code": "payment_received", "name": "Оплата получена", "sort_order": 70},
                {"code": "enrolled", "name": "Зачислен", "sort_order": 80, "is_terminal": True},
                {"code": "lost", "name": "Отказ / потерян", "sort_order": 90, "is_terminal": True},
            ],
        }
    ],
    "default_statuses": {
        "work_item": ["open", "in_progress", "won", "lost"],
    },
    "default_custom_fields": [
        {
            "entity_type": "party",
            "field_key": "birth_date",
            "field_type": "date",
            "label": "Дата рождения",
            "applies_to_json": {"party_role": "enrollee"},
            "is_required": True,
            "sort_order": 10,
        },
        {
            "entity_type": "party",
            "field_key": "allergies",
            "field_type": "text",
            "label": "Аллергии",
            "applies_to_json": {"party_role": "enrollee"},
            "sort_order": 20,
        },
        {
            "entity_type": "party",
            "field_key": "medical_notes",
            "field_type": "text",
            "label": "Медкарта / примечания",
            "applies_to_json": {"party_role": "enrollee"},
            "sort_order": 30,
        },
        {
            "entity_type": "party",
            "field_key": "group_name",
            "field_type": "string",
            "label": "Группа",
            "applies_to_json": {"party_role": "enrollee"},
            "sort_order": 40,
        },
        {
            "entity_type": "work_item",
            "field_key": "preferred_start_date",
            "field_type": "date",
            "label": "Желаемая дата начала",
            "sort_order": 10,
        },
    ],
    "default_document_templates": [
        {
            "code": "parent_contract",
            "name": "Договор с законным представителем",
            "document_type": "contract",
        },
        {
            "code": "enrollment_application",
            "name": "Заявление на зачисление",
            "document_type": "application",
        },
    ],
    "default_catalog_items": [
        {
            "item_type": "subscription_service",
            "name": "Обучение (месяц)",
            "sku": "edu-monthly",
        },
        {
            "item_type": "fee",
            "name": "Регистрационный взнос",
            "sku": "registration-fee",
        },
        {
            "item_type": "fee",
            "name": "Вступительный взнос",
            "sku": "enrollment-fee",
        },
    ],
    "default_dashboards": [],
    "default_ai_agents": [
        {"code": "ai_onboarding_manager", "name": "AI менеджер по поступлению"},
        {"code": "ai_document_manager", "name": "AI менеджер документов"},
    ],
    "labels_config": {
        "entities": {
            "work_item": "Заявка",
            "party": "Контрагент",
            "invoice": "Счёт",
            "payment": "Оплата",
            "pipeline": "Воронка поступления",
        },
        "party_roles": {
            "enrollee": "Ребёнок",
            "guardian": "Родитель",
            "staff": "Сотрудник",
        },
        "catalog_item_types": {
            "subscription_service": "Абонемент",
            "fee": "Сбор",
        },
    },
    "settings_schema": {
        "type": "object",
        "properties": {
            "academic_year_start": {"type": "string", "format": "date"},
            "default_group_capacity": {"type": "integer", "minimum": 1},
        },
    },
    "is_active": True,
}

INDUSTRY_TEMPLATES = [KINDERGARTEN_BASIC]
