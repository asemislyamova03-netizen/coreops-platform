# Implementation Plan: Kindergarten catalog items import

## Goal

When an industry template is applied to a tenant, create real tenant catalog
items from `default_catalog_items` instead of only storing them in tenant
settings. This closes the current mismatch in `kindergarten_basic`: the template
defines subscriptions and fees, but the tenant catalog remains empty.

## Classification

Project: Flexity

Category: industry_template

Risk: medium

Branch: feature/kindergarten-basic-seed

## Scope

### Files to modify

    backend/app/modules/industry_templates/service.py
    backend/tests/test_industry_templates.py
    backend/tests/test_mvp_scenario.py

Optional only if a focused assertion is needed:

    backend/tests/test_catalog.py

### Files not to touch

    backend/app/modules/catalog/models.py
    backend/app/modules/catalog/routes.py
    backend/app/modules/catalog/schemas.py
    backend/alembic/
    frontend/
    deploy/
    Trailers
    Consulting Flask
    tenant customization code

## Steps

1. Add an internal helper on `IndustryTemplateService` that imports
   `template.default_catalog_items` for the target tenant.
2. Use `CatalogRepository.get_item_by_sku()` for idempotency.
3. Create only missing catalog items with:
   - tenant_id;
   - item_type;
   - name;
   - description if present;
   - sku;
   - base_price;
   - currency;
   - is_active defaulting to true;
   - empty `custom_fields_json`;
   - audit user ids from the applying user.
4. Call the helper from `apply_to_tenant()` after modules are enabled and before
   the response is returned.
5. Keep the public API response unchanged unless tests show a strong reason to
   expose a catalog count later.
6. Update focused tests to assert that `edu-monthly`, `registration-fee`, and
   `enrollment-fee` exist after template application and are not duplicated on a
   second apply.

## Tests/checks

Run from `backend/`:

    .\.venv\Scripts\python.exe -m compileall app/modules/industry_templates app/modules/catalog
    .\.venv\Scripts\python.exe -m pytest tests/test_industry_templates.py -q
    .\.venv\Scripts\python.exe -m pytest tests/test_mvp_scenario.py -q
    .\.venv\Scripts\python.exe -m pytest -q

## Risks

- Existing tenants are not backfilled automatically; only future apply-template
  calls create catalog items.
- If a tenant already has a catalog item with the same SKU, the template item is
  skipped and not overwritten.
- This does not create price lists or recurring billing. Those remain separate
  future plans.

## Rollback

Revert changes in the scoped service/test files. No migrations or data model
changes are involved.

## Approval

Status: approved by user on 2026-06-09.
