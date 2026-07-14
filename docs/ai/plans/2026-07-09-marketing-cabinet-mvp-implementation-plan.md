# M5 — Marketing Cabinet MVP Implementation Plan

**Дата:** 2026-07-09  
**Проект:** Flexity / `coreops-platform`  
**Фаза:** M5 — implementation plan (M6 execution guide)  
**Категория:** `documentation_only`  
**Статус:** waiting for HQ approval — **код не менялся**

**Родительские документы:**
- [2026-07-03-marketing-content-cabinet-product-tz.md](./2026-07-03-marketing-content-cabinet-product-tz.md) (M0)
- [2026-07-09-margosya-to-cabinet-audit.md](../research/2026-07-09-margosya-to-cabinet-audit.md) (M1)
- [2026-07-09-marketing-cabinet-data-model-draft.md](./2026-07-09-marketing-cabinet-data-model-draft.md) (M2)
- [2026-07-09-marketing-cabinet-ui-wireframe-plan.md](./2026-07-09-marketing-cabinet-ui-wireframe-plan.md) (M3)
- [2026-07-09-marketing-cabinet-api-contract-draft.md](./2026-07-09-marketing-cabinet-api-contract-draft.md) (M4)

**HQ approval (this document):** documentation-only implementation plan. Код, migrations, deploy, Margosya — **только после отдельных gates ниже**.

---

## Task Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `universal_module` (marketing) |
| **Risk level** | medium |
| **Target execution** | M6 (after M5 HQ approval) |
| **Forbidden scope** | Margosya bot, Core public inbound, Booking / Clinic / Trailers, production deploy |

---

## 1. Goal

### 1.1 Цель M6

Создать **первый рабочий Marketing Cabinet MVP** внутри Flexity Console, чтобы Асем мог:

- выбирать темы и создавать publication packs в UI;
- редактировать тексты по 4 каналам;
- прикреплять media metadata;
- запускать preflight и approve;
- инициировать publish через **git export → существующие GitHub Actions**;
- видеть publish logs;
- вручную связывать контент с лидами в Core (`link-lead`).

**Заменить ежедневную работу через Telegram-команды** — постепенно; Margosya **не ломается** в M6.

### 1.2 Definition of done (M6 MVP)

| Criterion | Required |
|-----------|----------|
| `flexity-sales` tenant sees Marketing nav in Console | ✅ |
| Full pack lifecycle in UI (draft → preflight → approve → publish request) | ✅ |
| PostgreSQL = source of truth for pack metadata | ✅ |
| Git export produces compatible `landing/content/content-packs/` layout | ✅ |
| Publish does **not** auto-fire GHA without explicit user action + gate | ✅ |
| Margosya continues old filesystem flow unchanged | ✅ |
| Core CRM / public inbound unaffected | ✅ |
| Local pytest + console smoke pass | ✅ |

### 1.3 Not done in M6

- Margosya API cutover
- Production deploy
- Import of 16 packs (separate gate)
- `create-core-lead` endpoint
- Native Meta API publish from Marketing service

---

## 2. MVP scope

### 2.1 In scope

| Layer | Scope |
|-------|-------|
| **Backend** | New module `backend/app/modules/marketing/` |
| **Migration** | `0015_marketing_cabinet_mvp` (6 tables) |
| **API** | `/api/v1/marketing/*` per M4 |
| **Console** | `/workspace/:slug/marketing/*` P0 screens |
| **Module registry** | `marketing` module definition + enable for `flexity-sales` |
| **Git export** | Backend service writes pack files for GHA |
| **Import** | Planned separately; dry-run script optional behind gate |
| **Attribution** | Manual link to existing `party_id` / `work_item_id` |

### 2.2 MVP tables (6)

1. `marketing_content_topics`
2. `marketing_publication_packs`
3. `marketing_publication_texts`
4. `marketing_media_assets`
5. `marketing_publish_logs`
6. `marketing_lead_attribution`

### 2.3 P0 UI screens

| Screen | Route |
|--------|-------|
| Dashboard | `/workspace/:slug/marketing` |
| Topics | `.../marketing/topics` |
| Packs list | `.../marketing/packs` |
| Pack detail | `.../marketing/packs/:packId` |

**Pack detail tabs:** Texts, Media, Preflight, Approval, Publish, Logs.

### 2.4 P1 UI (same M6 wave if time, else M6.1)

| Screen | Route |
|--------|-------|
| Leads from Content | `.../marketing/leads` |

---

## 3. Out of scope

