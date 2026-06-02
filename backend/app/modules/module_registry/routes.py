import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_provider_owner
from app.core.modules import require_module
from app.core.tenancy import TenantContext
from app.modules.auth.models import User
from app.modules.module_registry.schemas import (
    ModuleDefinitionResponse,
    TenantModuleModeUpdate,
    TenantModuleResponse,
    TenantModuleUpdate,
)
from app.modules.module_registry.service import ModuleRegistryService

registry_router = APIRouter(prefix="/modules", tags=["modules"])
tenant_modules_router = APIRouter(
    prefix="/tenants/{tenant_id}/modules",
    tags=["tenant-modules"],
)


@registry_router.get("/registry", response_model=list[ModuleDefinitionResponse])
def list_module_registry(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ModuleDefinitionResponse]:
    definitions = ModuleRegistryService(db).list_registry()
    return [ModuleDefinitionResponse.model_validate(d) for d in definitions]


@tenant_modules_router.get("", response_model=list[TenantModuleResponse])
def list_tenant_modules(
    tenant_id: uuid.UUID,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> list[TenantModuleResponse]:
    modules = ModuleRegistryService(db).list_tenant_modules(current_user, tenant_id)
    return [TenantModuleResponse.model_validate(m) for m in modules]


@tenant_modules_router.get("/crm/access-check")
def check_crm_module_access(
    ctx: TenantContext = Depends(require_module("crm")),
) -> dict[str, str]:
    """Example endpoint guarded by require_module('crm')."""
    return {
        "tenant_id": str(ctx.tenant.id),
        "module": "crm",
        "access": "granted",
    }


@tenant_modules_router.get("/{module_code}", response_model=TenantModuleResponse)
def get_tenant_module(
    tenant_id: uuid.UUID,
    module_code: str,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> TenantModuleResponse:
    module = ModuleRegistryService(db).get_tenant_module(
        current_user, tenant_id, module_code
    )
    return TenantModuleResponse.model_validate(module)


@tenant_modules_router.patch("/{module_code}", response_model=TenantModuleResponse)
def patch_tenant_module(
    tenant_id: uuid.UUID,
    module_code: str,
    payload: TenantModuleUpdate,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> TenantModuleResponse:
    module = ModuleRegistryService(db).update_tenant_module(
        current_user, tenant_id, module_code, payload
    )
    db.commit()
    return TenantModuleResponse.model_validate(module)


@tenant_modules_router.post("/{module_code}/enable", response_model=TenantModuleResponse)
def enable_tenant_module(
    tenant_id: uuid.UUID,
    module_code: str,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> TenantModuleResponse:
    module = ModuleRegistryService(db).enable_module(
        current_user, tenant_id, module_code
    )
    db.commit()
    return TenantModuleResponse.model_validate(module)


@tenant_modules_router.post("/{module_code}/disable", response_model=TenantModuleResponse)
def disable_tenant_module(
    tenant_id: uuid.UUID,
    module_code: str,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> TenantModuleResponse:
    module = ModuleRegistryService(db).disable_module(
        current_user, tenant_id, module_code
    )
    db.commit()
    return TenantModuleResponse.model_validate(module)


@tenant_modules_router.patch("/{module_code}/mode", response_model=TenantModuleResponse)
def set_tenant_module_mode(
    tenant_id: uuid.UUID,
    module_code: str,
    payload: TenantModuleModeUpdate,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> TenantModuleResponse:
    module = ModuleRegistryService(db).set_module_mode(
        current_user, tenant_id, module_code, payload
    )
    db.commit()
    return TenantModuleResponse.model_validate(module)
