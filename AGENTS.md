# Flexity Agent Instructions

You are working in the Flexity ecosystem.

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
   - Trailers
   - Consulting Flask
   - Kindergarten inside Flexity

3. Identify scope and forbidden zones.

4. Create a plan.

5. Wait for explicit approval before code.

## Architecture

    Flexity Core
    -> Universal modules
    -> Industry template / industry package
    -> Tenant customization

Tenant customization is a separate client-specific layer and must not be mixed into core or industry package code without an approved plan.

## Live projects

Trailers and Consulting Flask are live/reference projects.

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
