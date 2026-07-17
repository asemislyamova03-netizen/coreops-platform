"""Import all ORM models for Alembic autogenerate and metadata registration."""

from app.modules.auth.models import User  # noqa: F401
from app.modules.branches.models import Branch  # noqa: F401
from app.modules.module_registry.models import ModuleDefinition, TenantModule  # noqa: F401
from app.modules.provider.models import ProviderCompany, ProviderStaff  # noqa: F401
from app.modules.subscriptions.models import (  # noqa: F401
    Feature,
    Plan,
    PlanFeature,
    Subscription,
    UsageEvent,
    UsageLimit,
)
from app.modules.industry_templates.models import IndustryTemplate  # noqa: F401
from app.modules.parties.models import (  # noqa: F401
    Address,
    ContactMethod,
    CustomFieldDefinition,
    CustomFieldValue,
    Party,
)
from app.modules.tenants.models import Tenant, TenantSettings, UserTenantMembership  # noqa: F401
from app.modules.catalog.models import (  # noqa: F401
    CatalogItem,
    PriceList,
    PriceListItem,
    UnitOfMeasure,
)
from app.modules.workflows.models import (  # noqa: F401
    Activity,
    Note,
    Pipeline,
    PipelineStage,
    Reminder,
    Task,
    WorkItem,
    WorkItemParticipant,
)
from app.modules.documents.models import (  # noqa: F401
    DocumentAuditTrail,
    DocumentField,
    DocumentFile,
    DocumentInstance,
    DocumentTemplate,
    SignatureRequest,
)
from app.modules.accounting.models import LegalEntity, TaxProfile  # noqa: F401
from app.modules.finance.models import (  # noqa: F401
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
)
from app.modules.integrations.models import (  # noqa: F401
    ExternalReference,
    IntegrationConnection,
    IntegrationProvider,
    SyncJob,
    SyncLog,
    WebhookEvent,
)
from app.modules.ai.models import (  # noqa: F401
    AIActionProposal,
    AIAgent,
    AIApproval,
    AITask,
    AIUsageEvent,
)
from app.modules.audit.models import AuditLog, DataAccessLog, SecurityEvent  # noqa: F401
from app.modules.booking.models import (  # noqa: F401
    BookingBookableObject,
    BookingCommissionRule,
    BookingItem,
    BookingManagementPermission,
    BookingMapPoint,
    BookingObjectPhoto,
    BookingOrder,
    BookingOwner,
    BookingTerritory,
)
from app.modules.marketing.models import (  # noqa: F401
    MarketingContentTopic,
    MarketingLeadAttribution,
    MarketingMediaAsset,
    MarketingPublicationPack,
    MarketingPublicationText,
    MarketingPublishingConnection,
    MarketingPublishLog,
    MarketingStorageResourceProfile,
)
from app.modules.process_overlay.models import (  # noqa: F401
    ProcessDefinitionVersion,
    ProcessRun,
    ProcessTemplate,
    TenantProcessConfiguration,
)