| Item | Reason |
|------|--------|
| Full Content Plan calendar | `marketing_content_plan_items` deferred |
| Scheduler / publish queue table | deferred |
| Reminders | deferred |
| Campaigns / offers full CRUD | deferred |
| Channel token management UI | secrets in env/GHA |
| Native Meta / Instagram APIs | GHA bridge MVP |
| WhatsApp Business API | out of scope |
| TikTok API | out of scope |
| Ads analytics | out of scope |
| Automatic demo provisioning | manual notes |
| `create-core-lead` endpoint | deferred; link-lead only |
| Second CRM kanban in Marketing | forbidden |
| Billing | out of scope |
| White-label | CR only |
| Client-owned storage | out of scope |
| Replacing Margosya immediately | parallel run |
| Object storage (S3) | git_path interim |
| Production deploy | separate gate |
| Changes to `margosya-os` | forbidden in M6 |
| Core `public-inbound-leads` | forbidden |
| Booking / Clinic / Trailers modules | forbidden |

---

## 4. Architecture

### 4.1 Layer diagram

```text
platform-console (React)
    → /api/v1/marketing/*  + X-Tenant-ID
        → marketing module (FastAPI routes)
            → MarketingService
                → repositories (SQLAlchemy)
                → PostgreSQL (SoT)
                → GitExportService (transition)
                    → landing/content/content-packs/
                    → landing/www/assets/social/
                → (optional) GHADispatchService — explicit gate only
            → Core services (read-only link validation)
                → PartyRepository / WorkflowService

Margosya (unchanged in M6)
    → filesystem helpers (legacy)

GitHub Actions (unchanged)
    → reads exported packs from repo
```

### 4.2 Backend module location

```text
backend/app/modules/marketing/
├── __init__.py
├── enums.py
├── exceptions.py
├── models.py
├── schemas.py
├── repository.py
├── service/
│   ├── __init__.py
│   ├── topics.py
│   ├── packs.py
│   ├── texts.py
│   ├── media.py
│   ├── preflight.py
│   ├── approval.py
│   ├── publish.py
│   ├── git_export.py
│   └── attribution.py
├── routes.py
└── seed.py                    # optional topic import helpers
```

### 4.3 Integration points (files to touch)

| File | Change |
|------|--------|
| `backend/app/api/v1/router.py` | include marketing router |
| `backend/app/modules/models.py` | import marketing models |
| `backend/app/modules/module_registry/seed.py` | add `marketing` definition |
| `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` | new migration |
| `backend/tests/test_marketing_*.py` | new tests |

### 4.4 Frontend location

```text
platform-console/src/
├── api/marketing.ts              # API client
├── pages/workspace/marketing/
│   ├── MarketingDashboardPage.tsx
│   ├── MarketingTopicsPage.tsx
│   ├── MarketingPacksPage.tsx
│   ├── MarketingPackDetailPage.tsx
│   └── MarketingLeadsPage.tsx    # P1
├── components/marketing/
│   ├── PackStatusBadges.tsx
│   ├── PackTextsTab.tsx
│   ├── PackMediaTab.tsx
│   ├── PackPreflightTab.tsx
│   ├── PackApprovalTab.tsx
│   ├── PackPublishTab.tsx
│   ├── PackLogsTab.tsx
│   └── TopicTable.tsx
├── routes.tsx                    # marketing routes
└── components/layout/WorkspaceSidebar.tsx  # nav item
```

### 4.5 Tenancy & module guard

| Mechanism | Implementation |
|-----------|----------------|
| Tenant | `X-Tenant-ID` header + `get_tenant_context` |
| Module | `Depends(require_module("marketing"))` on all routes |
| Row scope | all queries filter `tenant_id = ctx.tenant.id` |
| Cross-tenant FK | validate `party_id` / `work_item_id` same tenant |

### 4.6 PostgreSQL as SoT

- All pack/topic/log state in DB
- Git files are **export artifact**, not authoritative after M6 cutover for new packs
- `legacy_git_path` + `pack_dir_name` on pack for traceability

### 4.7 Margosya integration

**M6:** no Margosya changes.  
**Post-M6:** Margosya calls same API (M4 §14) after separate cutover gate.

---

## 5. Data model implementation

### 5.1 Migration

| Field | Value |
|-------|-------|
| Revision ID | `0015` (next after `0014_core_branches_baseline`) |
| Filename | `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` |
| Revises | `0014` |

### 5.2 Table specifications

