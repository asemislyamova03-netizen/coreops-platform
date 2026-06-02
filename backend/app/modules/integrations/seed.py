"""Platform integration provider catalog (configuration, not tenant data)."""

INTEGRATION_PROVIDERS = [
    {
        "code": "bitrix24",
        "name": "Bitrix24 (mock)",
        "description": "Mock CRM integration for development and external CRM mode",
        "provider_type": "crm",
        "supported_modules_json": ["crm"],
        "capabilities_json": {
            "sync_parties": True,
            "sync_work_items": True,
            "webhooks": True,
            "mock": True,
        },
    },
    {
        "code": "generic_crm",
        "name": "Generic external CRM",
        "description": "Placeholder adapter for any external CRM via REST",
        "provider_type": "crm",
        "supported_modules_json": ["crm"],
        "capabilities_json": {"sync_parties": True, "sync_work_items": True, "mock": True},
    },
    {
        "code": "mock_accounting",
        "name": "Mock accounting export",
        "description": "Mock finance/accounting bridge",
        "provider_type": "accounting",
        "supported_modules_json": ["finance", "accounting"],
        "capabilities_json": {"sync_invoices": True, "sync_payments": True, "mock": True},
    },
]
