# Implementation Plan: Marketing M6-FE3 — workflow polish

**Дата:** 2026-07-13  
**Проект:** Flexity / `coreops-platform`  
**Слайс:** M6-FE3  
**Категория:** `documentation_only` (этот документ) → позже `universal_module` (marketing FE)  
**Статус:** waiting for HQ approval on **code** — этот файл = audit + plan only  

**Родительские документы:**
- [2026-07-09-marketing-cabinet-mvp-implementation-plan.md](./2026-07-09-marketing-cabinet-mvp-implementation-plan.md)
- [2026-07-09-marketing-cabinet-ui-wireframe-plan.md](./2026-07-09-marketing-cabinet-ui-wireframe-plan.md)
- [2026-07-13-crm-ready-marketing-cabinet-next-handoff.md](../handoffs/2026-07-13-crm-ready-marketing-cabinet-next-handoff.md)
- FE2 report: [2026-07-10-marketing-cabinet-m6-fe2-pack-detail-editor-report.md](../reports/2026-07-10-marketing-cabinet-m6-fe2-pack-detail-editor-report.md)

**HQ approval (этот документ):** documentation / audit planning only.  
Код, backend, deploy, env, migrations, publish/export — **не трогать** до отдельного approval на реализацию.

---

## Task Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `documentation_only` (сейчас) / planned code: `universal_module` (marketing console UI) |
| **Risk level** | low (FE-only polish; no publish) |
| **Intended scope (docs)** | `docs/ai/plans/2026-07-13-marketing-m6-fe3-workflow-polish-plan.md` |
| **Intended scope (future code)** | `platform-console/src/pages/workspace/marketing/**`, `platform-console/src/api/marketing.ts`, `platform-console/src/types/marketing.ts`, helpers/labels |
| **Forbidden scope** | backend (unless HQ opens tiny gap), Margosya, publish/git export, binary upload, CRM tenant automation, Booking/Clinic/Trailers, deploy, env, migrations |

---

## Goal

Сделать Marketing Cabinet удобным для ежедневной работы Асем:

```text
Topics → взять тему → Pack detail → тексты → media → preflight → approve
```

**Без** publish/export. Publish остаётся честно disabled.

### Slice naming note

В исходном M5 плане: FE3 = Topics screen, FE5 = Pack detail.  
Фактически выполнено: **FE1 = shell**, **FE2 = pack detail editor**.  

**M6-FE3 в этом документе** = workflow polish (topics take-flow + packs list UX + next-action hints + media edit + publish honesty), а не «только topics table из M5».

---

## Audit — current state (2026-07-13, read-only)

### 1. Routes / navigation

| Browser URL (basename `/console`) | Component | State |
|-----------------------------------|-----------|--------|
| `/console/workspace/:slug/marketing` | `MarketingDashboardPage` | KPI + links; FE1 placeholder copy still says «редактор будет подключен» |
| `/console/workspace/:slug/marketing/topics` | `MarketingTopicsPage` | read-only list |
| `/console/workspace/:slug/marketing/packs` | `MarketingPacksPage` | read-only list + link to detail |
| `/console/workspace/:slug/marketing/packs/:packId` | `MarketingPackDetailPage` | FE2 editor tabs |

**Nav:** `WorkspaceSidebar` → segment `marketing` («Маркетинг»), между Финансы и Отчёты.  
**How to reach:** Sidebar → Маркетинг → Dashboard links Topics/Packs → Pack title link → detail.

**Verdict:** routes OK. Dashboard copy устарел относительно FE2.

---

### 2. Topics workflow

| Capability | Backend | Frontend API | UI |
|------------|---------|--------------|-----|
| List topics | ✅ `GET /topics` (+ status, rubric, search) | ✅ `listMarketingTopics` | ✅ table (title, rubric, status, priority, used, updated) |
| Create topic | ✅ `POST /topics` | ❌ missing | ❌ |
| Get / edit topic | ✅ `GET/PATCH /topics/{id}` | ❌ missing | ❌ |
| Take topic → pack | ✅ `POST /topics/{id}/take` → draft pack + 4 empty texts | ❌ missing | ❌ |
| Archive | ✅ `POST .../archive` | ❌ missing | ❌ |
| Mark used | ✅ `POST .../mark-used` | ❌ missing | ❌ |