#### `marketing_content_topics`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK → tenants | NOT NULL, indexed |
| `legacy_topic_id` | VARCHAR(64) | nullable |
| `title` | VARCHAR(512) | NOT NULL |
| `rubric` | VARCHAR(128) | NOT NULL |
| `angle` | TEXT | |
| `source` | VARCHAR(64) | default `manual` |
| `status` | ENUM | draft, approved, used, archived |
| `priority` | INT | default 0 |
| `reusable` | BOOL | default false |
| `recommended_channels` | JSONB | default `[]` |
| `used_count` | INT | default 0 |
| `last_used_at` | TIMESTAMPTZ | nullable |
| `slug_hint` | VARCHAR(128) | nullable |
| `metadata_json` | JSONB | default `{}` |
| audit + timestamps | | AuditUserMixin pattern |

**Indexes:** `(tenant_id, status)`, `(tenant_id, legacy_topic_id)`  
**Unique:** `(tenant_id, legacy_topic_id)` WHERE legacy_topic_id IS NOT NULL

#### `marketing_publication_packs`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | indexed |
| `campaign_id` | UUID | nullable, no FK MVP |
| `topic_id` | UUID FK → topics | nullable, SET NULL |
| `plan_item_id` | UUID | nullable, no FK MVP |
| `slug` | VARCHAR(128) | NOT NULL |
| `pack_dir_name` | VARCHAR(255) | nullable |
| `title` | VARCHAR(512) | NOT NULL |
| `planned_date` | DATE | NOT NULL |
| `status` | ENUM | see M2 §5.3 |
| `preflight_status` | ENUM | not_run, passed, failed |
| `preflight_report_json` | JSONB | default `{}` |
| `preflight_at` | TIMESTAMPTZ | |
| `approval_status` | ENUM | draft, pending, approved, rejected |
| `approved_at` | TIMESTAMPTZ | |
| `approved_by_user_id` | UUID | |
| `publish_status` | ENUM | not_started, partial, published, failed |
| `source` | VARCHAR(64) | console, margosya, import |
| `channel_config_json` | JSONB | default `{}` |
| `legacy_git_path` | VARCHAR(512) | |
| `metadata_json` | JSONB | default `{}` |

**Unique:** `(tenant_id, slug)`  
**Indexes:** `(tenant_id, status)`, `(tenant_id, planned_date)`, `(tenant_id, approval_status)`, `(tenant_id, publish_status)`

#### `marketing_publication_texts`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `pack_id` | UUID FK → packs | CASCADE |
| `channel` | ENUM | telegram, instagram, threads, insights |
| `text` | TEXT | default `''` |
| `status` | ENUM | draft, ready, approved |
| `version` | INT | default 1 |
| `char_count` | INT | denormalized |

**Unique:** `(pack_id, channel)` — **one current row per channel** (version increments in place)  
**Index:** `(tenant_id, pack_id)`

#### `marketing_media_assets`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `pack_id` | UUID FK | SET NULL |
| `role` | VARCHAR(64) | instagram_feed |
| `file_name` | VARCHAR(255) | |
| `mime_type` | VARCHAR(128) | |
| `storage_provider` | VARCHAR(32) | git_path |
| `storage_key` | VARCHAR(1024) | |
| `public_url` | VARCHAR(1024) | |
| `preview_url` | VARCHAR(1024) | nullable |
| `width`, `height` | INT | |
| `alt_text` | VARCHAR(512) | |
| `status` | ENUM | pending, stored, failed, archived |
| `metadata_json` | JSONB | |

**Index:** `(tenant_id, pack_id)`

#### `marketing_publish_logs`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `pack_id` | UUID FK | CASCADE |
| `queue_item_id` | UUID | nullable, no FK MVP |
| `channel` | VARCHAR(64) | |
| `action` | VARCHAR(64) | approved, published, failed, … |
| `status` | VARCHAR(64) | success, failed |
| `external_url` | VARCHAR(1024) | |
| `external_post_id` | VARCHAR(255) | |
| `published_at` | TIMESTAMPTZ | |
| `error_message` | TEXT | |
| `actor` | VARCHAR(64) | |
| `metadata_json` | JSONB | |
| `created_at` | TIMESTAMPTZ | append-only |

**Indexes:** `(tenant_id, pack_id)`, `(tenant_id, created_at DESC)`

#### `marketing_lead_attribution`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `party_id` | UUID FK → parties | nullable, SET NULL |
| `work_item_id` | UUID FK → work_items | nullable, SET NULL |
| `campaign_id` | UUID | nullable |
| `pack_id` | UUID FK → packs | nullable, SET NULL |
| `topic_id` | UUID FK → topics | nullable, SET NULL |
| `channel` | VARCHAR(64) | |
| `source_type` | ENUM | first_touch, assisted, converted |
| `source_url` | VARCHAR(1024) | |
| `content_slug` | VARCHAR(128) | |
| `utm_json` | JSONB | |
| `first_touch_at` | TIMESTAMPTZ | |
| `last_touch_at` | TIMESTAMPTZ | |
| `notes` | TEXT | |

