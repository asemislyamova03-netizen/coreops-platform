# Implementation Plan: Marketing M7.5 — Guide + Rubrics + Content Plan prompt/import

**Date:** 2026-07-27
**Project:** Flexity / `coreops-platform`
**Category:** `universal_module` (Marketing Cabinet)
**Branch / worktree:** `feature/marketing-m7-5-upstream-plan` @ `.worktrees/m7-5-upstream-plan`
**Baseline:** `origin/main` @ `51ed8b8`
**Status:** **CLOSED** — M7.5 COMPLETE / STAGE DOGFOOD GREEN (`origin/main` `438e39c`). Canonical: `docs/ai/reports/2026-07-28-marketing-m7-5-closeout-report.md`
**HQ gate:** M8-D3 remains **PAUSED**. This plan does not authorize D3, publish, adapters, or AI API calls.
**Cabinet lock:** extend existing Marketing Cabinet only — no new cabinet/module/app/UI.

**Parents / evidence:**

| Doc | Role |
|-----|------|
| `docs/ai/plans/2026-07-03-marketing-content-cabinet-product-tz.md` | Product TZ (content plan, topics, settings) |
| `docs/ai/plans/2026-07-09-marketing-cabinet-data-model-draft.md` | Deferred `marketing_content_plan_items`; topics ≠ permanent themes |
| `docs/ai/plans/2026-07-09-marketing-cabinet-mvp-implementation-plan.md` | M6 deferred full content-plan calendar |
| `docs/ai/plans/2026-07-14-marketing-m7-product-plan.md` | Daily topic→pack dogfood (consumable topics) |
| `docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md` | Publish Bridge — **out of this slice** |
| Gap audit (session 2026-07-27) | `GAP_CONFIRMED` · `TOPICS_DIRECTORY_PARTIAL` |

---

## Goal

Enable Asem dogfood **upstream** of Publish Bridge:

```text
Marketing Guide
  → active tenant rubrics
  → content-plan prompt (export only)
  → structured JSON (external AI / human)
  → import preview + validation
  → Content Plan + plan items
  → create MarketingContentTopic (consumable idea)
  → take → pack → preflight → approval
```

**Domain lock (HQ):**

1. `MarketingContentTopic` = **consumable publication idea** (`draft → approved → used → pack`).
2. It is **not** the permanent themes/rubrics directory.
3. New tenant-scoped **`MarketingRubric`** (a.k.a. theme directory) = reusable catalog.
4. Frontend `MARKETING_RUBRIC_OPTIONS` must stop being source of truth; UI loads rubrics from API.

---

## Classification

| Field | Value |
|-------|-------|
| Project | Flexity |
| Layer | `universal_module` (Marketing) |
| Risk | medium (schema + tenant isolation; no live publish) |
| Required plan | this document |
| Code | **forbidden** until separate HQ approval per slice A→D |

---

## Scope

### In scope (M7.5)

- Marketing Guide (tenant brief) persistence + prompt **export** (no provider calls).
- Rubric directory CRUD/activate/archive + seed-as-data.
- Content Plan header + plan items persistence/API.
- JSON schema shared by prompt contract and importer.
- Import preview → commit (all-or-nothing unless HQ later allows partial).
- Materialize plan item → existing `MarketingContentTopic` (no pack auto-create on import).
- Console dogfood UI for Guide / Rubrics / Plan / Prompt export / Import.

### Out of scope

- M8-D3 dry-run / execute / adapters / Telegram.
- Real AI API calls from Flexity backend.
- Sources directory (unless a single free-text `guide.sources_notes` field).
- Agent Briefs directory.
- Campaign CRUD.
- Client-tenant rollout / billing / DNS / deploy / production migrations without gate.

### Files not to touch (global)

- Dirty root worktree `feature/marketing-m8-publish-bridge` and unrelated modules.
- Publish destinations / connections / vault / historical publish.
- Margosya, GHA publishers, landing content-packs as SoT.
- `docs/content/flexity-content-bank.md` as runtime SoT (may remain reference for seed text only).

---

## Exact entity model

### A. `marketing_guides` — Marketing Guide

