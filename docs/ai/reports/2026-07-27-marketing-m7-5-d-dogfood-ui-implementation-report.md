# Report: M7.5-D Content Plan UI dogfood + plan item → topic

**Date:** 2026-07-27  
**Worktree:** `.worktrees/m7-5-d-dogfood-ui`  
**Branch:** `feature/marketing-m7-5-d-dogfood-ui`  
**Baseline:** `origin/main` @ `5348dcea9d28a704d3d5a680e4e4fae32889c6bd`  
**Category:** `universal_module` (Marketing Cabinet)  
**Slice:** M7.5-D only  
**Status:** implemented locally — **not committed** (await HQ)  
**VERDICT:** `M7_5_D_READY_FOR_COMMIT`

## Scope delivered

1. Marketing Cabinet nav + pages: Контент-планы (list/create, detail, prompt export, JSON import).
2. Prompt export UI via M7.5-C API — no AI/network model calls.
3. JSON import UI: paste + local file, preview, errors/warnings, unknown rubric mapping, commit after valid preview.
4. Plan lifecycle UI: approve/archive with confirmations; draft item CRUD/cancel; immutability after approve.
5. Backend `POST .../items/{item_id}/create-topic` + UI button / topic link / replay.
6. Topics: `MARKETING_RUBRIC_OPTIONS` removed as SoT fallback; empty → link to Rubrics.

## Migration

| Item | Value |
|------|-------|
| New migration | **none** |
| Alembic head | **`0028_mkt_content_plans`** (unchanged) |

## Backend action contract

`POST /api/v1/marketing/content-plans/{plan_id}/items/{item_id}/create-topic`  
RBAC: `require_marketing_settings_admin`

| Rule | Behavior |
|------|----------|
| Plan | must be `approved` |
| Item | must be `approved` (or already linked → replay) |
| Cancelled / draft / archived plan | 409 fail-closed |
| Cross-tenant | 404 |
| First create | 201; topic `status=approved`, `source=content_plan`, `rubric=code`; item → `topic_created` + `topic_id` |
| Replay | 200 + `replayed=true`; same topic; no duplicate |
| Packs | not created |
| Metadata | `plan_id`, `plan_item_id`, `rubric_id`, `channels`, editorial + `planned_date` |

Response: `{ item, topic, replayed }`

## UI routes / screens

| Path | Screen |
|------|--------|
| `/workspace/:slug/marketing/plans` | list + create draft |
| `/workspace/:slug/marketing/plans/prompt` | prompt export + copy |
| `/workspace/:slug/marketing/plans/import` | JSON paste/file → preview → commit |
| `/workspace/:slug/marketing/plans/:planId` | detail, items, approve/archive, create-topic |

Nav: `MarketingPageHeader` + dashboard quick links (existing cabinet, no new module).

## Dogfood sequence

1. Guide → activate  
2. Rubrics → create/seed active  
3. Планы → «Сформировать промпт» → copy  
4. External AI → JSON  
5. «Импорт JSON» → preview → map unknown codes if needed → commit  
6. Карточка плана → при необходимости правки draft → утвердить  
7. «Создать тему» на approved item  
8. Темы → «Взять в работу» (existing take → pack)  
9. Packs → preflight/approval (existing)

## Tests / build

| Check | Result |
|-------|--------|
| create-topic API | 5 passed |
| C + B + A regression | 36 passed (with create-topic suite in batch) |
| FE contract `marketingPlansPage.contract.test.ts` | OK |
| `marketingTaxonomy.test.ts` | ok |
| `tsc` (via `npm run build`) | GREEN |
| Vite build | GREEN |
| Alembic head | `0028` |
| compileall changed backend | OK |

## Security verdict

**PASS** — tenant-scoped create-topic; cross-tenant 404; no AI calls; no auto rubric; no pack/publish; import file stays local; fingerprint not shown as primary UX.

## Remaining gaps (non-blocking)

- Browser E2E against live tenant not run (local dogfood only).
- Detail page editorial fields beyond title/date/rubric/channels are viewable via API but create form is minimal (can PATCH later).
- Topic deep-link uses Topics list (not `?topicId=` filter) — acceptable for dogfood.
- `node_modules` installed locally in worktree for build only (gitignored).

## Intentionally not touched

- Dirty root / A/B/C worktrees  
- Migrations, AI APIs, publish adapters, M8-D3/D4/E  
- Deploy / commit / push  

## Next safe step

HQ review → separate approval to **commit** `feature/marketing-m7-5-d-dogfood-ui`.