**Indexes:** `(tenant_id, work_item_id)`, `(tenant_id, pack_id)`

### 5.3 Versioning decision

**Decision:** one row per `(pack_id, channel)`; `version` increments on each PUT.  
No history table in MVP.

### 5.4 ORM registration

Add to `backend/app/modules/models.py`:

```python
from app.modules.marketing.models import (  # noqa: F401
    MarketingContentTopic,
    MarketingPublicationPack,
    MarketingPublicationText,
    MarketingMediaAsset,
    MarketingPublishLog,
    MarketingLeadAttribution,
)
```

---

## 6. Backend slices

### 6.1 Execution order

```text
M6-BE1 → M6-BE2 → M6-BE3 → M6-BE4 → M6-BE5 → M6-BE6 → M6-BE7
```

Each slice: code + tests + local verify before next slice.

---

### M6-BE1 — Module skeleton

**Goal:** empty module boots; migration applies; router mounts.

| File | Action |
|------|--------|
| `backend/app/modules/marketing/__init__.py` | create |
| `backend/app/modules/marketing/enums.py` | create all status enums |
| `backend/app/modules/marketing/models.py` | create 6 models |
| `backend/app/modules/marketing/schemas.py` | stub response models |
| `backend/app/modules/marketing/repository.py` | base CRUD |
| `backend/app/modules/marketing/routes.py` | health `GET /marketing/health` |
| `backend/app/modules/marketing/exceptions.py` | MarketingError codes |
| `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` | create |
| `backend/app/api/v1/router.py` | include router |
| `backend/app/modules/models.py` | import models |
| `backend/app/modules/module_registry/seed.py` | add `marketing` module |
| `backend/tests/test_marketing_migration.py` | migration smoke |

**Module registry seed entry (draft):**

```python
{
    "code": "marketing",
    "name": "Marketing Cabinet",
    "description": "Content topics, packs, publish workflow",
    "dependencies_json": {"required": ["parties"]},
}
```

Enable for `flexity-sales` via existing tenant module seed path (document exact seed file in M6 execution).

**Tests:** migration up/down on sqlite test db; `GET /marketing/health` 200 with module enabled.

**Gate:** M6-BE approval before merge.

---

### M6-BE2 — Topics API

**Endpoints:**
- `GET /marketing/topics`
- `POST /marketing/topics`
- `GET /marketing/topics/{id}`
- `PATCH /marketing/topics/{id}`
- `GET /marketing/topics/suggested`
- `POST /marketing/topics/{id}/take`
- `POST /marketing/topics/{id}/archive`
- `POST /marketing/topics/{id}/mark-used`
- `POST /marketing/topics/import-content-bank` (admin; reads `docs/content/flexity-content-bank.md`)

**Service:** `service/topics.py` — selector logic ported from Margosya `content_bank_selector` (read-only reference, **do not import margosya package**).

**Fail-closed:**
- `no_approved_topics` on suggested when empty
- `topic_not_approved` on take
- basic duplicate check before take

**Files:**
- `service/topics.py`
- extend `schemas.py`, `repository.py`, `routes.py`
- `backend/tests/test_marketing_topics.py`

---

### M6-BE3 — Packs API

**Endpoints:**
- `GET /marketing/packs`
- `POST /marketing/packs`
- `GET /marketing/packs/{id}`
- `PATCH /marketing/packs/{id}`
- `GET /marketing/packs/last`
- `GET /marketing/dashboard` (aggregates packs + logs)

**Service:** `service/packs.py` — status machine; slug uniqueness; `pack_dir_name` generation `{date}-{slug}`.

**On create:** empty text rows for 4 channels.

**Files:**
- `service/packs.py`
- `backend/tests/test_marketing_packs.py`

---

### M6-BE4 — Texts & media API

**Endpoints:**
- `GET /marketing/packs/{id}/texts`
- `PUT /marketing/packs/{id}/texts/{channel}`
- `POST /marketing/packs/{id}/media`
- `GET /marketing/packs/{id}/media`
- `PATCH /marketing/media/{asset_id}`

**Texts:** update `char_count`; if pack `approval_status=approved` → reset approval (M4 rule).

**Media MVP:**
- accept `storage_key` + `public_url` register OR file upload to repo-relative path
- reuse PIL normalize logic — **copy minimal helper into marketing module** (do not depend on margosya-os)
- validate mime PNG/JPG/WebP; record width/height

**Files:**
- `service/texts.py`, `service/media.py`
- `backend/tests/test_marketing_texts.py`
- `backend/tests/test_marketing_media.py`

---

### M6-BE5 — Preflight & approval

