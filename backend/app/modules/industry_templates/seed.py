"""Industry template seed data — configuration only, no industry-specific code paths."""

from app.modules.industry_templates.lead_sources import FLEXITY_SALES_LEAD_SOURCES

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
        {
            "entity_type": "party",
            "field_key": "guardian_relationship",
            "field_type": "select",
            "label": "Тип представителя",
            "applies_to_json": {"party_role": "guardian"},
            "options_json": {"options": ["мать", "отец", "законный опекун"]},
            "is_required": False,
            "sort_order": 10,
        },
        {
            "entity_type": "party",
            "field_key": "start_date",
            "field_type": "date",
            "label": "Дата начала посещения",
            "applies_to_json": {"party_role": "enrollee"},
            "is_required": False,
            "sort_order": 50,
        },
    ],
    "default_document_templates": [
        {
            "code": "parent_contract",
            "name": "Договор с законным представителем",
            "document_type": "contract",
            "body_template": (
                "ДОГОВОР ОБ ОКАЗАНИИ ОБРАЗОВАТЕЛЬНЫХ УСЛУГ № {{contract_number}}\n\n"
                "г. Алматы  {{contract_date}}\n\n"
                "{{kindergarten_name}}, именуемое в дальнейшем «Исполнитель», "
                "и {{guardian_name}} ({{guardian_relationship}}), именуемый(-ая) "
                "в дальнейшем «Заказчик», заключили настоящий договор:\n\n"
                "1. ПРЕДМЕТ ДОГОВОРА\n"
                "1.1. Исполнитель оказывает образовательные услуги для ребёнка: "
                "{{child_name}}.\n"
                "1.2. Срок начала посещения: {{start_date}}.\n\n"
                "2. СТОИМОСТЬ И ПОРЯДОК ОПЛАТЫ\n"
                "2.1. Ежемесячная оплата составляет {{monthly_fee}} тенге.\n"
                "2.2. Оплата производится не позднее 5-го числа каждого месяца.\n\n"
                "3. ПОДПИСИ СТОРОН\n"
                "Заказчик: {{guardian_name}}\n"
                "Исполнитель: ____________________\n"
            ),
            "fields": [
                {"field_key": "contract_number", "label": "Номер договора",
                 "field_type": "string", "is_required": True},
                {"field_key": "contract_date", "label": "Дата договора",
                 "field_type": "date", "is_required": True},
                {"field_key": "kindergarten_name", "label": "Название детского сада",
                 "field_type": "string", "is_required": True},
                {"field_key": "guardian_name", "label": "Законный представитель",
                 "field_type": "string", "is_required": True},
                {"field_key": "guardian_relationship", "label": "Кем является представитель",
                 "field_type": "string", "is_required": False,
                 "default_value": "законный представитель"},
                {"field_key": "child_name", "label": "Ребёнок",
                 "field_type": "string", "is_required": True},
                {"field_key": "start_date", "label": "Дата начала посещения",
                 "field_type": "date", "is_required": True},
                {"field_key": "monthly_fee", "label": "Ежемесячная оплата",
                 "field_type": "string", "is_required": True},
            ],
        },
        {
            "code": "enrollment_application",
            "name": "Заявление на зачисление",
            "document_type": "application",
            "body_template": (
                "ЗАЯВЛЕНИЕ О ЗАЧИСЛЕНИИ В ДОШКОЛЬНУЮ ОРГАНИЗАЦИЮ\n\n"
                "Дата: {{application_date}}\n\n"
                "Я, {{guardian_name}}, прошу зачислить моего ребёнка "
                "{{child_name}}, дата рождения {{birth_date}}, "
                "в группу «{{group_name}}».\n\n"
                "Желаемая дата начала посещения: {{start_date}}.\n\n"
                "Подпись заявителя: ____________________\n"
                "{{guardian_name}}\n"
            ),
            "fields": [
                {"field_key": "application_date", "label": "Дата заявления",
                 "field_type": "date", "is_required": True},
                {"field_key": "guardian_name", "label": "Законный представитель",
                 "field_type": "string", "is_required": True},
                {"field_key": "child_name", "label": "Ребёнок",
                 "field_type": "string", "is_required": True},
                {"field_key": "birth_date", "label": "Дата рождения ребёнка",
                 "field_type": "date", "is_required": True},
                {"field_key": "group_name", "label": "Группа",
                 "field_type": "string", "is_required": False,
                 "default_value": "не указана"},
                {"field_key": "start_date", "label": "Желаемая дата начала",
                 "field_type": "date", "is_required": False,
                 "default_value": "не указана"},
            ],
        },
    ],
    "default_catalog_items": [
        {
            "item_type": "subscription_service",
            "name": "Обучение (месяц)",
            "sku": "edu-monthly",
            "base_price": "25000.00",
            "currency": "KZT",
        },
        {
            "item_type": "fee",
            "name": "Регистрационный взнос",
            "sku": "registration-fee",
            "base_price": "5000.00",
            "currency": "KZT",
        },
        {
            "item_type": "fee",
            "name": "Вступительный взнос",
            "sku": "enrollment-fee",
            "base_price": "10000.00",
            "currency": "KZT",
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

FLEXITY_SALES_BASIC = {
    "code": "flexity_sales_basic",
    "name": "Flexity Sales (внутренний)",
    "description": "Внутренняя воронка продаж Flexity: лиды, диагностика, КП, конвертация в client tenant",
    "default_modules": [
        "parties",
        "crm",
        "documents",
        "finance",
    ],
    "default_roles": [
        {"code": "tenant_owner", "name": "Администратор продаж"},
        {"code": "tenant_admin", "name": "Менеджер продаж"},
        {"code": "member", "name": "Участник команды"},
    ],
    "default_pipelines": [
        {
            "code": "flexity_sales",
            "name": "Воронка продаж Flexity",
            "entity_type": "work_item",
            "is_default": True,
            "stages": [
                {"code": "new_lead", "name": "Новый лид", "sort_order": 10},
                {"code": "contacted", "name": "Первичный контакт", "sort_order": 20},
                {"code": "diagnosis", "name": "Диагностика", "sort_order": 30},
                {"code": "proposal_prepared", "name": "КП подготовлено", "sort_order": 40},
                {"code": "proposal_sent", "name": "КП отправлено", "sort_order": 50},
                {"code": "negotiation", "name": "Переговоры", "sort_order": 60},
                {"code": "accepted", "name": "Согласовано", "sort_order": 70},
                {"code": "rejected", "name": "Отказ", "sort_order": 80, "is_terminal": True},
                {
                    "code": "converted_to_tenant",
                    "name": "Клиент создан",
                    "sort_order": 90,
                    "is_terminal": True,
                },
            ],
        }
    ],
    "default_statuses": {
        "work_item": ["open", "in_progress", "won", "lost"],
    },
    "default_custom_fields": [
        {
            "entity_type": "work_item",
            "field_key": "source_note",
            "field_type": "text",
            "label": "Детали источника",
            "is_required": False,
            "sort_order": 100,
        },
        {
            "entity_type": "work_item",
            "field_key": "disposition",
            "field_type": "select",
            "label": "Причина закрытия",
            "is_required": False,
            "sort_order": 200,
            "options_json": {
                "choices": [
                    "spam",
                    "off_topic",
                    "duplicate",
                    "test",
                    "no_response",
                    "other",
                ],
            },
        },
        {
            "entity_type": "work_item",
            "field_key": "disposition_note",
            "field_type": "text",
            "label": "Пояснение к закрытию",
            "is_required": False,
            "sort_order": 210,
        },
    ],
    "default_document_templates": [],
    "default_catalog_items": [],
    "default_dashboards": [],
    "default_ai_agents": [],
    "labels_config": {
        "entities": {
            "work_item": "Лид",
            "party": "Контакт",
            "invoice": "Счёт",
            "payment": "Оплата",
            "pipeline": "Воронка продаж",
        },
        "party_roles": {
            "lead": "Лид",
            "client": "Клиент",
            "contact": "Контакт",
        },
    },
    "settings_schema": {
        "type": "object",
        "properties": {},
        "lead_sources": FLEXITY_SALES_LEAD_SOURCES,
    },
    "is_active": True,
}

INDUSTRY_TEMPLATES = [KINDERGARTEN_BASIC, FLEXITY_SALES_BASIC]