**Take gate (backend):** topic must be `status === "approved"` (`MarketingTopicNotApprovedError` otherwise).  
Also: non-reusable + already used / active packs → duplicate blocked; slug uniqueness; one pack per topic+planned_date.

**Topic statuses (enum, not `in_progress`):** `draft` → `approved` → `used` → `archived`.

**After take (backend):** returns `TakeTopicPackResponse` with new `pack.id`. FE currently does not navigate.

**Verdict:** главный разрыв daily workflow — нет create / approve-topic / take / open pack.

---

### 3. Packs list

| Aspect | Current |
|--------|---------|
| Columns | title (link), slug, status, approval_status, preflight_status, planned_date, updated_at |
| Topic column | API includes `topic`, UI **не показывает** |
| Filters | ❌ none in UI |
| Search | FE types allow `search`; **BE `list_packs` не имеет search** (есть `status`, `topic_id`, `planned_date`) |
| Empty state | ✅ info alert «Пока нет публикаций» |
| Open pack | ✅ Link to detail |
| Subtitle | still «только просмотр (M6-FE1)» — outdated |

**approval_status filter:** нет на BE. Для FE3 достаточно client-side filter на загруженном списке (`limit: 200`) или filter по `status` через BE.

**Verdict:** list usable but thin; filters/topic column/next-entry points missing.

---

### 4. Pack detail

| Tab | State |
|-----|--------|
| Texts | ✅ per-channel edit + save + invalidate |
| Media | ✅ add metadata + archive; **no inline edit** (client has `updateMarketingMedia`) |
| Preflight | ✅ run + report (session-only after reload) |
| Approval | ✅ approve (if preflight passed) / reject |
| Publish | tab button **disabled**; content has disabled fake button «Опубликовать (disabled)» |
| Logs | ✅ read-only `publish_logs` |

**Header:** raw status strings (no RU labels), no topic link, **no next-action block**.

**Verdict:** editor works; daily guidance and media edit polish missing; publish honesty weak (fake button).

---

### 5. API client gaps

**Present in** `platform-console/src/api/marketing.ts`:

- health, listTopics, listPacks, getPack  
- updatePackText, list/add media, updateMedia, deleteMedia  
- preflight, approve, reject  

**Missing for FE3 workflow:**

| Method needed | Endpoint |
|---------------|----------|
| `createMarketingTopic` | `POST /marketing/topics` |
| `updateMarketingTopic` | `PATCH /marketing/topics/{id}` |
| `takeMarketingTopic` | `POST /marketing/topics/{id}/take` |
| `archiveMarketingTopic` | `POST /marketing/topics/{id}/archive` |
| optional `markMarketingTopicUsed` | `POST /marketing/topics/{id}/mark-used` |
| optional `createMarketingPack` | `POST /marketing/packs` |
| optional `patchMarketingPack` | `PATCH /marketing/packs/{id}` |

**Param mismatches:**

- FE `ListMarketingPacksParams.search` — BE ignores / not implemented.  
- BE `planned_date` filter — FE types omit.  
- No BE `approval_status` query param.

---

### 6. Types / helpers

| Item | State |
|------|--------|
| Types in `types/marketing.ts` | ✅ channels, statuses, payloads, preflight response |
| TakeTopic response type | ❌ missing |
| Topic create/update payloads | ❌ missing |
| RU status / channel / approval / preflight labels | ❌ none (raw enum strings in UI) |
| Next-action helper | ❌ none |

---

## Backend changes needed?

**No for recommended FE3 scope** — APIs already exist for take/create/patch topics and pack list status filter.

**Optional later BE (separate slice, not FE3):**

1. `GET /packs?approval_status=` and/or `search=`  
2. Persist `preflight_report_json` on pack detail (FE2 risk)  
3. Dedicated topic «approve» action (сегодня = `PATCH status=approved`)

If HQ wants server-side approval filter in FE3 — open **tiny BE gap** separately; otherwise client-side filter.

---

## Recommended FE3 scope (frontend-only)

### In scope

