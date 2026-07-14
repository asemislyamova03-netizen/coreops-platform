# M3 — Marketing Cabinet UI Wireframe Plan

**Дата:** 2026-07-09  
**Проект:** Flexity / `coreops-platform`  
**Фаза:** M3 — UI wireframe plan  
**Категория:** `documentation_only`  
**Статус:** wireframe plan — **код не менялся**

**Родительские документы:**
- [2026-07-03-marketing-content-cabinet-product-tz.md](./2026-07-03-marketing-content-cabinet-product-tz.md) (M0)
- [2026-07-09-margosya-to-cabinet-audit.md](../research/2026-07-09-margosya-to-cabinet-audit.md) (M1)
- [2026-07-09-marketing-cabinet-data-model-draft.md](./2026-07-09-marketing-cabinet-data-model-draft.md) (M2)

**HQ approval:** documentation-only. Код, migrations, production, deploy, Margosya bot — **не трогать**.

---

## Task Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `documentation_only` |
| **Risk level** | low |
| **Intended scope** | `docs/ai/plans/2026-07-09-marketing-cabinet-ui-wireframe-plan.md` |
| **Forbidden scope** | код, migrations, production, deploy, Margosya bot, Core public inbound, Booking / Clinic / Trailers |

---

## 1. Goal

### 1.1 Зачем нужен UI

Дать Асем **единый web-кабинет** для контента, публикаций, статусов, лидов из контента и демо-интереса — чтобы **не управлять всем через Telegram-команды** Маргоси.

Сейчас ежедневный цикл выглядит так:

```text
Telegram → /daily_content_topic → step intake → /attach_visual_asset
         → /preflight_content_pack → /approve_content_pack → /publish_approved
```

Целевой цикл:

```text
Console → Marketing Cabinet → Pack detail → Preflight → Approve → Publish
       → (опционально) Margosya mobile для быстрых действий
       → Core CRM для лидов
```

### 1.2 Что UI должен решить

| Проблема сейчас | Как решает UI |
|-----------------|---------------|
| Команды в Telegram неудобны на desktop | Нормальные формы, табы, кнопки |
| Статус pack размазан по YAML | Единая карточка pack со статусами |
| Нет обзора «что сегодня» | Dashboard widgets |
| Лиды из контента — вручную в notes | Leads from Content + link to Core |
| Margosya = de facto main UI | Cabinet = primary; Margosya = remote |

### 1.3 Принципы UI (MVP)

1. **Pack detail — главный экран** (80% ежедневной работы).
2. **Не строить вторую CRM** — лиды открываются в Core (`/workspace/:slug/crm`).
3. **MVP = list views**, calendar/scheduler — later.
4. **Reuse platform-console patterns** — sidebar, panels, KPI cards, tables.
5. **Fail-closed visible** — preflight errors, approve gates, publish blockers на виду.

### 1.4 UI host

Marketing Cabinet живёт **внутри tenant workspace** `flexity-sales`, как новая секция sidebar:

```text
/workspace/flexity-sales/marketing/...
```

Рядом с существующими: dashboard, crm, clients, documents, finance, reports.

**Не** отдельное приложение. **Не** provider console.

---

## 2. Main navigation

### 2.1 Proposed sidebar (Marketing section)

Добавить группу **«Маркетинг»** в `WorkspaceSidebar` (или подменю после CRM):

| # | Nav item | Route (draft) | MVP | Notes |
|---|----------|---------------|-----|-------|
| 1 | **Dashboard** | `.../marketing` | ✅ | Marketing home |
| 2 | **Content Plan** | `.../marketing/plan` | ⚠️ placeholder | List later; MVP = link from dashboard |
| 3 | **Topics** | `.../marketing/topics` | ✅ | |
| 4 | **Packs** | `.../marketing/packs` | ✅ | |
| 5 | **Media** | `.../marketing/media` | ⚠️ minimal | Pack-linked only in MVP |
| 6 | **Publish Queue** | `.../marketing/queue` | ⚠️ placeholder | Simple list MVP |
| 7 | **Leads from Content** | `.../marketing/leads` | ✅ | Attribution, not CRM |
| 8 | **Reports** | `.../marketing/reports` | ⚠️ minimal | Manual counters |
| 9 | **Settings** | `.../marketing/settings` | ⚠️ minimal | Rules + transition info |
| 10 | **Margosya Remote** | `.../marketing/margosya` | ⚠️ read-only | Bot status MVP |

### 2.2 Navigation map (ASCII)

