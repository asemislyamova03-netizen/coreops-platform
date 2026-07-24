import uuid

from sqlalchemy.orm import Session

from app.core.enums import ModuleMode, ModuleStatus
from app.modules.integrations.service import IntegrationService
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.modules import ModuleGuard
from app.core.permissions import get_provider_staff
from app.modules.auth.models import User
from app.modules.module_registry.repository import ModuleRegistryRepository
from app.modules.module_registry.schemas import TenantModuleUpdate, TenantModuleModeUpdate
from app.modules.module_registry.seed import MODULE_DEFINITIONS
from app.modules.tenants.repository import TenantRepository


class ModuleRegistryService:
    def __init__(self, db: Session):
        self.db = db
        self.registry = ModuleRegistryRepository(db)
        self.tenants = TenantRepository(db)

    def seed_definitions(self) -> None:
        for item in MODULE_DEFINITIONS:
            self.registry.upsert_definition(**item)
        self.db.commit()

    def list_registry(self) -> list:
        return self.registry.list_definitions()

    def provision_tenant_modules(self, tenant_id: uuid.UUID) -> list:
        definitions = self.registry.list_definitions()
        created = []
        for definition in definitions:
            existing = self.registry.get_tenant_module(tenant_id, definition.code)
            if existing:
                continue
            tenant_module = self.registry.create_tenant_module(
                tenant_id=tenant_id,
                module_code=definition.code,
                status=ModuleStatus.DISABLED,
                mode=ModuleMode.DISABLED,
            )
            created.append(tenant_module)
        self.db.flush()
        return created

    def list_tenant_modules(self, user: User, tenant_id: uuid.UUID) -> list:
        self._ensure_provider_access(user, tenant_id)
        return self.registry.list_tenant_modules(tenant_id)

    def get_tenant_module(self, user: User, tenant_id: uuid.UUID, module_code: str):
        self._ensure_provider_access(user, tenant_id)
        tenant_module = self.registry.get_tenant_module(tenant_id, module_code)
        if not tenant_module:
            raise NotFoundError(f"Module '{module_code}' not found for tenant")
        return tenant_module

    def update_tenant_module(
        self,
        user: User,
        tenant_id: uuid.UUID,
        module_code: str,
        payload: TenantModuleUpdate,
    ):
        tenant_module = self.get_tenant_module(user, tenant_id, module_code)
        if payload.status is not None:
            tenant_module.status = payload.status
        if payload.mode is not None:
            tenant_module.mode = payload.mode
        if payload.external_provider_code is not None:
            tenant_module.external_provider_code = payload.external_provider_code
        if payload.settings_json is not None:
            tenant_module.settings_json = payload.settings_json
        self.db.flush()
        self.db.refresh(tenant_module)
        return tenant_module

    def enable_module(self, user: User, tenant_id: uuid.UUID, module_code: str):
        self._ensure_provider_access(user, tenant_id)
        tenant_module = self._get_or_create_tenant_module(tenant_id, module_code)
        # Idempotent: already fully enabled — no-op (preserve mode/settings).
        if tenant_module.status == ModuleStatus.ENABLED:
            return tenant_module

        guard = ModuleGuard(self.db, tenant_id)
        guard.assert_dependencies(module_code)

        definition = self.registry.get_definition(module_code)
        tenant_module.status = ModuleStatus.ENABLED
        if tenant_module.mode == ModuleMode.DISABLED:
            tenant_module.mode = definition.default_mode if definition else ModuleMode.INTERNAL

        self.db.flush()
        self.db.refresh(tenant_module)
        return tenant_module

    def disable_module(self, user: User, tenant_id: uuid.UUID, module_code: str):
        tenant_module = self.get_tenant_module(user, tenant_id, module_code)
        # Idempotent: already disabled — no-op (preserve settings_json).
        if tenant_module.status == ModuleStatus.DISABLED:
            return tenant_module

        ModuleGuard(self.db, tenant_id).assert_no_active_dependents(module_code)

        # Enablement only: never delete tenant business data or settings_json.
        tenant_module.status = ModuleStatus.DISABLED
        tenant_module.mode = ModuleMode.DISABLED
        tenant_module.external_provider_code = None
        self.db.flush()
        self.db.refresh(tenant_module)
        return tenant_module

    def set_module_mode(
        self,
        user: User,
        tenant_id: uuid.UUID,
        module_code: str,
        payload: TenantModuleModeUpdate,
    ):
        tenant_module = self.get_tenant_module(user, tenant_id, module_code)
        if tenant_module.status == ModuleStatus.DISABLED:
            raise ConflictError("Enable the module before changing its mode")

        tenant_module.mode = payload.mode
        if payload.external_provider_code is not None:
            tenant_module.external_provider_code = payload.external_provider_code
        if payload.settings_json is not None:
            tenant_module.settings_json = payload.settings_json

        if payload.mode == ModuleMode.EXTERNAL and not tenant_module.external_provider_code:
            raise ConflictError("external_provider_code is required for external mode")

        if payload.mode == ModuleMode.EXTERNAL and tenant_module.external_provider_code:
            IntegrationService.validate_external_module_mode(
                self.db,
                tenant_id,
                module_code,
                tenant_module.external_provider_code,
                payload.mode,
            )

        self.db.flush()
        self.db.refresh(tenant_module)
        return tenant_module

    def apply_plan_modules(
        self,
        tenant_id: uuid.UUID,
        module_codes: list[str],
        *,
        as_trial: bool = True,
    ) -> None:
        self.enable_modules_ordered(tenant_id, module_codes, as_trial=as_trial)

    def enable_modules_ordered(
        self,
        tenant_id: uuid.UUID,
        module_codes: list[str],
        *,
        as_trial: bool = True,
    ) -> list[str]:
        """Enable modules respecting dependency order."""
        self.provision_tenant_modules(tenant_id)
        ordered = self._sort_module_codes(module_codes)
        enabled: list[str] = []
        status = ModuleStatus.TRIAL if as_trial else ModuleStatus.ENABLED

        for code in ordered:
            guard = ModuleGuard(self.db, tenant_id)
            guard.assert_dependencies(code)
            tenant_module = self._get_or_create_tenant_module(tenant_id, code)
            definition = self.registry.get_definition(code)
            tenant_module.status = status
            tenant_module.mode = definition.default_mode if definition else ModuleMode.INTERNAL
            enabled.append(code)

        return enabled

    def _sort_module_codes(self, module_codes: list[str]) -> list[str]:
        priority = [
            "parties",
            "catalog",
            "crm",
            "documents",
            "finance",
            "accounting",
            "integrations",
            "ai",
        ]
        codes_set = set(module_codes)
        ordered = [code for code in priority if code in codes_set]
        for code in module_codes:
            if code not in ordered:
                ordered.append(code)
        return ordered

    def _get_or_create_tenant_module(self, tenant_id: uuid.UUID, module_code: str):
        if not self.registry.get_definition(module_code):
            raise NotFoundError(f"Unknown module '{module_code}'")
        tenant_module = self.registry.get_tenant_module(tenant_id, module_code)
        if tenant_module:
            return tenant_module
        return self.registry.create_tenant_module(
            tenant_id=tenant_id,
            module_code=module_code,
        )

    def _ensure_provider_access(self, user: User, tenant_id: uuid.UUID) -> None:
        staff = get_provider_staff(user)
        tenant = self.tenants.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        if not staff or staff.provider_company_id != tenant.provider_company_id:
            raise PermissionDeniedError("Only provider staff can manage tenant modules")