#### A. Topics page polish
- Quick create topic (title, rubric, optional angle/priority).  
- Action «Утвердить тему» → `PATCH status=approved` (only for draft).  
- Action «Взять тему в работу» → `take` → `navigate` to `/marketing/packs/{packId}`.  
- Disable take unless `approved`; show friendly error if BE rejects.  
- Status badges with RU labels: draft / approved / used / archived.  
- Empty state + short hint: «Создайте тему → утвердите → возьмите в работу».  
- Optional: archive button (soft).

#### B. Packs list polish
- Show topic title (from `pack.topic`).  
- Client filters: pack `status`, `approval_status`; optional text filter on title/slug.  
- Use BE `status` query when single status selected (optional optimization).  
- Empty state; keep open-pack link.  
- Update FE1 «только просмотр» subtitle.

#### C. Pack detail — next action block
Pure helper from pack (+ texts/media counts):

| Condition | Next action copy |
|-----------|------------------|
| All channel texts empty/whitespace | «Заполните тексты по каналам» → focus Texts |
| Texts present, no active media | «Добавьте media metadata» → Media |
| Texts+media, preflight not_run / failed | «Запустите preflight» / «Исправьте ошибки preflight» |
| preflight passed, not approved | «Можно согласовать (Approval)» |
| approved | «Готово к публикации; publish пока выключен» |
| rejected | «Исправьте контент и снова запустите preflight» |

#### D. Media polish
- Keep metadata-only banner.  
- Wire `updateMarketingMedia` for inline edit of existing asset.  
- No binary upload.

#### E. Publish honesty
- Enable **viewing** Publish tab (read-only) OR keep tab disabled but improve copy if opened via code later.  
- Recommended: **enable tab for reading**, remove fake «Опубликовать» button, show:

  > Публикация пока выключена.  
  > Marketing Cabinet — source of truth. Margosya / git export — отдельным gate.

#### F. Shared helpers
- `marketingLabels.ts` — RU labels for topic/pack/preflight/approval/publish/channel.  
- `marketingNextAction.ts` — pure next-action resolver (unit-testable).  
- Types for TakeTopic + TopicCreate/Update.

#### G. Dashboard copy fix
- Remove stale «редактор будет подключен»; link KPI «На согласовании» → packs with filter query if easy.

### Explicitly out of scope (FE3)

- Publish / git export / GHA  
- Margosya integration  
- Binary media upload / object storage  
- Leads attribution (FE6/P1)  
- Full dashboard widgets rewrite (GET `/marketing/dashboard` if not exists)  
- Backend migrations / new endpoints (unless HQ opens tiny filter gap)  
- Deploy / env  
- CRM tenant automation  
- Renaming historical M5 FE3/FE5 numbers in old plans (note only)

---

## Scope — files (when code approved)

### Files to modify / create

| Path | Action |
|------|--------|
| `platform-console/src/api/marketing.ts` | add topic create/patch/take/archive (+ types usage) |
| `platform-console/src/types/marketing.ts` | TakeTopic*, TopicCreate/Update payloads |
| `platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx` | create / approve / take / badges |
| `platform-console/src/pages/workspace/marketing/MarketingPacksPage.tsx` | topic col, filters, empty polish |
| `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx` | next-action block, RU labels, publish tab policy |
| `platform-console/src/pages/workspace/marketing/packDetail/PackDetailMediaTab.tsx` | inline metadata edit |
| `platform-console/src/pages/workspace/marketing/packDetail/PackDetailPublishTab.tsx` | honesty copy, no fake CTA |
| `platform-console/src/pages/workspace/marketing/MarketingDashboardPage.tsx` | stale copy fix |
| `platform-console/src/pages/workspace/marketing/marketingLabels.ts` | **new** |
| `platform-console/src/pages/workspace/marketing/marketingNextAction.ts` | **new** |
| optional `.../marketing/__tests__/*` or colocated tests | next-action + labels |

### Files not to touch

- `backend/**`  
- Margosya / content-bank  
- migrations, `.env`, deploy/GHA  
- CRM / Booking / Clinic / Trailers  
- Publish BE (M6-BE6)

---

## Steps (implementation order after HQ code approval)

