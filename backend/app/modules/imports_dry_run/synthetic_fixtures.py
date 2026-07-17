from decimal import Decimal


def build_consulting_synthetic_fixture() -> dict[str, list[dict]]:
    """Synthetic fixture: no real personal data, no production source."""
    return {
        "users": [
            {"id": "u-1", "login": "owner.synthetic", "is_active": True},
            {"id": "u-2", "login": "manager.synthetic", "is_active": True},
            {"id": "u-3", "login": "manager.synthetic", "is_active": True},  # duplicate login
        ],
        "clients": [
            {
                "id": "c-1",
                "status": "active",
                "party_type": "PERSON",
                "display_name": "Synthetic Client A",
                "email": "client-a@synthetic.local",
            },
            {
                "id": "c-2",
                "status": "new",
                "party_type": "BUSINESS",
                "display_name": "Synthetic Client B",
                "email": "client-b@synthetic.local",
            },
        ],
        "services": [
            {"id": "s-1", "name": "Consulting Base"},
            {"id": "s-2", "name": "Implementation Sprint"},
        ],
        "orders": [
            {"id": "o-1", "number": "ORD-100", "client_id": "c-1", "status": "COMPLETED"},
            {"id": "o-2", "number": "ORD-200", "client_id": "c-2", "status": "IN_PROGRESS"},
            {"id": "o-3", "number": "ORD-300", "client_id": "c-404", "status": "UNKNOWN_STATE"},
        ],
        "order_stages": [
            {"id": "os-1", "order_id": "o-1", "template_id": "tpl-1", "status": "DONE"},
            {"id": "os-2", "order_id": "o-2", "template_id": None, "status": "NOT_STARTED"},
            {"id": "os-3", "order_id": "o-x", "template_id": None, "status": "X_STATUS"},
        ],
        "order_items": [
            {"id": "oi-1", "order_id": "o-1", "service_id": "s-1", "amount": Decimal("10000")},
            {"id": "oi-2", "order_id": "o-x", "service_id": "s-2", "amount": Decimal("5000")},
            {"id": "oi-3", "order_id": "o-2", "service_id": "s-x", "amount": Decimal("3000")},
        ],
        "contracts": [
            {
                "id": "ct-1",
                "number": "CON-1",
                "client_id": "c-1",
                "order_id": "o-1",
                "status": "SIGNED",
                "amount": Decimal("10000"),
            },
            {
                "id": "ct-2",
                "number": "CON-2",
                "client_id": "c-2",
                "order_id": None,
                "status": "ON_REVIEW",
                "amount": Decimal("0"),
            },
        ],
        "payments": [
            {"id": "p-1", "order_id": "o-1", "client_id": "c-1", "type": "INCOME", "amount": Decimal("7000")},
            {"id": "p-2", "order_id": "o-2", "client_id": "c-2", "type": "EXPENSE", "amount": Decimal("1000")},
            {"id": "p-3", "order_id": "o-z", "client_id": "c-2", "type": "UNKNOWN_TYPE", "amount": Decimal("1500")},
        ],
    }

