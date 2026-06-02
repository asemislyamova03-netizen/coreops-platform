import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ModuleMode, ModuleStatus
from app.modules.module_registry.models import ModuleDefinition, TenantModule


class ModuleRegistryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_definitions(self, active_only: bool = True) -> list[ModuleDefinition]:
        stmt = select(ModuleDefinition).order_by(ModuleDefinition.code)
        if active_only:
            stmt = stmt.where(ModuleDefinition.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_definition(self, code: str) -> ModuleDefinition | None:
        stmt = select(ModuleDefinition).where(ModuleDefinition.code == code)
        return self.db.scalar(stmt)

    def list_tenant_modules(self, tenant_id: uuid.UUID) -> list[TenantModule]:
        stmt = (
            select(TenantModule)
            .where(TenantModule.tenant_id == tenant_id)
            .order_by(TenantModule.module_code)
        )
        return list(self.db.scalars(stmt).all())

    def get_tenant_module(self, tenant_id: uuid.UUID, module_code: str) -> TenantModule | None:
        stmt = select(TenantModule).where(
            TenantModule.tenant_id == tenant_id,
            TenantModule.module_code == module_code,
        )
        return self.db.scalar(stmt)

    def create_tenant_module(
        self,
        *,
        tenant_id: uuid.UUID,
        module_code: str,
        status: ModuleStatus = ModuleStatus.DISABLED,
        mode: ModuleMode = ModuleMode.DISABLED,
    ) -> TenantModule:
        tenant_module = TenantModule(
            tenant_id=tenant_id,
            module_code=module_code,
            status=status,
            mode=mode,
        )
        self.db.add(tenant_module)
        self.db.flush()
        return tenant_module

    def upsert_definition(self, **kwargs) -> ModuleDefinition:
        existing = self.get_definition(kwargs["code"])
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing
        definition = ModuleDefinition(**kwargs)
        self.db.add(definition)
        self.db.flush()
        return definition
