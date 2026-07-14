"""Registry seed data for module definitions."""

MODULE_DEFINITIONS = [
    {
        "code": "parties",
        "name": "Parties",
        "description": "Universal contacts and organizations",
        "default_mode": "internal",
        "dependencies_json": {"required": [], "recommended": []},
    },
    {
        "code": "crm",
        "name": "CRM & Workflows",
        "description": "Pipelines, work items, tasks and activities",
        "default_mode": "internal",
        "dependencies_json": {"required": ["parties"], "recommended": []},
    },
    {
        "code": "catalog",
        "name": "Catalog",
        "description": "Products and services",
        "default_mode": "internal",
        "dependencies_json": {"required": [], "recommended": []},
    },
    {
        "code": "documents",
        "name": "Documents",
        "description": "Document templates and instances",
        "default_mode": "internal",
        "dependencies_json": {"required": [], "recommended": ["parties"]},
    },
    {
        "code": "finance",
        "name": "Finance",
        "description": "Invoices, payments and receivables",
        "default_mode": "internal",
        "dependencies_json": {"required": [], "recommended": ["catalog", "parties"]},
    },
    {
        "code": "accounting",
        "name": "Accounting Profiles",
        "description": "Legal entity and tax configuration",
        "default_mode": "internal",
        "dependencies_json": {"required": [], "recommended": ["finance"]},
    },
    {
        "code": "integrations",
        "name": "Integrations",
        "description": "External systems and sync",
        "default_mode": "internal",
        "dependencies_json": {"required": [], "recommended": []},
    },
    {
        "code": "ai",
        "name": "AI Foundation",
        "description": "AI agents and action proposals",
        "default_mode": "internal",
        "dependencies_json": {"required": [], "recommended": []},
    },
    {
        "code": "marketing",
        "name": "Marketing Cabinet",
        "description": "Content topics, packs, publish workflow",
        "default_mode": "internal",
        "dependencies_json": {"required": ["parties"], "recommended": []},
    },
]