```text
┌─────────────────────────────────────────────────────────────┐
│ Flexity Workspace · flexity-sales                              │
├──────────────┬──────────────────────────────────────────────┤
│ Dashboard    │  Marketing Dashboard                          │
│ CRM          │  ┌─────────┬─────────┬─────────┬─────────┐  │
│ Clients      │  │ Today   │ Pending │ Failed  │ Leads   │  │
│ Documents    │  │ content │ approve │ publish │ content │  │
│ Finance      │  └─────────┴─────────┴─────────┴─────────┘  │
│ Reports      │                                               │
│ ─────────    │  Quick: [Take topic] [New pack] [Open CRM]   │
│ Маркетинг ▼  │                                               │
│  · Dashboard │                                               │
│  · Topics    │                                               │
│  · Packs     │                                               │
│  · Leads     │                                               │
│  · …         │                                               │
└──────────────┴──────────────────────────────────────────────┘
```

### 2.3 Hidden / placeholder in MVP

| Section | MVP behavior |
|---------|--------------|
| Content Plan | Nav visible; page = «Скоро» + shortcut «создать pack на дату» |
| Publish Queue | Nav visible; page = filter on Packs list (`publish_status`) |
| Reports | Nav visible; 4–6 manual counters |
| Settings | Nav visible; publishing rules text + git transition note |
| Margosya Remote | Read-only status card |

---

## 3. Dashboard wireframe

**Route:** `/workspace/:tenantSlug/marketing`

### 3.1 Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Маркетинг · Рабочий стол                         [+ Новый pack]│
├──────────────────────────────────────────────────────────────┤
│ ROW 1 — KPI cards (4–6)                                       │
├──────────────────────────────────────────────────────────────┤
│ ROW 2 — Two columns                                           │
│  LEFT: Today's content          RIGHT: Pending approval       │
├──────────────────────────────────────────────────────────────┤
│ ROW 3 — Two columns                                           │
│  LEFT: Failed publish           RIGHT: Latest publications    │
├──────────────────────────────────────────────────────────────┤
│ ROW 4 — Leads from content (table, last 5)                    │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Widgets

| Widget | Data source | Actions | MVP |
|--------|-------------|---------|-----|
| **Today's content** | Pack where `planned_date = today` OR plan item | Open pack, Create pack | ✅ |
| **Pending approval** | Packs `approval_status = pending` or `ready_for_approval` | Open pack → Approve | ✅ |
| **Failed publish** | Packs `publish_status = failed` OR last log `status=failed` | Open pack → Retry publish | ✅ |
| **Draft packs** | Packs `status = draft` | Open pack, Continue editing | ✅ |
| **Latest publications** | `marketing_publish_logs` last 5 | Open pack, External URL | ✅ |
| **New leads from content** | `marketing_lead_attribution` last 7d | Open lead in Core, Add attribution | ✅ |
| **Active demo access** | attribution.notes / future demo table | Open Core work item | ⚠️ notes only |
| **Reminders** | future `marketing_reminders` | Dismiss | ❌ later; static hint MVP |

### 3.3 Dashboard actions (header)

| Button | Target |
|--------|--------|
| **+ Новый pack** | Topics → Take topic OR Pack create modal |
| **Выбрать тему** | Topics list filtered `approved` |
| **Открыть CRM** | `/workspace/:slug/crm` (Core) |

### 3.4 Empty states

| State | Message | CTA |
|-------|---------|-----|
| No pack today | «На сегодня публикации нет» | [Выбрать тему] [Создать pack] |
| All approved | «Нет pack на approve» | — |
| No failures | «Ошибок публикации нет» | — |

---

## 4. Content Plan screen

**Route:** `/workspace/:tenantSlug/marketing/plan`  
**MVP:** placeholder + workaround via Packs filter by `planned_date`.

### 4.1 Modes

| Mode | MVP | Later |
|------|-----|-------|
| **List view** | ⚠️ simplified (packs grouped by date) | ✅ full `marketing_content_plan_items` |
| **Calendar view** | ❌ | ✅ month/week grid |

### 4.2 List row fields (target)

| Column | Source |
|--------|--------|
| Date | `planned_date` |
| Topic | topic.title |
| Channels | pack channels / plan.channels |
| Campaign | campaign.title (nullable) |
| Status | plan_item.status or pack.status |
| Pack | link if `pack_id` set |
| Actions | … |

### 4.3 Row actions