**Cardinality:** **one active guide per tenant** (MVP). Optional `version` integer increments on replace; previous rows become `superseded` (soft history, no parallel active).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK → tenants CASCADE | indexed |
| `version` | INT NOT NULL | starts at 1 |
| `status` | ENUM | `draft` \| `active` \| `superseded` |
| `business_name` | VARCHAR(255) NOT NULL | |
| `business_summary` | TEXT NOT NULL | what the business does |
| `products_services` | TEXT NOT NULL | |
| `audiences` | TEXT NOT NULL | |
| `goals` | TEXT NOT NULL | period goals |
| `channels` | JSONB NOT NULL | e.g. `["telegram","instagram","threads","insights"]` |
| `default_frequency` | VARCHAR(64) NOT NULL | e.g. `daily`, `5_per_week` |
| `tone_rules` | TEXT NULL | |
| `constraints` | TEXT NULL | fail-closed / do-not-claim |
| `sources_notes` | TEXT NULL | free-text; **not** Sources directory |
| `extra_json` | JSONB NOT NULL default `{}` | non-secret only |
| audit / timestamps | standard mixins | |

**Unique partial:** one `(tenant_id)` where `status = 'active'`.

**Prompt build (no AI call):** deterministic markdown/text assembled in service from active guide + active rubrics + requested `period_start` / `period_end` / frequency / channel list + **embedded JSON schema** + hard rules (no auto-create rubrics; Russian/EN as HQ decides; calm tone).

---

### B. `marketing_rubrics` — permanent directory

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK CASCADE | |
| `code` | VARCHAR(64) NOT NULL | stable slug per tenant (`asem_column`, …) |
| `name` | VARCHAR(255) NOT NULL | display |
| `description` | TEXT NULL | |
| `content_instructions` | TEXT NULL | optional guidance for writers/AI |
| `status` | ENUM | `active` \| `inactive` \| `archived` |
| `sort_order` | INT NOT NULL default 0 | |
| `metadata_json` | JSONB NOT NULL `{}` | non-secret |
| audit / timestamps | | |

**Constraints:**

- `UNIQUE (tenant_id, code)`
- Never becomes `used`; reusable forever.
- Inactive/archived: hidden from prompt + new plan items; historical topic/pack rows remain readable.
- **No** cross-tenant reads.

**Seed:** on first Guide setup or explicit “seed default rubrics” action, insert editable rows from a **backend seed list** (same codes as today’s FE options). Seed is **data**, not FE hardcode. Re-seed must be idempotent by `(tenant_id, code)` and must not overwrite user-edited `name`/`description` unless `force=true` (HQ gate).

---

### C. Content Plan + items

#### `marketing_content_plans`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `title` | VARCHAR(512) NOT NULL | e.g. `2026-08 Flexity` |
| `period_start` | DATE NOT NULL | |
| `period_end` | DATE NOT NULL | |
| `status` | ENUM | `draft` \| `approved` \| `archived` |
| `guide_id` | UUID NULL FK → guides | snapshot link |
| `guide_version` | INT NULL | denormalized |
| `source` | VARCHAR(64) NOT NULL | `manual` \| `json_import` |
| `import_fingerprint` | VARCHAR(128) NULL | hash of committed JSON for replay guard |
| `metadata_json` | JSONB `{}` | |
| audit / timestamps | | |

#### `marketing_content_plan_items`

Aligns with data-model draft; extended for dogfood:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `plan_id` | UUID FK → plans CASCADE | |
| `planned_date` | DATE NOT NULL | |
| `rubric_id` | UUID FK → rubrics RESTRICT | **required** after validation |
| `working_title` | VARCHAR(512) NOT NULL | |
| `angle` | TEXT NULL | |
| `channels` | JSONB NOT NULL `[]` | planned channels |
| `format` | VARCHAR(64) NULL | e.g. `carousel`, `long_post` |
| `goal` | TEXT NULL | |
| `audience` | TEXT NULL | |
| `cta` | TEXT NULL | |
| `pain` | TEXT NULL | |
| `insight` | TEXT NULL | |
| `funnel_stage` | VARCHAR(64) NULL | |
| `notes` | TEXT NULL | |
| `status` | ENUM | `draft` \| `approved` \| `topic_created` \| `cancelled` |
| `topic_id` | UUID NULL FK → `marketing_content_topics` SET NULL | set when materialized |
| `external_line_key` | VARCHAR(128) NULL | stable id from JSON for dedupe |
| audit / timestamps | | |

