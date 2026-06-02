from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderTestResult:
    success: bool
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ProviderSyncResult:
    success: bool
    message: str
    entities_synced: int = 0
    references_created: int = 0
    references_updated: int = 0
    details: dict = field(default_factory=dict)


class IntegrationAdapter(ABC):
    provider_code: str

    @abstractmethod
    def test_connection(self, credentials: dict, settings: dict) -> ProviderTestResult:
        ...

    @abstractmethod
    def sync(
        self,
        *,
        credentials: dict,
        settings: dict,
        job_type: str,
    ) -> ProviderSyncResult:
        ...