| Action | MVP | Later |
|--------|-----|-------|
| Create plan item | ❌ | ✅ |
| Create pack from topic | ✅ via Topics | ✅ inline |
| Mark skipped | ❌ | ✅ |
| Filter by channel/status/date | ✅ on Packs list | ✅ |

### 4.4 MVP workaround

**Content Plan nav** → redirect or embed:

```text
Packs list with:
  - group header by planned_date
  - filter: next 7 days
  - badge: no pack for today → warning
```

---

## 5. Topics screen

**Route:** `/workspace/:tenantSlug/marketing/topics`

### 5.1 Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Темы контента                    [+ Добавить тему] [Импорт bank]│
├──────────────────────────────────────────────────────────────┤
│ Tabs: [Approved] [Unused] [Used] [All] [Archived]             │
├──────────────────────────────────────────────────────────────┤
│ Filters: rubric ▼   reusable ☐   search ___________           │
├──────────────────────────────────────────────────────────────┤
│ TABLE                                                         │
│  Rubric | Title | Angle | Status | Used | Channels | Actions  │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Tabs / filters

| Tab | Filter |
|-----|--------|
| **Approved** | `status = approved` |
| **Unused** | `approved` AND `used_count = 0` |
| **Used** | `used_count > 0` OR `status = used` |
| **Reusable** | `reusable = true` |
| **Archived** | `status = archived` |
| **All** | no status filter |

### 5.3 Table columns

| Column | Notes |
|--------|-------|
| Rubric | from content bank |
| Title | |
| Angle | truncated |
| `legacy_topic_id` | e.g. CB-2026-06-28-015 |
| Status | badge |
| Used | `used_count`, `last_used_at` |
| Channels | chips: telegram, instagram, … |
| Duplicate marker | ✅ OK / ⚠️ duplicate (from selector logic) |
| Actions | Take, Create pack, Archive |

### 5.4 Row actions

| Action | Result |
|--------|--------|
| **Take topic** | Create draft pack + navigate to Pack detail |
| **Create pack** | Same with date picker |
| **Approve topic** | `status → approved` (from draft) |
| **Mark used** | manual override (admin) |
| **Archive** | `status → archived` |
| **Add topic** | Modal: title, rubric, angle, channels |

### 5.5 Anti-duplicate marker

Visual badge per topic (read-only in list):

| Badge | Meaning |
|-------|---------|
| 🟢 OK | No matching published pack |
| 🟡 Warning | Similar title in recent packs |
| 🔴 Blocked | Same `legacy_topic_id` in active pack |

Logic from Margosya `content_bank_selector` — shown before «Take topic».

### 5.6 Import bank (MVP)

Button **«Импорт из content bank»** → one-time / manual sync from markdown (admin action, not automatic).

---

## 6. Pack detail screen

**Route:** `/workspace/:tenantSlug/marketing/packs/:packId`  
**Это главный MVP-экран.**

### 6.1 Page structure