**Indexes:** `(tenant_id, plan_id)`, `(tenant_id, planned_date)`, unique partial `(tenant_id, plan_id, external_line_key)` where key NOT NULL; unique optional `(tenant_id, plan_id, planned_date, working_title)` soft-check in service.

#### Link to existing consumable topic

When operator runs **«Create topic from item»** (slice D):

1. Require plan `approved` (or item `approved` — HQ default: **plan approved**).
2. Create `MarketingContentTopic` with:
   - `title` ← `working_title`
   - `rubric` ← **rubric.code** (string denormalized for M6/M7 compatibility)
   - `angle`, `recommended_channels` ← item
   - `status=draft` then operator approves topic as today
   - `metadata_json` editorial fields from item
   - `metadata_json.rubric_id` ← UUID (new optional key; non-breaking)
   - `metadata_json.plan_item_id` ← item id
3. Set `plan_item.topic_id`, `plan_item.status=topic_created`.
4. Existing **take → pack → preflight → approval** unchanged.

**Import never creates packs or publishes.**

---

### Compatibility with existing M6/M7

| Existing | Behavior in M7.5 |
|----------|------------------|
| `MarketingContentTopic.rubric` VARCHAR | **Keep**. Continue storing **rubric.code** string. Do **not** drop column in M7.5. |
| Packs with `topic_id` / historical packs | Untouched. |
| `pack.plan_item_id` nullable UUID without FK | Later migration may add FK to `marketing_content_plan_items` when table exists; **optional in M7.5-B** (prefer SET NULL FK once table lands). |
| FE `MARKETING_RUBRIC_OPTIONS` | Replace with API list; keep **fallback label map** only for unknown legacy codes (`marketingRubricLabel(code)` → code or archived name). |
| Soft rubric allow-list in M7-A | Soft-validate against **tenant active rubrics** instead of static list. |
| Content bank markdown | Not SoT; optional seed text source for first rubrics only. |

**No rewrite of topic lifecycle.** No automatic `mark_used` on rubric.

---

## Prompt contract (D / export)

`POST /marketing/content-plans/prompt-export` (or `/marketing/guides/active/prompt-export`):

**Inputs:** `period_start`, `period_end`, optional frequency override, optional channel subset.
**Output:** `{ prompt_text, schema_version, json_schema, guide_version, rubric_codes[], generated_at }`.

Prompt must instruct the model/human to return **only** JSON matching schema below.
**No** OpenAI/Anthropic/etc. calls inside Flexity in M7.5.

---

## JSON schema outline (prompt ≡ importer)

`schema_version`: `"m7.5.plan.v1"`

```json
{
  "schema_version": "m7.5.plan.v1",
  "period_start": "YYYY-MM-DD",
  "period_end": "YYYY-MM-DD",
  "title": "string",
  "items": [
    {
      "line_key": "string (stable unique within plan)",
      "date": "YYYY-MM-DD",
      "rubric_code": "string (must match tenant rubric.code)",
      "working_title": "string",
      "angle": "string|null",
      "channels": ["telegram", "instagram", "threads", "insights"],
      "format": "string|null",
      "goal": "string|null",
      "audience": "string|null",
      "cta": "string|null",
      "pain": "string|null",
      "insight": "string|null",
      "funnel_stage": "string|null",
      "notes": "string|null"
    }
  ]
}
```

**Importer rules:**

| Rule | Behavior |
|------|----------|
| Preview | Parse + validate; **no DB writes** |
| Unknown `rubric_code` | Item marked `unresolved_rubric`; **do not auto-create**; UI offers link-to-existing or create-rubric then re-preview |
| Inactive/archived rubric | Same as unknown for **new** imports |
| Duplicate `line_key` in file | Fail preview |
| Replay same `import_fingerprint` on tenant | Reject commit (`already_imported`) |
| Partial import | **Forbidden** in M7.5 — commit is all-or-nothing after all items resolve |
| Audit | `audit` event + optional `marketing_content_plan_import_logs` row (tenant, fingerprint, counts, actor) |
| Side effects | Creates plan + items only; **no topics/packs/publish** |

---

## API contracts (summary)

Base: `/api/v1/marketing` + module gate + tenant header.
RBAC: MEMBER+ read; OWNER/ADMIN (+ provider staff same company pattern as connections) mutate.

### Guide