**Endpoints:**
- `POST /marketing/packs/{id}/preflight`
- `POST /marketing/packs/{id}/approve`
- `POST /marketing/packs/{id}/reject`

**Service:** `service/preflight.py` — checklist from M4 §9; optional subprocess dry-run to existing Flexity scripts (read-only, no network in unit tests).

**Service:** `service/approval.py` — gates; audit events.

**Rules:**
- approve blocked if `preflight_status != passed`
- reject → `approval_status=rejected`, `status=draft`
- audit via `AuditRecorder`

**Files:**
- `service/preflight.py`, `service/approval.py`
- `backend/tests/test_marketing_preflight.py`
- `backend/tests/test_marketing_approval.py`

---

### M6-BE6 — Publish logs + git export bridge

**Endpoints:**
- `GET /marketing/packs/{id}/logs`
- `GET /marketing/publish-logs`
- `POST /marketing/packs/{id}/publish`

**Service:** `service/publish.py` + `service/git_export.py`

**Publish flow (MVP):**

```text
1. Validate approval_status = approved
2. GitExportService.export_pack(pack_id) → writes files
3. Append publish_log action=publish_requested
4. If user confirmed live dispatch (explicit flag in request):
     GHADispatchService.dispatch_telegram_instagram(slug)
   ELSE:
     return exported + "dispatch skipped" (default safe)
5. On dispatch result → append success/failed logs
6. Update publish_status / channel state on pack
```

**Default MVP:** `dispatch_live=false` unless request body `{ "dispatch_live": true }` — **double confirmation** in UI.

**Git export output** (per M4 §15):

```text
landing/content/content-packs/{pack_dir_name}/
  pack.yml
  telegram.md
  instagram.md
  threads.md
  insights.md
  instagram.yml
  visual.yml
  publish_log.yml   # merged from DB logs
```

**GHADispatch:** wrap existing pattern from `margosya-os/content_ops_publish.py` logic — reimplement minimal GitHub workflow dispatch in Flexity (read env `GITHUB_TOKEN` from settings, not repo).

**Gate:** **M6-bridge approval** required before enabling `dispatch_live` even locally.

**Files:**
- `service/git_export.py`, `service/publish.py`
- `backend/tests/test_marketing_git_export.py`
- `backend/tests/test_marketing_publish.py`

---

### M6-BE7 — Attribution link

**Endpoints:**
- `GET /marketing/lead-attribution`
- `POST /marketing/lead-attribution`
- `PATCH /marketing/lead-attribution/{id}`
- `POST /marketing/packs/{id}/link-lead`

**Service:** `service/attribution.py`

**Rules:**
- validate `work_item_id` / `party_id` exist in same tenant
- optional: write `work_items.custom_fields_json.marketing` bridge
- **no** `create-core-lead`

**Files:**
- `service/attribution.py`
- `backend/tests/test_marketing_attribution.py`

---

## 7. Frontend slices

### 7.1 Execution order

```text
M6-FE1 → M6-FE2 → M6-FE3 → M6-FE4 → M6-FE5 → M6-FE6
```

Can start **M6-FE1** in parallel after **M6-BE2** (topics API ready).

---

### M6-FE1 — Route / nav shell

| File | Action |
|------|--------|
| `platform-console/src/routes.tsx` | add marketing routes |
| `platform-console/src/components/layout/WorkspaceSidebar.tsx` | «Маркетинг» nav group |
| `platform-console/src/api/marketing.ts` | API client skeleton |
| `platform-console/src/pages/workspace/marketing/MarketingPlaceholderPage.tsx` | temporary |

**Routes:**
- `marketing` → Dashboard (placeholder OK initially)
- `marketing/topics`
- `marketing/packs`
- `marketing/packs/:packId`

**Gate:** M6-FE approval.

---

### M6-FE2 — Dashboard

| File | Action |
|------|--------|
| `MarketingDashboardPage.tsx` | KPI cards + widgets |
| `components/marketing/DashboardWidgets.tsx` | |

**API:** `GET /marketing/dashboard`

**Widgets:** today content, pending approval, failed publish, drafts, latest publications.

---

### M6-FE3 — Topics screen

| File | Action |
|------|--------|
| `MarketingTopicsPage.tsx` | |
| `components/marketing/TopicTable.tsx` | |
| `components/marketing/CreateTopicModal.tsx` | |

**Actions:** list, filter, create, take topic → navigate to pack detail.

---

### M6-FE4 — Packs list

| File | Action |
|------|--------|
| `MarketingPacksPage.tsx` | |

**Filters:** status, approval, publish, date, search.

---

### M6-FE5 — Pack detail (main)