```text
┌──────────────────────────────────────────────────────────────┐
│ ← Packs    AI в госсекторе                    [Preflight] [Approve] [Publish]│
│ slug: ai-v-gossektore · 2026-07-07 · CB-2026-06-28-015      │
│ Status: APPROVED · Publish: PARTIAL · Source: console         │
├──────────────────────────────────────────────────────────────┤
│ TABS: [Texts] [Media] [Preflight] [Approval] [Publish] [Logs] │
├──────────────────────────────────────────────────────────────┤
│ (active tab content)                                          │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Pack header

| Field | UI element |
|-------|------------|
| Title | H1 |
| Slug | mono text + copy |
| Topic | link to Topics |
| Planned date | date |
| Status badges | `status`, `preflight_status`, `approval_status`, `publish_status` |
| Campaign | nullable; «—» in MVP |
| Source | `console` / `margosya` / `import` |
| Created at | timestamp |
| Legacy git path | collapsible «Transition» link (MVP) |

### 6.3 Tab: Channel texts

```text
┌─ Telegram ─────────────────────────────────────────────────┐
│ [textarea]                              chars: 1234 / 4096  │
│ Status: draft                                                │
├─ Instagram ────────────────────────────────────────────────┤
│ [textarea]                              chars: 890          │
├─ Threads ──────────────────────────────────────────────────┤
│ [textarea]                                                   │
├─ Insights (сайт) ──────────────────────────────────────────┤
│ [textarea — taller]                                          │
└──────────────────────────────────────────────────────────────┘
[Сохранить черновик]
```

| Channel | MVP | Validation hint |
|---------|-----|-----------------|
| Telegram | ✅ | warn if > 4096 |
| Instagram | ✅ | |
| Threads | ✅ | |
| Insights | ✅ | |

**Actions:** Save draft (per channel or all). No AI generate in MVP.

### 6.4 Tab: Media

```text
┌──────────────────────────────────────┐
│  [image preview 300x300]              │
│  instagram-feed.png                   │
│  1080×1080 · stored: git_path         │
│  Public URL: https://...  [test]      │
│                                       │
│  [Загрузить] [Заменить]               │
└──────────────────────────────────────┘
```

| Element | MVP |
|---------|-----|
| Image preview | ✅ |
| Upload / replace | ✅ file picker |
| Validation 1080×1080 | ✅ show pass/fail after upload |
| Public URL test | ✅ link + HTTP status badge |
| Carousel / video | ❌ later |

### 6.5 Tab: Preflight

```text
┌─ Preflight report ─────────────────────────────────────────┐
│ Status: PASSED / FAILED                    [Запустить снова] │
├────────────────────────────────────────────────────────────┤
│ ✅ pack.yml equivalent (metadata complete)                   │
│ ✅ telegram text not empty                                   │
│ ✅ instagram text not empty                                  │
│ ✅ instagram image present                                   │
│ ✅ public image URL HTTP 200                                 │
│ ⚠️ pack not on origin/main (transition warning)              │
│ ✅ telegram eligible (dry-run)                               │
│ ✅ instagram eligible (dry-run)                              │
├────────────────────────────────────────────────────────────┤
│ FAIL-CLOSED errors (if any) in red box                       │
└──────────────────────────────────────────────────────────────┘
```

| Element | MVP |
|---------|-----|
| Run preflight button | ✅ (header + tab) |
| Checklist | ✅ from `preflight_report_json` |
| Errors / warnings | ✅ |
| Channel dry-run excerpt | ✅ collapsible |

**Gate:** Approve button disabled if `preflight_status != passed`.

### 6.6 Tab: Approval

```text
┌─ Approval ─────────────────────────────────────────────────┐
│ Status: PENDING / APPROVED / REJECTED                       │
│                                                               │
│ [✅ Approve]  [❌ Reject]                                     │
│                                                               │
│ Approved at: 2026-07-08 15:30 by Asem                        │
│ Note: ___________________________ (optional)                  │
└──────────────────────────────────────────────────────────────┘
```

| Rule | UI |
|------|-----|
| Approve only after preflight pass | disabled + tooltip |
| Reject → back to draft | confirm modal |
| Audit trail | show timestamp |

### 6.7 Tab: Publish

```text
┌─ Publish ──────────────────────────────────────────────────┐
│ Channel status chips:                                         │
│  Telegram: published ✓   Instagram: published ✓              │
│  Threads: not started    Insights: not started             │
│                                                               │
│ [Publish now — all ready channels]                           │
│ [Publish Insights site]                                      │
│ Schedule: [datetime picker] (disabled MVP / placeholder)     │
└──────────────────────────────────────────────────────────────┘
```

| Action | MVP |
|--------|-----|
| Publish now (TG+IG) | ✅ |
| Publish Insights | ✅ separate button |
| Publish Threads | ⚠️ manual / secondary |
| Schedule later | ❌ placeholder disabled |
| Per-channel publish | ⚠️ optional secondary |

**Gate:** Publish disabled if `approval_status != approved`.

### 6.8 Tab: Logs

```text
┌─ Publish log ───────────────────────────────────────────────┐
│ TIME          CHANNEL    ACTION     STATUS   LINK           │
│ 07-08 13:25   telegram   published  success  [open]         │
│ 07-08 13:42   instagram  published  success  [open]         │
│ 07-08 12:50   content    approved   success  —              │
└──────────────────────────────────────────────────────────────┘
```

| Column | Source |
|--------|--------|
| Time | `created_at` |
| Channel | |
| Action | approved / published / failed |
| Status | success / failed |
| External | URL + post id |
| Error | expandable |

### 6.9 Packs list (companion screen)

**Route:** `/workspace/:tenantSlug/marketing/packs`

| Column | Notes |
|--------|-------|
| Date | planned_date |
| Title | |
| Slug | |
| Topic | |
| Approval | badge |
| Publish | badge |
| Channels | icons |
| Updated | |

**Filters:** status, approval, publish, date range, search slug/title.

**Default sort:** `planned_date DESC`, then `updated_at DESC`.

---

## 7. Media Library screen

**Route:** `/workspace/:tenantSlug/marketing/media`

### 7.1 MVP

```text
┌──────────────────────────────────────────────────────────────┐
│ Медиа · привязано к packs                                     │
├──────────────────────────────────────────────────────────────┤
│ TABLE: Preview | File | Pack | Size | Status | Uploaded       │
│ (only assets with pack_id)                                    │
└──────────────────────────────────────────────────────────────┘
```

| Feature | MVP |
|---------|-----|
| List pack-linked media | ✅ |
| Upload from pack only | ✅ (redirect to Pack detail → Media tab) |
| Standalone upload | ❌ |
| Search / tags | ❌ |
| Reusable library | ❌ |
| Video | ❌ |

### 7.2 Later

- Grid view with filters
- Object storage browser
- Orphan asset cleanup
- Usage rights metadata

---

## 8. Publish Queue screen

**Route:** `/workspace/:tenantSlug/marketing/queue`

### 8.1 MVP (simple list)

```text
┌──────────────────────────────────────────────────────────────┐
│ Очередь публикаций (упрощённо)                                │
├──────────────────────────────────────────────────────────────┤
│ Derived from packs + publish_logs (no queue table yet)         │
│                                                               │
│ Pack          Channel    Status      Scheduled    Error       │
│ ai-v-gossektore  instagram  published   —           —         │
│ threads-smoke    telegram   failed      —           token…    │
└──────────────────────────────────────────────────────────────┘
```

| Feature | MVP | Later |
|---------|-----|-------|
| Pack / channel / status list | ✅ | |
| Scheduled column | placeholder «—» | ✅ from queue table |
| Retry button | ✅ opens Pack publish tab | ✅ inline |
| Calendar schedule | ❌ | ✅ |
| Channel health | ❌ | ✅ |
| Auto retries | ❌ | ✅ |

---

## 9. Leads from Content screen

**Route:** `/workspace/:tenantSlug/marketing/leads`

### 9.1 Principle

**Не CRM.** Таблица attribution + ссылки в Core. Kanban / stages — только в `/crm`.

### 9.2 Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Лиды из контента              [+ Зафиксировать интерес]      │
├──────────────────────────────────────────────────────────────┤
│ TABLE                                                         │
│  Date | Channel | Content | Topic | Party | Lead | Touch | …  │
└──────────────────────────────────────────────────────────────┘
```

