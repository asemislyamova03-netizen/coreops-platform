import enum


class ProviderRole(str, enum.Enum):
    PROVIDER_OWNER = "provider_owner"
    PROVIDER_ADMIN = "provider_admin"
    SALES_MANAGER = "sales_manager"
    IMPLEMENTATION_MANAGER = "implementation_manager"
    CONSULTANT = "consultant"
    SUPPORT_MANAGER = "support_manager"
    FINANCE_MANAGER = "finance_manager"
    DEVELOPER = "developer"


class TenantRole(str, enum.Enum):
    TENANT_OWNER = "tenant_owner"
    TENANT_ADMIN = "tenant_admin"
    MEMBER = "member"


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class ModuleStatus(str, enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    TRIAL = "trial"
    SUSPENDED = "suspended"


class ModuleMode(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    HYBRID = "hybrid"
    DISABLED = "disabled"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class UsagePeriod(str, enum.Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class PartyType(str, enum.Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    SOLE_PROPRIETOR = "sole_proprietor"


class PartyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ContactMethodType(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"
    MOBILE = "mobile"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    OTHER = "other"


class AddressType(str, enum.Enum):
    LEGAL = "legal"
    ACTUAL = "actual"
    MAILING = "mailing"
    OTHER = "other"


class WorkItemStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ActivityType(str, enum.Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"
    STATUS_CHANGE = "status_change"
    OTHER = "other"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class ReminderStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"


class WorkItemParticipantRole(str, enum.Enum):
    CLIENT = "client"
    ASSIGNEE = "assignee"
    OBSERVER = "observer"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    SENT_FOR_REVIEW = "sent_for_review"
    SENT_FOR_SIGNATURE = "sent_for_signature"
    SIGNED = "signed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class SignatureStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    SIGNED = "signed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class DocumentFileType(str, enum.Enum):
    GENERATED = "generated"
    SIGNED = "signed"
    ATTACHMENT = "attachment"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    SENT = "sent"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    VOID = "void"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    CARD = "card"
    ONLINE = "online"
    OTHER = "other"


class PaymentDirection(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    NEEDS_REVIEW = "needs_review"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    REJECT = "reject"
    LOGIN = "login"
    OTHER = "other"


class SecurityEventType(str, enum.Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    OTHER = "other"


class DataAccessType(str, enum.Enum):
    READ = "read"
    LIST = "list"
    EXPORT = "export"
    SEARCH = "search"


class AITaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIActionProposalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AIApprovalDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class AIActionType(str, enum.Enum):
    SEND_DOCUMENT = "send_document"
    CREATE_INVOICE = "create_invoice"
    UPDATE_PAYMENT = "update_payment"
    DELETE_DATA = "delete_data"
    SEND_MESSAGE = "send_message"
    CHANGE_WORK_ITEM_STATUS = "change_work_item_status"
    UPDATE_LEGAL_PROFILE = "update_legal_profile"
    OTHER = "other"


class IntegrationConnectionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class ExternalSyncStatus(str, enum.Enum):
    PENDING = "pending"
    LINKED = "linked"
    SYNCED = "synced"
    ERROR = "error"


class SyncJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncJobType(str, enum.Enum):
    TEST = "test"
    FULL_SYNC = "full_sync"
    INCREMENTAL = "incremental"


class SyncLogLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TaxRegime(str, enum.Enum):
    GENERAL = "general"
    SIMPLIFIED = "simplified"
    PATENT = "patent"
    OTHER = "other"


class CatalogItemType(str, enum.Enum):
    PRODUCT = "product"
    SERVICE = "service"
    SUBSCRIPTION_SERVICE = "subscription_service"
    BUNDLE = "bundle"
    FEE = "fee"
    DISCOUNT = "discount"


class CustomFieldType(str, enum.Enum):
    STRING = "string"
    TEXT = "text"
    NUMBER = "number"
    MONEY = "money"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    FILE = "file"
    JSON = "json"
    REFERENCE = "reference"
