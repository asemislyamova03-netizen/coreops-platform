"""Seed data for plans, features and usage limits."""

FEATURES = [
    {"code": "crm.work_items.create", "module_code": "crm", "name": "Create work items"},
    {"code": "crm.work_items.read", "module_code": "crm", "name": "View work items"},
    {"code": "documents.generate", "module_code": "documents", "name": "Generate documents"},
    {"code": "finance.invoices.create", "module_code": "finance", "name": "Create invoices"},
    {"code": "catalog.items.create", "module_code": "catalog", "name": "Create catalog items"},
    {"code": "ai.tasks.create", "module_code": "ai", "name": "Create AI tasks"},
]

PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "Core CRM and parties for small teams",
        "default_modules_json": ["parties", "crm"],
        "features": [
            "crm.work_items.create",
            "crm.work_items.read",
        ],
        "limits": [
            {"limit_code": "crm.work_items", "limit_value": 500, "period": "monthly"},
        ],
    },
    {
        "code": "business",
        "name": "Business",
        "description": "CRM, catalog, documents and finance",
        "default_modules_json": ["parties", "crm", "catalog", "documents", "finance"],
        "features": [
            "crm.work_items.create",
            "crm.work_items.read",
            "documents.generate",
            "finance.invoices.create",
            "catalog.items.create",
        ],
        "limits": [
            {"limit_code": "crm.work_items", "limit_value": 5000, "period": "monthly"},
            {"limit_code": "finance.invoices", "limit_value": 1000, "period": "monthly"},
        ],
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "All modules and AI foundation",
        "default_modules_json": [
            "parties",
            "crm",
            "catalog",
            "documents",
            "finance",
            "accounting",
            "integrations",
            "ai",
        ],
        "features": [f["code"] for f in FEATURES],
        "limits": [],
    },
]