### 9.3 Table columns

| Column | Source |
|--------|--------|
| First touch | `first_touch_at` |
| Channel | telegram, instagram, website, manual |
| Content | pack title / `content_slug` link |
| Topic | topic title |
| Campaign | «—» MVP |
| Party | name → Core client/lead |
| Work item | title → Core CRM |
| Touch type | first_touch / assisted / converted |
| Notes | manual intake text |
| Demo | notes badge MVP |

### 9.4 Actions

| Action | Behavior |
|--------|----------|
| **+ Зафиксировать интерес** | Modal: channel, pack picker, notes → optional create Core lead |
| **Create Core lead** | Opens `CreateWorkItemModal` prefilled source + marketing metadata |
| **Link existing lead** | Search work item → set `work_item_id` on attribution |
| **Open in Core** | `/workspace/:slug/crm` or work item deep link |
| **Mark follow-up** | Create Activity/Task in Core (link out) |
| **Issue demo access** | Notes + expires_at field MVP; auto later |

### 9.5 Create attribution modal (MVP)

```text
Канал: [instagram ▼]
Пост / pack: [picker from packs]
Контакт (опционально): имя, телефон, @username
Заметки: ___________________
☐ Создать лид в CRM сейчас
[Сохранить]
```

If checkbox: call Core API → Party + WorkItem → save attribution with IDs.

### 9.6 Core link UX

| Element | Pattern |
|---------|---------|
| Lead link | External-link icon → CRM board |
| Party link | → `/clients/:partyId` |
| No inline kanban | ❌ |
| No stage edit | ❌ |

---

## 10. Reports screen

**Route:** `/workspace/:tenantSlug/marketing/reports`