| File | Action |
|------|--------|
| `MarketingPackDetailPage.tsx` | header + tabs |
| `components/marketing/PackStatusBadges.tsx` | |
| `components/marketing/PackTextsTab.tsx` | 4 textareas |
| `components/marketing/PackMediaTab.tsx` | preview + register path |
| `components/marketing/PackPreflightTab.tsx` | run + checklist |
| `components/marketing/PackApprovalTab.tsx` | approve/reject |
| `components/marketing/PackPublishTab.tsx` | export + optional dispatch checkbox |
| `components/marketing/PackLogsTab.tsx` | table |

**Header actions:** Preflight, Approve, Publish (disabled per gates).

**Publish tab MVP:**
- Button «Export to git» (always)
- Checkbox «Запустить live publish (GitHub Actions)» — off by default
- Confirm modal with fail-closed text

---

### M6-FE6 — Lead attribution (P1)

| File | Action |
|------|--------|
| `MarketingLeadsPage.tsx` | |
| `components/marketing/LinkLeadModal.tsx` | work_item_id picker |

**Link to Core:** `<Link to={/workspace/${slug}/crm}>`.

---

## 8. Margosya bridge plan

### 8.1 M6 policy

| Rule | Detail |
|------|--------|
| **Do not modify** | `margosya-os` code |
| **Do not disable** | existing filesystem flow |
| **Do not cut over** | Margosya to API in M6 |
| Parallel run | new packs can be created in Console OR Margosya until cutover gate |

### 8.2 Future bridge (post-M6)

| Phase | Action |
|-------|--------|
| M7-MG1 | Issue Margosya service token; read-only API (topics, pack status) |
| M7-MG2 | Write path: take topic, PUT texts, POST media via API |
| M7-MG3 | Preflight/approve/publish via API |
| M7-MG4 | Disable filesystem writes in Margosya behind feature flag |
| M7-MG5 | Reminders webhook |

### 8.3 Compatibility during parallel run

**Risk:** same slug created in both systems.

**Mitigation until cutover:**
- unique `(tenant_id, slug)` in DB
- Margosya continues git-first; Console DB-first + export
- document: «one pack per day per slug» operational rule
- import gate reconciles legacy git packs

---

## 9. Git export bridge

### 9.1 Current git pack format (reference)

From M1 audit — per `landing/content/content-packs/<pack_dir_name>/`:

| File | Purpose |
|------|---------|
| `pack.yml` | metadata, content_bank.topic_id, publish.* status |
| `telegram.md` | post body |
| `instagram.md` | caption |
| `threads.md` | threads text |
| `insights.md` | article |
| `instagram.yml` | IG post config |
| `visual.yml` | visual brief |
| `publish_log.yml` | events[] |

### 9.2 Export service contract

```python
class GitExportService:
    def export_pack(self, pack_id: UUID, *, flexity_root: Path) -> ExportResult:
        """Write/update pack directory from DB SoT."""
```

**Rules:**
- Only backend service writes files — **never from UI directly**
- Atomic write: temp dir → rename
- Never delete unrelated packs
- `pack_dir_name` default: `{planned_date}-{slug}`
- Media: copy or symlink to `landing/www/assets/social/{pack_dir_name}/instagram-feed.png`

### 9.3 `pack.yml` mapping

```yaml
date: <planned_date>
topic: <title>
slug: <slug>
status: <approval mapping>
content_bank:
  topic_id: <legacy_topic_id>
publish:
  telegram:
    enabled: true
    status: approved   # if approved
```

### 9.4 Publish log compatibility

Export merges DB `marketing_publish_logs` → `publish_log.yml` `events[]` format (M1 §8.4).

### 9.5 Dual SoT risk

| Phase | SoT | Git role |
|-------|-----|----------|
| M6 start | DB for Console-created packs | export target |
| Margosya packs | git (unchanged) | still SoT until import |
| After import | DB | export mirror |

**Rollback:** disable export; delete exported dirs only if created by export (track `source=console`).

---

## 10. Import existing packs

### 10.1 Policy

**Separate gate:** `M6-import approval` — **not** part of default M6.

### 10.2 Importer design

| Step | Action |
|------|--------|
| 1 | Script `backend/scripts/marketing_import_git_packs.py` |
| 2 | Dry-run mode (default): print would-import rows |
| 3 | Read `landing/content/content-packs/*/pack.yml` |
| 4 | Map → DB entities per M2 §8.1 |
| 5 | Skip if `(tenant_id, slug)` exists |
| 6 | Preserve `publish_log.yml` events |
| 7 | Register media paths without moving files |
| 8 | Import topics from `content_bank.topic_id` if missing |

### 10.3 Count

