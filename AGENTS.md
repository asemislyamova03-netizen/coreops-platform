# Flexity Agent Instructions

You are working in the Flexity ecosystem.

## Current product direction

Flexity is the **single main product**.

Clinic App Flask, Consulting Flask, Trailers Flask and Kindergarten (inside Flexity) are **reference systems and validation directions** for business logic — not parallel product lines.

Rules:

- Study reference projects to extract reusable business patterns.
- Generalize shared logic into Flexity **universal modules**.
- Put industry-specific behavior into **industry templates/packages** (`kindergarten_basic`, `consulting_basic`, `clinic_basic`, `trailers_basic`).
- Put tenant/client-specific behavior into **tenant customization** — only with explicit approval.
- **Do not copy legacy Flask code directly** into Flexity.
- **Do not continue multiple Flask applications** as long-term parallel products.

Always read these files before planning or editing:

- docs/ai/PRODUCT_ARCHITECTURE.md
- docs/ai/ORCHESTRATION.md
- docs/ai/CHANGE_REQUESTS.md
- .cursor/rules/90-coordinator.mdc

## Mandatory workflow

Before code:

1. Classify the task:
   - platform_core
   - universal_module
   - industry_template
   - industry_package
   - tenant_customization
   - live_client_hotfix
   - migration_map
   - documentation_only
   - research_only

2. Identify project:
   - Flexity
   - Trailers (reference)
   - Consulting Flask (reference)
   - Clinic App Flask (reference)
   - Kindergarten inside Flexity (validation template/tenant)

3. Identify scope and forbidden zones.

4. Create a plan.

5. Wait for explicit approval before code.

## Architecture

    Flexity Core
    -> Universal modules
    -> Industry template / industry package
    -> Tenant customization

Tenant customization is a separate client-specific layer and must not be mixed into core or industry package code without an approved plan.

## Live / reference projects

Trailers, Consulting Flask and Clinic App Flask are live/reference projects.

Use them for read-only mapping, minimal approved hotfixes, and migration research — not as target architecture.

Do not:

- rewrite broadly;
- run deploy;
- run migrations;
- change Nginx/systemd;
- push;
- delete files;
- run destructive git commands.

## Safe commands

Allowed for read/check work:

- git status
- git status --short
- git diff
- git diff --stat
- git log --oneline -n 20
- python -m pytest
- python -m compileall
- ls
- pwd
- cat
- grep
- find

Explicit approval required:

- git reset
- git clean
- git push
- git pull
- git merge
- rm
- del
- flask db upgrade
- alembic upgrade
- pip install
- npm install
- docker compose down
- systemctl
- nginx
- ssh
- scp
- deploy scripts

## Current kindergarten rule

Do not start kindergarten code until orchestration setup is complete.

The next intended code step is limited to:

- backend/app/modules/industry_templates/seed.py only;
- add kindergarten_basic document body_template and fields;
- add guardian_relationship, start_date, base_price, currency;
- no migrations;
- no frontend;
- no dependencies.