### 10.1 MVP layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Отчёты · контент (ручной MVP)                                 │
├──────────────────────────────────────────────────────────────┤
│ Period: [last 7 days ▼]                                       │
├──────────────────────────────────────────────────────────────┤
│ KPI row:                                                      │
│  Published posts | By channel | Linked leads | Consultations  │
│  Demo issued     | Converted clients                          │
├──────────────────────────────────────────────────────────────┤
│ TABLE: Pack | Channel | Published | Leads | Reactions (manual)│
│ Reactions: editable number per pack (manual field MVP)        │
└──────────────────────────────────────────────────────────────┘
```

| Metric | Source MVP |
|--------|------------|
| Posts published | `publish_logs` count |
| By channel | group by channel |
| Linked leads | `lead_attribution` count |
| Consultations | manual flag on attribution |
| Demo issued | count notes containing demo |
| Clients converted | `source_type = converted` |
| Reactions / DMs | manual integer on pack or attribution |

### 10.2 Later

- Meta Insights API
- Yandex Metrika
- Campaign ROI
- Funnel charts
- Export CSV

---

## 11. Settings screen

**Route:** `/workspace/:tenantSlug/marketing/settings`

### 11.1 MVP sections

```text
┌─ Publishing rules (read-only info) ─────────────────────────┐
│ • Нет approved topic → нельзя создать pack (strict mode)     │
│ • Preflight обязателен перед approve                          │
│ • Publish только после approve                                │
│ • Instagram требует image 1080×1080 + public URL             │
├─ Channels (placeholders) ────────────────────────────────────┤
│ Telegram: configured via GitHub Actions (not in UI)           │
│ Instagram: configured via GitHub Actions                      │
│ Insights: generate_insights + deploy                          │
│ Threads: manual                                               │
├─ Transition ─────────────────────────────────────────────────┤
│ Git export path: landing/content/content-packs/               │
│ Export on publish: enabled (transition)                       │
├─ Content bank sync ──────────────────────────────────────────┤
│ [Импортировать topics из markdown]  Last: —                   │
└──────────────────────────────────────────────────────────────┘
```

### 11.2 Later

| Section | Content |
|---------|---------|
| Token management | vault refs, never show secret |
| Channel connections | health check UI |
| Storage settings | S3 bucket, quotas |
| Reminders | rules editor |
| Margosya API key | service token rotate |

---

## 12. Margosya Remote / Bot Status

**Route:** `/workspace/:tenantSlug/marketing/margosya`

### 12.1 Purpose

Показать, что Telegram — **remote control**, не source of truth. Дать Асем уверенность, что bot и Cabinet синхронизированы.

### 12.2 Layout (MVP read-only)

```text
┌──────────────────────────────────────────────────────────────┐
│ Margosya · Telegram remote                                    │
├──────────────────────────────────────────────────────────────┤
│ Bot status: 🟢 Connected / 🔴 Unknown (heartbeat later)       │
│ Mode: API (target) / Filesystem (transition)                │
├──────────────────────────────────────────────────────────────┤
│ Last pack from Telegram:                                      │
│   title, slug, created_at, source=margosya                    │
│   [Open pack]                                                 │
├──────────────────────────────────────────────────────────────┤
│ Pending approvals via bot: 0                                  │
│ Failed bot actions (24h): 0                                   │
├──────────────────────────────────────────────────────────────┤
│ Quick help:                                                   │
│   Bot commands mirror Pack detail actions.                    │
│   Primary editing → use this Cabinet.                         │
└──────────────────────────────────────────────────────────────┘
```

| Field | MVP | Later |
|-------|-----|-------|
| Bot connected | static / manual | heartbeat API |
| Last command | ❌ | webhook log |
| Last pack from TG | ✅ query `source=margosya` | |
| Pending approvals | ✅ count packs pending | push sync |
| Failed actions | ❌ | bot error log |
| Reminders sent | ❌ | |
| Force sync | ❌ | admin |

### 12.3 Target architecture note

```text
Margosya → Marketing Cabinet API → PostgreSQL
                ↓ (transition)
           git export for GHA publish
