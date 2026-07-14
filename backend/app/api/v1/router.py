from fastapi import APIRouter

from app.api.v1 import health
from app.api.v1.public_leads import router as public_leads_router
from app.modules.auth.routes import router as auth_router
from app.modules.catalog.routes import items_router as catalog_items_router
from app.modules.catalog.routes import price_lists_router as catalog_price_lists_router
from app.modules.catalog.routes import units_router as catalog_units_router
from app.modules.parties.routes import router as parties_router
from app.modules.industry_templates.routes import router as industry_templates_router
from app.modules.industry_templates.routes import tenant_template_router
from app.modules.module_registry.routes import registry_router, tenant_modules_router
from app.modules.subscriptions.routes import router as subscriptions_router
from app.modules.tenants.routes import router as tenants_router
from app.modules.workflows.routes import pipelines_router, work_items_router
from app.modules.documents.routes import documents_router, templates_router
from app.modules.accounting.routes import legal_entities_router, tax_profiles_router
from app.modules.finance.routes import finance_router, invoices_router, payments_router
from app.modules.integrations.routes import (
    connections_router,
    providers_router,
    references_router,
    sync_router,
    webhooks_router,
)
from app.modules.ai.routes import agents_router, proposals_router, tasks_router, usage_router
from app.modules.audit.routes import router as audit_router
from app.modules.marketing.routes import router as marketing_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(public_leads_router)
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(registry_router)
api_router.include_router(tenant_modules_router)
api_router.include_router(subscriptions_router)
api_router.include_router(industry_templates_router)
api_router.include_router(tenant_template_router)
api_router.include_router(pipelines_router)
api_router.include_router(work_items_router)
api_router.include_router(parties_router)
api_router.include_router(catalog_items_router)
api_router.include_router(catalog_price_lists_router)
api_router.include_router(catalog_units_router)
api_router.include_router(templates_router)
api_router.include_router(documents_router)
api_router.include_router(legal_entities_router)
api_router.include_router(tax_profiles_router)
api_router.include_router(invoices_router)
api_router.include_router(payments_router)
api_router.include_router(finance_router)
api_router.include_router(providers_router)
api_router.include_router(connections_router)
api_router.include_router(sync_router)
api_router.include_router(references_router)
api_router.include_router(webhooks_router)
api_router.include_router(agents_router)
api_router.include_router(tasks_router)
api_router.include_router(proposals_router)
api_router.include_router(usage_router)
api_router.include_router(audit_router)
api_router.include_router(marketing_router)
