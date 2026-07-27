# Report: M7.5-A Marketing Guide + Rubrics (existing Cabinet)

**Date:** 2026-07-27
**Worktree:** `.worktrees/m7-5-upstream-plan`
**Branch:** `feature/marketing-m7-5-upstream-plan`
**Baseline HEAD:** `51ed8b8` (`origin/main`)
**Category:** `universal_module` (Marketing Cabinet)
**Slice:** M7.5-A only — Guide + tenant Rubrics directory
**Status:** implemented locally — **not committed** (await HQ)

## Architectural lock (HQ)

- **No** new Marketing Cabinet, module, app, or parallel UI.
- Existing M6/M7 Cabinet (`topics` / `packs` / `preflight` / `approval` + connections) remains the only surface.
- M7.5-A **extends** that Cabinet: Guide + Rubrics nav/settings + Topics form reads rubrics from tenant API.
- Topics / Packs / Approval are **not** duplicated.

## Goal

1. Persist tenant Marketing Guide (one active per tenant).
2. Persist tenant Rubric directory (permanent themes; not consumable topics).
3. Seed defaults **per tenant** via explicit admin POST (idempotent).
4. Demote FE `MARKETING_RUBRIC_OPTIONS` to legacy fallback; Topics select uses `GET /marketing/rubrics?status=active`.

## Classification

| Field | Value |
|-------|-------|
| Project | Flexity |
| Layer | universal_module (Marketing) |
| Risk | medium (schema + tenant isolation; no live publish) |

## Migration

| Item | Value |
|------|-------|
| Revision | `0027_mkt_guides_rubrics` |
| Parent | `0026_mkt_publish_destinations` |
| Tables | `marketing_guides`, `marketing_rubrics` |
| Topics/packs | **unchanged** (`topic.rubric` remains `String`, no FK) |
| Production migrate | **not run** — local/schema readiness only |

## API contracts (prefix `/api/v1/marketing`)

| Method | Path | RBAC |
|--------|------|------|
| GET | `/guides`, `/guides/active`, `/guides/{id}` | `require_module("marketing")` |
| POST/PATCH | `/guides`, `/guides/{id}`, `/guides/{id}/activate` | settings admin (= connection admin) |
| GET | `/rubrics`, `/rubrics/{id}` | `require_module("marketing")` |
| POST/PATCH/lifecycle | `/rubrics*`, `/rubrics/seed-defaults` | settings admin |

### Domain rules enforced

- One **active** Guide per tenant (partial unique + ordered supersede/activate flush).
- Rubric `code` unique per tenant; immutable after create.
- No hard delete (archive/deactivate).
- Topic create/update: inactive/archived directory code → 409; unknown/legacy free-text still OK.
- Cross-tenant guide/rubric id → **404**.
- Seed only current tenant; no global auto-seed.

## Frontend (same Cabinet)

| Surface | Change |
|---------|--------|
| `MarketingPageHeader` | Links to `/marketing/guide` and `/marketing/rubrics` |
| Routes | Existing workspace marketing routes + guide/rubrics |
| `MarketingGuidePage` | New page in same marketing folder |
| `MarketingRubricsPage` | New page + seed + lifecycle |
| `MarketingTopicsPage` | Rubric `<select>` from API active rubrics; legacy static fallback if empty |
| `marketingTaxonomy.ts` | SoT demoted to `LEGACY_RUBRIC_LABELS` |

URLs for topics/packs/approval **unchanged**.

## Files changed (summary)

### Backend
- `alembic/versions/20260727_0027_mkt_guides_rubrics.py` (new)
- `app/modules/marketing/{models,enums,exceptions,schemas,routes,deps,repository}.py`
- `app/modules/marketing/rubric_seed.py` (new)
- `app/modules/marketing/service/{guides,rubrics}.py` (new)
- `app/modules/marketing/service/topics.py` (selectable code guard)
- `app/modules/models.py` (register models)
- `tests/test_marketing_guides_rubrics_api.py` (new)
- `tests/test_migration_0027_mkt_guides_rubrics.py` (new)
- `tests/test_migration_0026_*.py`, `tests/test_marketing_migration.py` (head/tables)

### Frontend
- `platform-console/src/api/marketing.ts`, `types/marketing.ts`, `i18n/ruUi.ts`, `routes.tsx`
- `pages/workspace/marketing/Marketing{Guide,Rubrics}Page.tsx` (new)
- `MarketingPageHeader.tsx`, `MarketingTopicsPage.tsx`, `marketingTaxonomy.ts` (+ test)

### Docs
- Plan (pre-existing in worktree)
- This report

## Intentionally not touched

- Dirty Flexity root / `feature/marketing-m8-publish-bridge`
- M7.5-B/C/D (content plan, prompt, import)
- M8-D3 dry-run / adapters / Telegram
- AI provider calls
- Production alembic upgrade / deploy / commit / push

## Checks

| Check | Result |
|-------|--------|
| `pytest` guides/rubrics + migration 0026/0027 + marketing_migration | **17 passed** |
| `pytest tests/test_marketing_topics.py` | (run in same session) |
| `tsx marketingTaxonomy.test.ts` | **ok** |
| Security review (subagent) | **PASS** (tenant isolation + authz; no medium+) |

## Security verdict

**PASS** — tenant-scoped repo filters; mutate = settings admin; seed scoped to current tenant; no secrets vault changes; topics keep string rubric without FK.

## Gaps / follow-ups (non-blocking)

1. MEMBER → 403 mutate tests for guides/rubrics (parity with connections).
2. Optional `metadata_json` forbidden-key parity with guide `extra_json`.
3. Guide draft list UI (MVP loads **active** guide only; draft-without-activate still reachable via API).

## Verdict

**M7_5_A_READY_FOR_COMMIT**

Next HQ step: review diff in this worktree → explicit commit approval → then decide M7.5-B. M8-D3 remains **PAUSED**.