```

---

## 13. MVP UI scope

### 13.1 Screens IN MVP (M6)

| Screen | Priority |
|--------|----------|
| Marketing Dashboard | P0 |
| Topics list | P0 |
| Packs list | P0 |
| **Pack detail** (all tabs) | **P0 — main** |
| Leads from Content (list + create modal) | P1 |
| Margosya Remote (read-only) | P2 |
| Reports (minimal) | P2 |
| Settings (minimal) | P2 |
| Media (pack-linked list) | P2 |
| Publish Queue (derived list) | P2 |
| Content Plan (placeholder) | P3 |

### 13.2 Features IN MVP

- Topics list with tabs/filters
- Take topic → create pack
- Pack detail: 4 channel text areas
- Media preview + upload
- Preflight button + report display
- Approve / reject
- Publish now + publish insights
- Publish log table
- Manual lead attribution + link to Core
- Basic dashboard widgets
- Import topics from content bank (admin button)

### 13.3 EXCLUDED from MVP

| Feature | Reason |
|---------|--------|
| Full calendar | plan_items table deferred |
| Real queue scheduler | queue table deferred |
| Meta inbox | scope |
| WhatsApp API | scope |
| Ads analytics | scope |
| Token management UI | security; GHA/env |
| Automatic demo provisioning | manual notes first |
| Billing | out of scope |
| AI text generation | external ChatGPT |
| Multi-tenant marketing | dogfood one tenant |
| Inline CRM kanban | Core only |
| Video media library | later |
| TikTok publish UI | later |

### 13.4 MVP route summary

```text
/workspace/:tenantSlug/marketing              → Dashboard
/workspace/:tenantSlug/marketing/topics       → Topics
/workspace/:tenantSlug/marketing/packs        → Packs list
/workspace/:tenantSlug/marketing/packs/:id    → Pack detail
/workspace/:tenantSlug/marketing/leads        → Leads from Content
/workspace/:tenantSlug/marketing/reports      → Reports (minimal)
/workspace/:tenantSlug/marketing/settings     → Settings (minimal)
/workspace/:tenantSlug/marketing/margosya      → Bot status
/workspace/:tenantSlug/marketing/media        → Media (minimal)
/workspace/:tenantSlug/marketing/queue        → Queue (derived)
/workspace/:tenantSlug/marketing/plan         → Placeholder
```

---

## 14. Daily workflow for Асем

### 14.1 Desktop-first (primary)

```text
08:00  1. Открыть /marketing Dashboard
       2. Проверить блок «Сегодня» — есть ли pack на сегодня
       3. Если нет → Topics → Take topic

09:00  4. Pack detail → вставить/проверить тексты (4 канала)
       5. Media tab → загрузить instagram-feed.png

09:30  6. Preflight → исправить ошибки если FAIL
       7. Approve

10:00  8. Publish now (TG + IG)
       9. Publish Insights (если нужна статья)
       10. Logs tab → проверить external URLs

в течение дня:
       11. Leads from Content → «Написал в Instagram»
       12. Создать/привязать lead → Open in Core CRM
       13. Follow-up в Core (не в Marketing)
```

### 14.2 Mobile fallback (Margosya)

```text
Если нет компьютера:
  Telegram → выбрать тему → отправить тексты → фото
  → Margosya создаёт pack через API
  → позже на desktop: Pack detail → preflight → approve → publish
```

### 14.3 Decision rule

| Situation | Where |
|-----------|-------|
| Полный цикл контента | **Cabinet** |
| Быстрый текст/фото с телефона | **Margosya** |
| Работа с лидом / КП / клиентом | **Core CRM** |
| Аналитика эффективности (MVP) | **Cabinet Reports** (manual) |

---

## 15. Migration from Margosya UX

| Margosya UX | Marketing Cabinet UI |
|-------------|----------------------|
| `/daily_content_topic` | Topics → suggested / «Take topic» |
| `/daily_content_topic_next` | Topics → filter unused → next row |
| Inline «Взять эту тему» | Topics row action **Take topic** |
| Step 1–4 intake messages | Pack detail → Texts tab (4 textareas) |
| `/create_content_pack_from_text` | Pack create modal or paste-all mode |
| `/attach_visual_asset` + photo | Pack detail → Media tab → Upload |
| `/preflight_content_pack` | Pack header **[Preflight]** + Preflight tab |
| `/approve_content_pack` | Pack header **[Approve]** + Approval tab |
| `/publish_approved` | Pack header **[Publish]** + Publish tab |
| `/publish_insights_site` | Publish tab → **[Publish Insights]** |
| `/list_content_drafts` | Packs list filter `draft` |
| `/last_content_pack` | Dashboard «Latest» / Packs sort by updated |
| `/recent_publish_log` | Pack detail → Logs tab; Dashboard widget |
| ContentOps menu buttons | Pack detail header actions |
| `/recent_publish_log` (global) | Dashboard «Latest publications» |
| Telegram status commands | Margosya Remote screen |

### 15.1 UX improvement vs Margosya

| Margosya pain | Cabinet fix |
|---------------|-------------|
| Команды нужно помнить | Visible buttons + tabs |
| Статус размазан | Header badges |
| Preflight report в chat wall | Structured checklist tab |
| Нет обзора недели | Packs list + filters |
| Лид из DM — отдельно в CRM | Leads from Content bridge |

---

## 16. UI risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| 1 | **Слишком много разделов сразу** | Overwhelm, delay M6 | MVP: 4 primary nav items + rest placeholder |
| 2 | **Дублирование Core CRM** | Two lead systems | Leads screen = attribution only; link out |
| 3 | **Сложная аналитика рано** | Wasted effort | Manual counters only in MVP Reports |
| 4 | **Scheduler UI before storage** | Broken publish | Publish now only; schedule disabled |
| 5 | **Margosya и Cabinet расходятся** | Dual SoT confusion | `source` field; Margosya Remote screen |
| 6 | **UI неудобный → back to Telegram** | Cabinet unused | Pack detail first; desktop-optimized forms |
| 7 | **Pack detail too heavy** | Slow load | Tab lazy-load; save per channel |
| 8 | **Transition git export hidden** | Publish fails | Settings + preflight warning visible |
| 9 | **10 sidebar items** | Cognitive load | Group under «Маркетинг»; MVP show 4–5 |
| 10 | **No mobile responsive** | Asem uses phone | Acceptable: Margosya covers mobile |

### 16.1 Scope guard for M6 UI slice

**Ship first:** Dashboard + Topics + Packs list + Pack detail.  
**Ship second:** Leads + Reports minimal.  
**Ship third:** Settings + Margosya Remote + placeholders.

---

## 17. Recommended next step

### 17.1 Path

```text
M0 TZ ✅ → M1 Audit ✅ → M2 Data model ✅ → M3 UI wireframes ✅
    → M4 API contract draft
    → (optional M3b MVP cut review if HQ wants smaller UI)
    → M5 MVP implementation plan
    → HQ approval → M6 code