| Method | Path | Notes |
|--------|------|-------|
| GET | `/guides/active` | 404 if none |
| GET | `/guides` | history |
| PUT/POST | `/guides` | create draft / activate (supersede previous) |
| POST | `/guides/active/prompt-export` | body: period + options |

### Rubrics

| Method | Path | Notes |
|--------|------|-------|
| GET | `/rubrics?status=` | |
| POST | `/rubrics` | |
| PATCH | `/rubrics/{id}` | |
| POST | `/rubrics/{id}/activate` | |
| POST | `/rubrics/{id}/deactivate` | |
| POST | `/rubrics/{id}/archive` | |
| POST | `/rubrics/seed-defaults` | idempotent editable seed |

### Content plans

| Method | Path | Notes |
|--------|------|-------|
| GET/POST | `/content-plans` | |
| GET/PATCH | `/content-plans/{id}` | |
| POST | `/content-plans/{id}/approve` | |
| GET | `/content-plans/{id}/items` | |
| PATCH | `/content-plans/{id}/items/{item_id}` | |
| POST | `/content-plans/import/preview` | body: raw JSON |
| POST | `/content-plans/import/commit` | body: preview_token or same JSON + resolved rubric map |
| POST | `/content-plans/{id}/items/{item_id}/create-topic` | materialize topic |

---

## UI contracts (slice D)

| Screen | Path (draft) | Behavior |
|--------|--------------|----------|
| Guide | `.../marketing/settings/guide` | form + save/activate + «Export prompt» |
| Rubrics | `.../marketing/settings/rubrics` | table CRUD / activate / archive / seed |
| Plans list | `.../marketing/plans` | list periods/statuses |
| Plan detail | `.../marketing/plans/:id` | items grid; approve; create-topic per row |
| Import | modal or `.../marketing/plans/import` | paste JSON → preview issues → resolve rubrics → commit |
| Topics page | existing | rubric `<select>` from `GET /rubrics?status=active` |

---

## Code slices

### M7.5-A — Guide + Rubrics

**Deliver:** models, migration(s), services, routes, tests; optional seed endpoint; **no** plan/import UI required.
**FE optional micro:** rubrics settings page OR API-only + Topics dropdown wired to API (prefer dropdown in A if small).

### M7.5-B — Content Plan persistence/API

**Deliver:** plans + items tables, CRUD/approve APIs, tests. No import yet.

### M7.5-C — Prompt export + JSON preview/import

**Deliver:** prompt builder, shared schema module, preview/commit, fingerprint, audit, unresolved-rubric flow. No pack creation.

### M7.5-D — UI dogfood + plan item → topic

**Deliver:** Guide/Rubrics/Plans/Import UI; `create-topic` from item; Topics page uses API rubrics; remove SoT role of `MARKETING_RUBRIC_OPTIONS` (keep legacy label helper only).

Each slice: separate HQ approval before code; no deploy without gate.

---

## Future files (expected allow-list)

### Backend (illustrative)

```text
backend/app/modules/marketing/models.py          # +Guide, Rubric, Plan, PlanItem [, ImportLog]
backend/app/modules/marketing/enums.py           # +statuses
backend/app/modules/marketing/schemas.py         # request/response DTOs
backend/app/modules/marketing/routes.py          # new routers
backend/app/modules/marketing/repository.py      # queries tenant-scoped
backend/app/modules/marketing/deps.py            # admin deps if needed
backend/app/modules/marketing/service/guides.py
backend/app/modules/marketing/service/rubrics.py
backend/app/modules/marketing/service/content_plans.py
backend/app/modules/marketing/service/content_plan_prompt.py
backend/app/modules/marketing/service/content_plan_import.py
backend/app/modules/marketing/content_plan_schema.py  # shared JSON schema + version
backend/alembic/versions/20260727_0027_mkt_guides_rubrics.py      # A
backend/alembic/versions/20260727_0028_mkt_content_plans.py       # B
backend/tests/test_marketing_guides_api.py
backend/tests/test_marketing_rubrics_api.py
backend/tests/test_marketing_content_plans_api.py
backend/tests/test_marketing_content_plan_import.py
backend/tests/test_migration_0027_*.py / 0028_*.py
```

### Frontend

