import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exception_handlers import core_ops_error_handler
from app.core.exceptions import CoreOpsError
from app.modules.audit.middleware import install_audit_middleware
from app.modules.industry_templates.service import IndustryTemplateService
from app.modules.integrations.service import IntegrationService
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.subscriptions.service import SubscriptionService

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)

    if settings.seed_on_startup and "pytest" not in sys.modules:
        db = SessionLocal()
        try:
            ModuleRegistryService(db).seed_definitions()
            SubscriptionService(db).seed_catalog()
            IndustryTemplateService(db).seed_templates()
            IntegrationService(db).seed_providers()
        finally:
            db.close()

    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_exception_handler(CoreOpsError, core_ops_error_handler)
install_audit_middleware(app)

if settings.public_leads_allowed_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.public_leads_allowed_origin_list,
        allow_credentials=False,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": settings.app_name, "docs": "/docs"}