```

### 17.2 M3b trigger (optional)

Запустить **M3b — MVP UI cut review** если HQ считает:
- 10 nav items слишком много;
- Pack detail 6 tabs тяжёлый для первого slice;
- Leads screen можно отложить.

**Рекомендация M3:** scope приемлем для M6 **при поэтапной поставке** (§16.1). M3b **не обязателен**, если согласны на 3-wave UI delivery.

### 17.3 M4 inputs from M3

Для API contract нужны screen-action mapping:

| Screen action | API endpoint (draft) |
|---------------|---------------------|
| Topics list | `GET /marketing/topics` |
| Take topic | `POST /marketing/packs` |
| Save texts | `PATCH /marketing/packs/{id}/channels/{ch}` |
| Upload media | `POST /marketing/packs/{id}/media` |
| Preflight | `POST /marketing/packs/{id}/preflight` |
| Approve | `POST /marketing/packs/{id}/approve` |
| Publish | `POST /marketing/packs/{id}/publish` |
| Logs | `GET /marketing/packs/{id}/logs` |
| Attribution | `POST /marketing/attributions` |
| Dashboard widgets | `GET /marketing/dashboard` |

---

## 18. HQ summary

### 1. Path

```text
M0 ✅ → M1 ✅ → M2 ✅ → M3 ✅ → M4 API contract → M5 impl plan → M6 code
```

### 2. Main UI sections

10 разделов: Dashboard, Content Plan, Topics, Packs, Media, Publish Queue, Leads from Content, Reports, Settings, Margosya Remote.

### 3. MVP screens

**P0:** Dashboard, Topics, Packs list, **Pack detail**  
**P1:** Leads from Content  
**P2:** Reports, Settings, Media, Queue (minimal), Margosya Remote  
**P3:** Content Plan placeholder

### 4. Daily workflow

Dashboard → topic → pack texts → media → preflight → approve → publish → logs → attribution → Core CRM.

### 5. Margosya UX mapping

14 соответствий command/button → Cabinet screen (§15).

### 6. Excluded from MVP

Full calendar, scheduler UI, token UI, Meta inbox, ads analytics, auto demo, billing, AI generate, CRM kanban, video library.

### 7. Main UI risks

Too many sections, CRM duplication, Margosya/Cabinet drift, UI unused if Pack detail weak.

### 8. Recommended next step

**M4 — API contract draft** (screen-action → endpoints + schemas).

Optional: **M3b MVP cut review** if HQ wants smaller first UI slice.

### 9. Implementation approval needed?

**Yes.** UI code only after approved **M5 MVP implementation plan**.

---

*Документ подготовлен без изменений кода, migrations, deploy, production, Margosya bot и Core public inbound.*