16 pack directories (M1) — import in batches of 5 with manual review.

### 10.4 Safety

- **No overwrite** of existing DB rows
- **No delete** of git files
- **No publish** during import
- HQ sign-off on dry-run report before `--apply`

---

## 11. Tests

### 11.1 Backend

| Test file | Coverage |
|-----------|----------|
| `test_marketing_migration.py` | tables, indexes, unique constraints |
| `test_marketing_topics.py` | CRUD, suggested, take, fail-closed |
| `test_marketing_packs.py` | lifecycle, slug unique, tenant isolation |
| `test_marketing_texts.py` | PUT channel, approval invalidation |
| `test_marketing_media.py` | register metadata, validation |
| `test_marketing_preflight.py` | pass/fail scenarios |
| `test_marketing_approval.py` | gates, audit called |
| `test_marketing_git_export.py` | file layout, pack.yml shape |
| `test_marketing_publish.py` | dispatch_live=false default |
| `test_marketing_attribution.py` | link-lead, tenant FK |
| `test_marketing_tenant_isolation.py` | cross-tenant 403 |

**Run:**

```bash
cd backend && python -m pytest tests/test_marketing_*.py -q
```

### 11.2 Frontend

| Check | Command |
|-------|---------|
| Build | `cd platform-console && npm run build` |
| Route smoke | manual or playwright later |
| Pack detail flow | manual smoke script in M6 closeout |

### 11.3 Regression (must pass)

| Area | Check |
|------|-------|
| Core CRM | existing `test_workflows*.py`, CRM smoke |
| Public inbound | no changes to `public_leads.py` |
| Margosya | no repo changes |
| Existing git packs | untouched without import gate |
| Module disabled tenant | marketing routes 403 |

---

## 12. Security

| Control | Implementation |
|---------|----------------|
| Tenant isolation | all queries + FK validation |
| `require_module("marketing")` | all routes |
| No secrets in API response | channel tokens never returned |
| Publish without approve | 409 `approval_required` |
| Preflight before approve | 409 `preflight_failed` |
| Audit | approve, publish, attribution create |
| `dispatch_live` default false | prevent accidental GHA |
| File export path traversal | validate `slug`, `pack_dir_name` |
| Upload size limit | 10MB MVP |
| Margosya service token | design only in M6; implement M7 |

---

## 13. Deployment plan

### 13.1 Phases

| Phase | Environment | Approval |
|-------|-------------|----------|
| D0 | local dev | M6-BE/FE gates |
| D1 | local alembic upgrade | developer |
| D2 | local console smoke | developer |
| D3 | staging server | **Gate server deploy** |
| D4 | production | **separate HQ approval** |

### 13.2 M6 default

**Local/staging only.** No production deploy.

### 13.3 Staging checklist (when approved)

1. `alembic upgrade head` on staging DB
2. Enable `marketing` module for `flexity-sales`
3. Import content bank topics (admin endpoint)
4. Create test pack → export → verify files
5. Optional: `dispatch_live=true` on test pack only
6. Verify Margosya still works on unrelated slug

### 13.4 Rollback

1. Disable `marketing` module for tenant
2. `alembic downgrade -1` (if no production data)
3. Remove exported test pack dirs from git (manual commit revert)

---

## 14. Approval gates

| Gate | ID | Approves | Blocks |
|------|-----|----------|--------|
| Implementation plan | **M5** | This document | any M6 code |
| Backend slice start | **M6-BE** | BE1–BE7 local | FE depending on API |
| Frontend slice start | **M6-FE** | FE1–FE6 local | — |
| Git export + publish dispatch | **M6-bridge** | BE6 `dispatch_live` | live GHA calls |
| Import 16 packs | **M6-import** | importer `--apply` | DB writes from git |
| Staging deploy | **server deploy** | alembic on server | — |
| Production deploy | **production** | go-live | — |
| Margosya API cutover | **Margosya cutover** | bot changes | filesystem SoT off |

**Rule:** each gate requires explicit HQ message «approved».

---

## 15. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| 1 | Scope creep | high | delay | strict M6 slices; P1 leads optional |
| 2 | Dual SoT DB+git | high | confusion | export only from DB; import gate |
| 3 | Break Margosya | medium | high | no margosya changes in M6 |
| 4 | Export format mismatch | medium | publish fail | git_export unit tests; manual diff |
| 5 | Tenant leakage | low | critical | isolation tests |
| 6 | Premature publish automation | medium | high | `dispatch_live=false` default |
| 7 | Pack status complexity | medium | bugs | orthogonal sub-statuses |
| 8 | UI too large | medium | delay | FE waves; pack detail last |
| 9 | GHA token on server | medium | security | env only; never commit |
| 10 | Approval invalidation UX | low | user error | clear badges + tooltips |

