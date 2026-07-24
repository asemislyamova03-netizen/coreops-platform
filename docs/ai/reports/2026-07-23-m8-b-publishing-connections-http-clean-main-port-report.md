# M8-B Publishing Connections HTTP API — clean-main port report

Date: 2026-07-23
Branch: `feature/marketing-m8b-http-clean-main`
Base: `origin/main` @ `308b804`
Source checkpoint: `860d904`
Worktree: `.worktrees/marketing-m8b-http-clean`
Status: implemented locally; **no commit**, **no push**, **no deploy**

## Goal

Port M8-B Publishing Connections HTTP API onto clean main without migrations and without AWS vault.

## What was already on main (not re-ported)

- Domain model `MarketingPublishingConnection`
- Services `publishing_connections.py`, `publishing_secret_lifecycle.py`
- Storage profiles domain (M8-C2a)
- Secrets port: `SecretVaultPort`, `InMemorySecretVault`, `SecretPlaintext`, `SecretRef`
- Alembic: `0021_mkt_publishing_conn`, `0022_mkt_secret_binding`, `0023_mkt_storage_profiles` (+ process overlay / `0024`)
- `PublishingConnectionView` as service DTO only (no HTTP request DTOs)

## Files changed

### Created

1. `backend/app/modules/marketing/deps.py` — from `.ai_local/deps_860.py` / `860d904`
2. `backend/tests/test_marketing_publishing_connections_api.py` — from `.ai_local/test_api_860.py` / `860d904`
3. `docs/ai/reports/2026-07-23-m8-b-publishing-connections-http-clean-main-port-report.md` (this report)
4. `docs/ai/plans/2026-07-23-m8-b2-production-secret-provider-plan.md` — documentation-only M8-B2 plan

### Modified

1. `backend/app/core/permissions.py` — added `user_has_any_tenant_role` only
2. `backend/app/modules/marketing/schemas.py` — HTTP request DTOs + View docstring update
3. `backend/app/modules/marketing/routes.py` — merged publishing-connections endpoints

## Explicitly not changed

- Any Alembic migration / revision chain
- AWS Secrets Manager adapter
- Production vault code
- Telegram / destinations / publish execution / frontend
- Unrelated marketing or core modules

## Security invariants preserved

- Tenant isolation via service/repository scoped to `ctx.tenant.id`
- MEMBER: list/get only; mutations require OWNER/ADMIN (or same-provider staff)
- Production / staging / unknown env: vault DI fail-closed → `503 secret_vault_unavailable`
- InMemory vault only in allow-list `{test, testing, development, dev, local}`
- API responses expose `has_secret` only; never `secret_ref` or plaintext

## Adaptations vs `860d904`

- None material: deps copied as-is; schemas request DTOs match checkpoint; routes section merged into clean-main `routes.py` (~331 lines → append after media routes) without removing topics/packs/historical_publish handlers.

## Checks

- Scoped pytest: `tests/test_marketing_publishing_connections_api.py` + `tests/test_publishing_secret_lifecycle.py` → **38 passed** (57s; SAWarning on DROP cycle branches/tenants only)
- `git diff --check` → clean
- Alembic: **unchanged** (no paths under `backend/alembic` in `git status`)
- HEAD remains `308b804` on `feature/marketing-m8b-http-clean-main`; **no commit**

## Next safe step

- Reviewer pass on RBAC + redaction + fail-closed
- Separate HQ decision / M8-B2 for production secret provider (see plan)
- Commit only after explicit owner approval