1. Add types + API client methods for topics mutations + take.  
2. Add `marketingLabels` + `marketingNextAction` helpers + unit tests.  
3. Topics page: create, approve, take→navigate, badges, empty state.  
4. Packs list: topic column, client filters, copy fix.  
5. Pack detail: next-action banner; RU labels in header.  
6. Media: inline edit via existing PATCH.  
7. Publish tab honesty (view-only, no fake button).  
8. Dashboard copy fix.  
9. `npm run build` + manual smoke.

---

## Tests / checks

| Check | How |
|-------|-----|
| Labels helpers | unit: each status → non-empty RU string |
| Next-action helper | unit: matrix of pack states → expected action id |
| Topic take → navigate | manual smoke (or component test if harness exists) |
| Filters | manual: status/approval change table rows |
| Empty states | manual: empty tenant / empty filter |
| Publish honesty | manual: no enabled publish CTA |
| Build | `cd platform-console && npm run build` |
| Backend regression | **none expected** (FE-only) |

Frontend test script historically not configured — prefer small pure-helper tests if Vitest already present; else document manual smoke only.

### Manual smoke script

1. Marketing → Topics → create topic (draft).  
2. Approve topic → badge `approved`.  
3. Take → land on pack detail with 4 empty texts.  
4. Fill one text → next action updates.  
5. Add media metadata → edit metadata → archive.  
6. Preflight → approve.  
7. Next action shows publish disabled message.  
8. Packs list: filter pending/approved; open pack.  
9. Confirm Publish tab: no live publish.

---

## Risks

1. **Take requires approved topic** — UI must expose approve step or take always fails for drafts.  
2. **Duplicate / slug errors** — need friendly mapping (`formatMarketingApiError`).  
3. **Pack search/approval filter** — client-side only up to 200 rows; large tenants may need BE later.  
4. **Product word `in_progress`** — not in enum; map UX to `approved` (topic) / pack `draft`…`ready_for_approval`.  
5. **Enabling Publish tab for reading** — must not look like publish is live.  
6. **Local-only marketing** — do not assume production deploy of BE/FE; smoke only where module enabled.  
7. **Dirty Flexity tree** — FE3 code commit/deploy must stay scoped; no CRM mix.

---

## Rollback

Revert FE commits / files listed above. No DB/migration rollback. No BE changes if FE-only.

---

## Approval

| Gate | Status |
|------|--------|
| Documentation / audit plan (this file) | **requested / HQ approved for planning** |
| Code implementation of FE3 | **waiting for separate HQ approval** |
| Deploy | **forbidden until explicit HQ** |
| Publish/export | **forbidden** |

**Status:** waiting for approval **to implement code**

---

## Next safe step

1. HQ: approve **FE3 code scope** as written (frontend-only).  
2. Implement Steps 1–9 in one small PR/slice.  
3. Report + local build smoke.  
4. Deploy only if HQ opens a separate marketing deploy gate.

---

## HQ summary checklist

1. **Status:** Plan ready (docs only); code not started.  
2. **Files inspected:** marketing FE pages, `api/marketing.ts`, `types/marketing.ts`, `routes.tsx`, `WorkspaceSidebar`, backend `routes.py` / `enums.py` / `topics.py` take logic, FE1/FE2 reports, handoff.  
3. **Routes/nav:** 4 routes OK; sidebar «Маркетинг» OK.  
4. **Topics:** list-only UI; BE has create/take/archive/mark-used; take needs `approved`.  
5. **Packs list:** open detail OK; no filters; topic col unused; FE1 subtitle stale.  
6. **Pack detail:** FE2 editor OK; no next-action; media no edit UI; publish fake-disabled.  
7. **API gaps:** topic mutations + take (+ optional create/patch pack).  
8. **Backend needed:** **No** for recommended scope.  
9. **FE3 scope:** topics take-flow + packs filters + next-action + media edit + publish honesty + labels.  
10. **Tests:** helper units + build + manual smoke.  
11. **Out of scope:** publish/export, Margosya, upload, BE, deploy, CRM tenants.  
12. **Risks:** take gate, client-side filters, label `in_progress` mismatch, local-only module.  
13. **Next:** HQ approve FE3 **code** implementation.
)