---

## 16. Recommended first implementation slice

### 16.1 Primary recommendation (backend-first)

**After M5 HQ approval, start with:**

```text
M6-BE1 + M6-BE2 only (local)
```

| Deliverable | |
|-------------|--|
| Migration `0015` | 6 tables |
| Module `marketing` registered | |
| Topics API full | |
| Tests green | |
| No UI | |
| No publish | |
| No git export | |
| No Margosya changes | |

**Verify:** `pytest test_marketing_*`; `curl GET /api/v1/marketing/topics` with `X-Tenant-ID`.

### 16.2 Alternative (parallel FE shell)

If HQ wants visible progress:

```text
M6-BE1 + M6-FE1 in parallel
```

FE shows placeholder + Topics list once BE2 ready.

### 16.3 Not recommended as first slice

- ❌ M6-BE6 git export (too early)
- ❌ Full pack detail UI before BE3
- ❌ Import 16 packs
- ❌ Margosya bridge

---

## 17. Files summary

### 17.1 Files to create (M6 full)

**Backend (~20 files):**

```text
backend/app/modules/marketing/**
backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py
backend/tests/test_marketing_*.py
backend/scripts/marketing_import_git_packs.py   # import gate only
```

**Frontend (~15 files):**

```text
platform-console/src/api/marketing.ts
platform-console/src/pages/workspace/marketing/**
platform-console/src/components/marketing/**
```

### 17.2 Files to modify (M6)

```text
backend/app/api/v1/router.py
backend/app/modules/models.py
backend/app/modules/module_registry/seed.py
platform-console/src/routes.tsx
platform-console/src/components/layout/WorkspaceSidebar.tsx
```

### 17.3 Files NOT to touch

```text
margosya-os/**
backend/app/api/v1/public_leads.py
backend/app/modules/booking/**
backend/app/modules/branches/**
backend/scripts/content/publish_*.py      # read-only reference
.github/workflows/telegram-publish.yml  # no change M6
landing/content/content-packs/**          # except export writes (gate)
```

---

## 18. HQ summary

### 1. Path

```text
M0 ✅ → M1 ✅ → M2 ✅ → M3 ✅ → M4 ✅ → M5 (this doc) → M6 code (gated slices)
```

### 2. MVP scope

Backend `marketing` module + 6 tables + `/api/v1/marketing/*` + Console P0 UI + git export bridge + link-lead attribution.

### 3. Tables

`marketing_content_topics`, `marketing_publication_packs`, `marketing_publication_texts`, `marketing_media_assets`, `marketing_publish_logs`, `marketing_lead_attribution`.

### 4. Backend slices

BE1 skeleton → BE2 topics → BE3 packs → BE4 texts/media → BE5 preflight/approval → BE6 publish+git export → BE7 attribution.

### 5. Frontend slices

FE1 nav → FE2 dashboard → FE3 topics → FE4 packs list → FE5 pack detail → FE6 leads (P1).

### 6. Git bridge approach

DB SoT → `GitExportService` → `landing/content/content-packs/` → existing GHA; `dispatch_live=false` by default.

### 7. Margosya impact

**None in M6.** Parallel run. API cutover = separate Margosya gate.

### 8. Import existing packs

Separate `M6-import` gate; dry-run script; 16 packs; no auto-import in M6.

### 9. Tests

~11 backend test modules; frontend build + manual smoke; regression on CRM/public inbound/Margosya.

### 10. Approval gates

M5 → M6-BE → M6-FE → M6-bridge → M6-import → server deploy → production → Margosya cutover.

### 11. Recommended first code slice

**M6-BE1 + M6-BE2** (module skeleton + migration + topics API + tests). No UI, no publish, no export.

### 12. Risks

Scope creep, dual SoT, export mismatch, accidental live publish, Margosya breakage (mitigated by no-touch policy).

### 13. Implementation approval needed?

**Yes.**

| Approval | For |
|----------|-----|
| **M5 (this plan)** | start any M6 code |
| **M6-BE** | backend slices |
| **M6-FE** | frontend slices |
| **M6-bridge** | git export + live dispatch |
| **M6-import** | pack importer apply |

---

## Approval

| Field | Value |
|-------|-------|
| **Status** | `waiting for HQ approval` |
| **Document** | M5 implementation plan |
| **Next action after approval** | Execute **M6-BE1 + M6-BE2** locally |
| **Blocked until approved** | all code, migrations, deploy, Margosya |

---

*Документ подготовлен без изменений кода, migrations, deploy, production, Margosya bot и Core public inbound.*
