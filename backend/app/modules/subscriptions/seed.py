"""Seed data for plans, features and usage limits."""

FEATURES = [
    {"code": "crm.work_items.create", "module_code": "crm", "name": "Create work items"},
    {"code": "crm.work_items.read", "module_code": "crm", "name": "View work items"},
    {"code": "documents.generate", "module_code": "documents", "name": "Generate documents"},
    {"code": "finance.invoices.create", "module_code": "finance", "name": "Create invoices"},
    {"code": "catalog.items.create", "module_code": "catalog", "name": "Create catalog items"},
    {"code": "ai.tasks.create", "module_code": "ai", "name": "Create AI tasks"},
    {"code": "booking.territories.manage", "module_code": "booking", "name": "Manage booking territories"},
    {"code": "booking.objects.manage", "module_code": "booking", "name": "Manage bookable objects"},
    {"code": "booking.orders.create", "module_code": "booking", "name": "Create booking orders and holds"},
    {"code": "booking.orders.read", "module_code": "booking", "name": "View booking orders"},
    {"code": "booking.orders.confirm_payment", "module_code": "booking", "name": "Confirm booking payments"},
    {"code": "booking.public.page", "module_code": "booking", "name": "Public booking page"},
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
        "default_modules_json": ["parties", "crm", "catalog", "documents", "finance", "booking"],
        "features": [
            "crm.work_items.create",
            "crm.work_items.read",
            "documents.generate",
            "finance.invoices.create",
            "catalog.items.create",
            "booking.orders.read",
            "booking.objects.manage",
        ],
        "limits": [
            {"limit_code": "crm.work_items", "limit_value": 5000, "period": "monthly"},
            {"limit_code": "finance.invoices", "limit_value": 1000, "period": "monthly"},
            {"limit_code": "booking.orders", "limit_value": 500, "period": "monthly"},
            {"limit_code": "booking.bookable_objects", "limit_value": 50, "period": "lifetime"},
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
            "booking",
            "accounting",
            "integrations",
            "ai",
        ],
        "features": [f["code"] for f in FEATURES],
        "limits": [],
    },
]
