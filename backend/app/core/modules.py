import uuid
from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.enums import ModuleMode, ModuleStatus
from app.core.exceptions import ModuleDependencyError, ModuleDisabledError, NotFoundError
from app.core.tenancy import TenantContext, get_tenant_context
from app.modules.module_registry.repository import ModuleRegistryRepository


ACTIVE_MODULE_STATUSES = {ModuleStatus.ENABLED, ModuleStatus.TRIAL}


class ModuleGuard:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = ModuleRegistryRepository(db)

    def get_tenant_module(self, module_code: str):
        return self.repo.get_tenant_module(self.tenant_id, module_code)

    def is_active(self, module_code: str) -> bool:
        tenant_module = self.get_tenant_module(module_code)
        if tenant_module is None:
            return False
        return tenant_module.status in ACTIVE_MODULE_STATUSES

    def assert_enabled(self, module_code: str) -> None:
        tenant_module = self.get_tenant_module(module_code)
        if tenant_module is None:
            raise ModuleDisabledError(f"Module '{module_code}' is not configured for tenant")
        if tenant_module.status not in ACTIVE_MODULE_STATUSES:
            raise ModuleDisabledError(
                f"Module '{module_code}' is not enabled (status: {tenant_module.status.value})"
            )

    def assert_mode(
        self,
        module_code: str,
        allowed_modes: set[ModuleMode],
    ) -> None:
        self.assert_enabled(module_code)
        tenant_module = self.get_tenant_module(module_code)
        assert tenant_module is not None
        if tenant_module.mode not in allowed_modes:
            raise ModuleDisabledError(
                f"Module '{module_code}' mode '{tenant_module.mode.value}' "
                f"is not allowed for this operation"
            )

    def check_required_dependencies(self, module_code: str) -> list[str]:
        definition = self.repo.get_definition(module_code)
        if not definition:
            raise NotFoundError(f"Unknown module '{module_code}'")

        required = definition.dependencies_json.get("required", [])
        missing: list[str] = []
        for dep_code in required:
            if not self.is_active(dep_code):
                missing.append(dep_code)
        return missing

    def assert_dependencies(self, module_code: str) -> None:
        missing = self.check_required_dependencies(module_code)
        if missing:
            raise ModuleDependencyError(
                f"Cannot enable '{module_code}': required modules not active: {', '.join(missing)}"
            )

    def list_active_dependents(self, module_code: str) -> list[str]:
        """Return active modules that list ``module_code`` as a required dependency."""
        dependents: list[str] = []
        for definition in self.repo.list_definitions(active_only=True):
            required = definition.dependencies_json.get("required", []) or []
            if module_code in required and self.is_active(definition.code):
                dependents.append(definition.code)
        return sorted(dependents)

    def assert_no_active_dependents(self, module_code: str) -> None:
        dependents = self.list_active_dependents(module_code)
        if dependents:
            raise ModuleDependencyError(
                f"Cannot disable '{module_code}': required by active modules: "
                f"{', '.join(dependents)}"
            )


def require_module(module_code: str) -> Callable:
    def dependency(
        ctx: TenantContext = Depends(get_tenant_context),
        db: Session = Depends(get_db),
    ) -> TenantContext:
        ModuleGuard(db, ctx.tenant.id).assert_enabled(module_code)
        return ctx

    return dependency