```text
platform-console/src/api/marketing.ts            # new client calls
platform-console/src/types/marketing.ts
platform-console/src/pages/workspace/marketing/MarketingGuidePage.tsx
platform-console/src/pages/workspace/marketing/MarketingRubricsPage.tsx
platform-console/src/pages/workspace/marketing/MarketingPlansPage.tsx
platform-console/src/pages/workspace/marketing/MarketingPlanDetailPage.tsx
platform-console/src/pages/workspace/marketing/MarketingPlanImportModal.tsx
platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx  # rubric select from API
platform-console/src/pages/workspace/marketing/marketingTaxonomy.ts    # demote static options
platform-console/src/routes.tsx                  # nav routes
platform-console/src/components/layout/WorkspaceSidebar.tsx  # nav entries
```

### Docs (this plan only until approval)

```text
docs/ai/plans/2026-07-27-marketing-m7-5-upstream-guide-rubrics-content-plan-implementation-plan.md
```

---

## Migrations

| Rev (proposed) | Down | Contents |
|----------------|------|----------|
| `0027_mkt_guides_rubrics` | `0026_mkt_publish_destinations` | `marketing_guides`, `marketing_rubrics` + indexes/uniques |
| `0028_mkt_content_plans` | `0027_…` | `marketing_content_plans`, `marketing_content_plan_items` (+ optional import_logs); optional FK `packs.plan_item_id` → items |

**Rules:** additive only; no drop of `topics.rubric`; no data deletion; single Alembic head; revision ids ≤32 chars.

**Data backfill (optional, separate approval):** for `flexity-sales` only, seed rubrics from former FE codes; leave topics’ string `rubric` as-is.

---

## Tests / checks

| Area | Cases |
|------|-------|
| Tenant isolation | cross-tenant guide/rubric/plan → 404 |
| Rubric lifecycle | activate/deactivate/archive; archived not in prompt |
| Seed | idempotent; no overwrite without force |
| Prompt export | contains schema_version, active rubric codes, period |
| Import preview | unknown rubric unresolved; duplicate line_key fail |
| Import commit | all-or-nothing; fingerprint replay rejected; creates plan+items only |
| create-topic | sets topic.rubric=code, metadata plan_item_id; no pack |
| Regression | existing topics/packs/preflight/approval/take tests green |
| FE | taxonomy tests updated (API mock / no SoT static list) |
| `git diff --check` | clean on allow-list |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Confusing Topic vs Rubric in UI | Labels: «Рубрика (справочник)» vs «Тема публикации (идея)» |
| Legacy topic.rubric free text | Keep string; label helper; optional later migrate to rubric_id column |
| Operators expect AI inside Flexity | Explicit copy: export prompt → paste JSON |
| Import creates packs by mistake | Hard forbid in service; tests |
| Scope creep into M8-D3 | Approval gates; out-of-scope list |
| Dirty sibling worktrees | Implement only in this clean worktree |

---

## Rollback

- Per slice: revert PR / restore migration downgrade on disposable DB only.
- Production: no migrate until explicit gate; rollback = alembic downgrade + console dist restore pattern.
- Data: guides/rubrics/plans additive — safe to leave unused if feature flagged off (optional module flag later; not required MVP).

---

## Approval gates

| Gate | Phrase |
|------|--------|
| Plan accept | `APPROVED: M7.5 implementation plan` |
| Slice A code | `APPROVED: M7.5-A Guide + Rubrics` |
| Slice B code | `APPROVED: M7.5-B Content Plan API` |
| Slice C code | `APPROVED: M7.5-C Prompt + Import` |
| Slice D code | `APPROVED: M7.5-D UI dogfood` |
| Any migrate/deploy | separate explicit approval |

**M8-D3 remains paused** until HQ reopens after upstream dogfood readiness.

---

## Dogfood success criteria (Asem / flexity-sales)

1. Fill one active Marketing Guide.
2. See editable tenant rubrics (seed then edit).
3. Export prompt for a month.
4. Paste valid JSON → preview clean → commit plan.
5. See plan items; create topics from items.
6. Take → pack → preflight → approve as today.
7. No publish, no AI provider call from app.

---

## Steps (after approval — not now)

1. HQ approve this plan.
2. Implement **M7.5-A** only in this worktree.
3. Stop for review; then B → C → D with separate approvals.
4. Do not start M8-D3 from this branch.

---

## Approval

**Status:** waiting for approval

**Verdict of this documentation step:** **M7_5_PLAN_READY** (plan file only; no code).
