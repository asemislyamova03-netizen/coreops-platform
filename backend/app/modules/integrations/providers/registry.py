from app.core.exceptions import NotFoundError
from app.modules.integrations.providers.base import IntegrationAdapter
from app.modules.integrations.providers.bitrix24_mock import Bitrix24MockAdapter
from app.modules.integrations.providers.generic import GenericCrmAdapter, MockAccountingAdapter

_ADAPTERS: dict[str, IntegrationAdapter] = {
    "bitrix24": Bitrix24MockAdapter(),
    "generic_crm": GenericCrmAdapter(),
    "mock_accounting": MockAccountingAdapter(),
}


def get_adapter(provider_code: str) -> IntegrationAdapter:
    adapter = _ADAPTERS.get(provider_code)
    if not adapter:
        raise NotFoundError(f"No adapter registered for provider '{provider_code}'")
    return adapter
