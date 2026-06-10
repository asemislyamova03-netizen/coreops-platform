# Implementation Plan: Kindergarten seed/test sync

## Goal

Finish the approved small kindergarten template step by keeping the current
`kindergarten_basic` seed enrichment and syncing focused tests with the new
document placeholders and custom field count.

## Classification

Project: Flexity

Category: industry_template

Risk: medium

Branch: feature/kindergarten-basic-seed

## Scope

### Files to modify

    backend/app/modules/industry_templates/seed.py
    backend/tests/test_industry_templates.py
    backend/tests/test_documents.py
    backend/tests/test_mvp_scenario.py

### Files not to touch

    backend/alembic/
    backend/app/modules/documents/service.py
    frontend/
    deploy/
    Trailers
    Consulting Flask
    tenant customization code

## Steps

1. Keep the seed change limited to `kindergarten_basic` configuration.
2. Ensure document template field definitions match required placeholders.
3. Update focused tests for the new custom field count and document context.
4. Do not add migrations, frontend, dependencies, or catalog import logic.

## Tests/checks

    python -m compileall backend/app/modules/industry_templates backend/app/modules/documents
    pytest tests/test_industry_templates.py -q
    pytest tests/test_mvp_scenario.py -q

## Risks

- Existing tenants are not updated by seed changes.
- Catalog items remain stored in template settings only; automatic catalog item
  creation is a separate future plan.
- New required document placeholders must be supplied by callers until UI/default
  context support exists.

## Rollback

Revert the changes in the three scoped backend files and remove this plan file.

## Approval

Status: approved by user on 2026-06-09.
