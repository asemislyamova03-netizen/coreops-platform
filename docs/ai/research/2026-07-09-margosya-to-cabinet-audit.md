# M1 Audit: Margosya → Marketing Cabinet

**Дата:** 2026-07-09  
**Проект:** Flexity / `coreops-platform`  
**Фаза:** M1 — read-only audit Margosya features  
**Категория:** `research_only` / `documentation_only`  
**Статус:** audit complete — **код не менялся**

**Родительский документ:** [2026-07-03-marketing-content-cabinet-product-tz.md](../plans/2026-07-03-marketing-content-cabinet-product-tz.md)  
**Аудируемый репозиторий:** `margosya-os` (отдельный deploy, bot `margosya-bot`)  
**Source of truth сегодня (interim):** Flexity git repo `landing/content/content-packs/` + `docs/content/flexity-content-bank.md`

---

## Task Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity (+ read-only audit `margosya-os`) |
| **Category** | `research_only` |
| **Risk level** | low |
| **Intended scope** | `docs/ai/research/2026-07-09-margosya-to-cabinet-audit.md` |
| **Forbidden scope** | код, migrations, production, deploy, publish, env/secrets, изменения Telegram bot |
| **Required plan** | M1 audit (этот документ) |

---

## 1. Context

### 1.1 Зачем этот аудит

HQ decision: Marketing Cabinet во Flexity становится **source of truth** для контент-операций. Маргося остаётся **Telegram thin client**.

M1 фиксирует:
- что уже реализовано в Маргосе;
- где хранятся данные и статусы;
- какие функции нужно перенести в Marketing Cabinet;
- что оставить в боте;
- gaps между текущим состоянием и MVP из product TZ.

### 1.2 Метод аудита

| Источник | Что смотрели |
|----------|--------------|
| `margosya-os` Python modules | Команды, handlers, state, publish helpers |
| `margosya-os/docs/MARGOSYA_CONTENTOPS_RUNBOOK.md` | Операционный flow |
| `margosya-os/reports/MARGOSYA_CONTENTOPS_BOUNDARY.md` | Границы ответственности |
| `margosya-os/reports/MARGOSYA_PUBLISHING_AND_REPO_SPLIT_AUDIT.md` | Предыдущий publish audit (июль 2026) |
| `Flexity/landing/content/content-packs/` | Реальные pack-артефакты |
| `Flexity/docs/content/flexity-content-bank.md` | Content bank (approved topics) |
| `Flexity/scripts/content/` | Publish scripts (Telegram, Instagram, insights) |
| Unit tests в `margosya-os/scripts/test_*.py` | Покрытие ContentOps flows |

**Не делали:** SSH на сервер, чтение production `.env`, live publish, изменения кода.

---

## 2. Executive summary

### 2.1 Текущая архитектура (as-is)

```text
Асем (Telegram)
    → margosya-bot (telegram_inbox_bot.py)
        → Python helpers (content_pack_factory, content_ops_publish, …)
            → Flexity filesystem (landing/content/content-packs/*)
            → Flexity scripts (publish_telegram.py, instagram publisher, generate_insights)
            → GitHub Actions workflows (telegram-publish.yml, instagram-publish.yml)
            → publish_log.yml в git
```

**Ключевой вывод:** Маргося сейчас **оркестратор + UI**, но **не владеет** pack metadata как DB. Source of truth de facto — **git repo Flexity** (`pack.yml`, `*.md`, `publish_log.yml`).

### 2.2 Зрелость по блокам

| Блок | Зрелость | Комментарий |
|------|----------|-------------|
| Topic selection | ✅ Работает | Read-only из markdown content bank + duplicate logic |
| Step intake (4 канала) | ✅ Работает | Telegram → IG → Threads → Insights |
| Legacy pack from text | ✅ Работает | Без insights.md на legacy route |
| ContentOps intake contract | ⚠️ Хрупкий | Длинные блоки в Telegram часто ломаются |
| Visual asset upload | ✅ MVP | PNG/JPG/WebP → `landing/www/assets/social/` |
| Preflight | ✅ Работает | Dry-run + fail-closed gates |
| Approve | ✅ Работает | Меняет `pack.yml` / `instagram.yml` status |
| Publish TG/IG | ✅ Работает | Через GitHub Actions dispatch |
| Publish Insights | ✅ Работает | generate + deploy landing |
| Publish Threads/TikTok | ⚠️ Partial | Команды есть; зрелость ниже TG/IG |
| Publish log | ✅ Работает | `publish_log.yml` per pack |
| Status / drafts list | ✅ Работает | Read YAML из packs dir |
| Reminders | ❌ Нет | Только ручные уведомления через bot |
| Lead attribution | ❌ Нет | Не в scope Маргоси |
| Campaign / Offer | ❌ Нет | Не в scope Маргоси |
| Content Plan calendar | ❌ Нет | Только content bank + pack date |
| Scheduled publish UI | ⚠️ Partial | `publish_at` в pack.yml; cron в GHA |
| Flexity API integration | ❌ Нет | Прямые вызовы Python + filesystem |
| Multi-user / roles | ❌ Нет | `TELEGRAM_ALLOWED_USER_IDS` whitelist |

### 2.3 Рекомендация M1

Переносить в Marketing Cabinet **логику и metadata**, не копировать bot handlers. Маргосю оставить как **transport layer** с mapping на API из M4.

Следующий шаг: **M2 — Data model draft** (сущности из product TZ + mapping из таблиц ниже).

---

## 3. Margosya module map

### 3.1 ContentOps modules (in scope для Cabinet)

| Файл | Роль |
|------|------|
| `integrations/telegram/telegram_inbox_bot.py` | Polling bot, commands, callbacks, routing |
| `telegram_contentops_menu.py` | Reply keyboard + inline menus, pack action buttons |
| `content_bank_selector.py` | Topic selection из `flexity-content-bank.md`, duplicate check |
| `daily_content_topic_session.py` | Session: proposed topics за день |
| `content_pack_factory.py` | Create pack from text / intake contract |
| `content_pack_intake_state.py` | Pending legacy 2-step intake (JSONL) |
| `content_pack_step_intake.py` | Step-by-step 4-channel intake |
| `content_pack_step_intake_state.py` | Pending step intake (JSONL) |
| `visual_asset_attach.py` | Image normalize + save instagram-feed.png |
| `visual_asset_intake_state.py` | Pending visual upload session |
| `content_ops_publish.py` | Preflight, approve, publish, sync, insights |
| `content_ops_status.py` | List drafts, last pack, recent publish log |
| `runtime_path_resolver.py` | Resolve Flexity root path |

### 3.2 Non-ContentOps modules (out of scope M1 migration, не трогать в Cabinet v1)

| Файл | Роль | Примечание |
|------|------|------------|
| `universal_dispatcher.py` | Multi-task dispatch | Отдельный контур AI tasks |
| `margosya_dispatcher.py` | Task routing | Не content |
| `margosya_worker_runner.py` | Auto worker | Publishing preflight tasks |
| `approval_state.py` | Generic approval files | `approval_requests/` — не content pack |
| `integrations/github/github_issue_sync.py` | GitHub sync | После approve tasks |
| `daily_content_draft.py` | Deprecated | Redirect на новый flow |

**Правило:** Marketing Cabinet **не заменяет** universal dispatch / worker / generic approvals.

---

## 4. Commands & UI inventory

### 4.1 Telegram commands (ContentOps)

| Команда | Handler | Делает | Target Cabinet entity |
|---------|---------|--------|----------------------|
| `/daily_content_topic` | `content_bank_selector.run_daily_content_topic` | Suggested approved topic | Content Topic + selector |
| `/daily_content_topic_next` | `run_daily_content_topic_next` | Другая тема без дублей | Content Topic rotation |
| `/create_content_pack_from_text` | pending intake → `create_content_pack_from_text` | Pack из секций | Publication Pack |
| `/attach_visual_asset <slug>` | `visual_asset_attach` | Upload image | Media Asset |
| `/list_content_drafts` | `content_ops_status.list_content_drafts` | Pending packs | Packs list filter |
| `/last_content_pack` | `content_ops_status.last_content_pack` | Latest by mtime | Dashboard / Packs |
| `/recent_publish_log` | `content_ops_status.recent_publish_log` | Last log event | Publish Log |
| `/preflight_content_pack <slug>` | `content_ops_publish.preflight_content_pack` | Dry-run checks | Preflight status |
| `/approve_content_pack <slug>` | `approve_content_pack` | Status → approved | Approve status |
| `/publish_approved <slug>` | `publish_approved` | TG+IG via GHA | Publish Queue + Log |
| `/publish_threads_approved <slug>` | `publish_threads_approved` | Threads script | Publish Queue (threads) |
| `/publish_tiktok_approved <slug>` | `publish_tiktok_approved` | TikTok script | Publish Queue (tiktok) |
| `/publish_insights_site <slug>` | `publish_insights_site` | Article + deploy | Publish Log (insights) |
| `/daily_content_draft` | deprecated message | Показывает новый flow | — |

### 4.2 Button menus (`telegram_contentops_menu.py`)

| UI element | Action | API target (future) |
|------------|--------|---------------------|
| 📝 Контент → 🎯 Выбрать тему дня | `menu:action:daily_topic` | `GET /topics/suggested` |
| 🔄 Другая тема | `menu:action:daily_topic_next` | `GET /topics/suggested?exclude=...` |
| ✅ Взять эту тему (inline) | `topic:accept:<id>` | `POST /packs` (start draft) |
| 📦 Создать pack из текста | hint only | `POST /packs` |
| Шаги 1–4 intake | text messages | `PATCH /packs/{id}/channels/*` |
| 🧪 Preflight (inline) | `pack:preflight:<dir>` | `POST /packs/{id}/preflight` |
| ✅ Approve (inline) | `pack:approve:<dir>` | `POST /packs/{id}/approve` |
| 🚀 Publish (inline) | `pack:publish:<dir>` | `POST /packs/{id}/publish` |
| 🔄 Sync main | `pack:sync:<dir>` | `POST /packs/{id}/sync` (transition) |
| 🧵 Threads / 🎵 TikTok | channel publish | `POST /packs/{id}/publish?channel=...` |
| 👀 Pending packs | `list_content_drafts` | `GET /packs?status=draft` |

### 4.3 Commands NOT found (из старых планов)

| Команда | Статус |
|---------|--------|
| `/dry_run_approved_publish` | ❌ Не существует (заменена `/preflight_content_pack`) |
| `/run_approved_publish` | ❌ Не существует (заменена `/publish_approved`) |

---

## 5. User flows (as-is)

### 5.1 Recommended flow (step intake)

```text
1. Кнопка «Выбрать тему дня» или /daily_content_topic
2. Inline «Взять эту тему» → start_step_intake_from_topic()
3. Шаг 1/4 Telegram text
4. Шаг 2/4 Instagram text
5. Шаг 3/4 Threads text
6. Шаг 4/4 Insights text
7. create_content_pack_from_text() → pack dir с insights.md
8. /attach_visual_asset <slug> + photo
9. /preflight_content_pack <slug>
10. /approve_content_pack <slug>
11. /publish_approved <slug>  (+ optional /publish_insights_site)
```

**State during intake:** `state/content_pack_step_intake.jsonl` (per Telegram user).

### 5.2 Legacy flow (pack from text)

```text
1. /create_content_pack_from_text <topic_id> <date> <slug>
2. Одно сообщение с ---telegram--- / ---instagram--- / ---threads---
3. Pack БЕЗ insights.md
4. Дальше attach → preflight → approve → publish
```

**State:** `state/content_pack_intake.jsonl`.

### 5.3 ContentOps intake contract (не рекомендуется)

```text
---contentops-intake---
topic_id, date, slug, title, angle
---telegram--- ... ---insights--- ... ---visual---
---end-contentops-intake---
```

Парсится `parse_contentops_intake_block()`. Проблема: Telegram разбивает длинные сообщения → fail.

### 5.4 Publish pipeline (technical)

```text
preflight_content_pack()
    → file checks (pack.yml, telegram.md, instagram.md, …)
    → asset check / generate_social_assets.py
    → public HTTP check image URL
    → reconcile_publish_state_from_origin() (git)
    → scan_*_eligible() via Flexity scripts (dry-run)
    → fail-closed validation

approve_content_pack()
    → requires preflight pass
    → sets pack.status=approved, channel statuses

publish_approved()
    → GitHub workflow dispatch (telegram-publish.yml, instagram-publish.yml)
    → workflow updates pack yml + publish_log.yml in repo

publish_insights_site()
    → sync_insights_article_from_pack()
    → run_generate_insights()
    → deploy_landing_www()
```

---

## 6. Data artifacts (current source of truth)

### 6.1 Content bank (topics)

| Поле | Где |
|------|-----|
| Location | `Flexity/docs/content/flexity-content-bank.md` |
| Format | YAML blocks in markdown |
| Read by | `content_bank_selector.parse_content_bank()` |
| Write | Manual edit in git (Cursor) |
| Cabinet target | `Content Topic` table + optional sync from markdown |

**Approved topics:** ~15+ entries (CB-2026-06-28-001 … 015+).

### 6.2 Publication pack (per slug)

Типичная структура директории `landing/content/content-packs/<date>-<slug>/`:

| File | Назначение | Cabinet mapping |
|------|------------|-----------------|
| `pack.yml` | Metadata, status, content_bank.topic_id, publish.* | Publication Pack |
| `telegram.md` | Telegram post text | Pack.texts.telegram |
| `instagram.md` | Instagram caption | Pack.texts.instagram |
| `threads.md` | Threads text | Pack.texts.threads |
| `insights.md` | Site article body | Pack.texts.insights |
| `instagram.yml` | IG post type, media refs, status | Channel config + Media |
| `threads.yml` | Threads publish metadata | Channel config |
| `tiktok.yml` | TikTok metadata (optional) | Channel config |
| `visual.yml` | Visual brief | Media Asset metadata |
| `publish_log.yml` | events[] audit trail | Publish Log |

**Пример реального pack:** `2026-07-07-ai-v-gossektore` — approved, TG+IG published, insights present.

**Pack count в repo:** 16 directories (на момент аудита).

### 6.3 Media assets

| Поле | Где |
|------|-----|
| File | `landing/www/assets/social/<pack_dir>/instagram-feed.png` |
| Public URL | `https://www.flexity.asia/assets/social/<pack_dir>/instagram-feed.png` |
| Upload | Margosya `visual_asset_attach.py` (PIL normalize 1080×1080) |
| Cabinet target | Media Asset + storage ref |

### 6.4 Insights articles

| Поле | Где |
|------|-----|
| Source markdown | `pack/insights.md` или `landing/content/articles/*.md` |
| Generated HTML | `landing/www/insights/<slug>.html` |
| Public URL | `https://www.flexity.asia/insights/<slug>` |

### 6.5 Margosya local state (NOT source of truth)

| File | Назначение | Migrate? |
|------|------------|----------|
| `state/daily_content_topic_session.json` | Proposed topics per user/day | → ephemeral; Cabinet stores plan |
| `state/content_pack_step_intake.jsonl` | In-progress step intake | → draft pack in Cabinet |
| `state/content_pack_intake.jsonl` | Legacy pending intake | → draft pack in Cabinet |
| `state/visual_asset_intake.jsonl` | Pending photo upload | → upload session in API |

**Правило:** при переходе на Cabinet API эти файлы **не переносятся** как SoT — только как migration reference.

### 6.6 Secrets & external deps

| Secret / dep | Used by | Cabinet note |
|--------------|---------|--------------|
| `TELEGRAM_BOT_TOKEN` | margosya-bot | Stays in Margosya |
| `GITHUB_TOKEN` | workflow dispatch | Channel Connection vault |
| `FLEXITY_ROOT` / path resolver | filesystem access | Replaced by API |
| Meta Instagram tokens | GHA secrets | Channel Connection |
| Telegram channel config | GHA / scripts | Channel Connection |

---

## 7. Feature matrix: Margosya → Marketing Cabinet

| # | Margosya feature | Current implementation | SoT today | Cabinet entity | MVP? | Gap |
|---|------------------|------------------------|-----------|----------------|------|-----|
| 1 | Topic selection | `content_bank_selector` | markdown bank | Content Topic | ✅ | DB import |
| 2 | Topic rotation / next | session exclude list | JSON session | Content Plan rules | ✅ | API |
| 3 | Duplicate check | scan packs + calendar | filesystem | Preflight rule | ✅ | DB query |
| 4 | Accept topic → intake | step intake | JSONL state | Pack draft | ✅ | API session |
| 5 | Text per channel (4) | step intake / factory | `*.md` files | Pack.texts | ✅ | UI fields |
| 6 | Pack create | `content_pack_factory` | git dir | Publication Pack | ✅ | API |
| 7 | Pack slug / date | factory naming | dir name | Pack.slug | ✅ | — |
| 8 | Visual upload | `visual_asset_attach` | PNG on disk | Media Asset | ✅ | storage layer |
| 9 | Visual preview | public URL check | HTTP | Media preview | ✅ | signed URL |
| 10 | Preflight | `preflight_content_pack` | computed report | Preflight status | ✅ | persist report |
| 11 | Approve | `approve_content_pack` | pack.yml status | Approve status | ✅ | audit |
| 12 | Publish TG+IG | GHA dispatch | publish_log | Publish Queue | ✅ | in-process later |
| 13 | Publish Insights | `publish_insights_site` | HTML on site | Publish Log | ✅ | — |
| 14 | Publish Threads | script | threads.yml | Publish Queue | ⚠️ | lower priority |
| 15 | Publish TikTok | script | tiktok.yml | Publish Queue | ❌ later | not MVP |
| 16 | Publish log view | `recent_publish_log` | publish_log.yml | Publish Log | ✅ | DB |
| 17 | Drafts list | `list_content_drafts` | pack.yml status | Packs filter | ✅ | — |
| 18 | Last pack | `last_content_pack` | mtime | Dashboard | ✅ | — |
| 19 | Sync to origin/main | `sync_pack_to_origin_main` | git ops | — | ⚠️ transition | optional post-API |
| 20 | Scheduled publish | `publish_at` in pack.yml | yaml | Queue scheduled_at | ⚠️ | scheduler UI |
| 21 | Retry failed | manual re-run commands | — | Queue retry | ⚠️ | MVP manual |
| 22 | Reminders | — | — | Reminder | ❌ | new in Cabinet |
| 23 | Content Plan calendar | — | — | Content Plan Item | ❌ | new in Cabinet |
| 24 | Campaign / Offer | — | — | Campaign, Offer | ❌ | post-MVP |
| 25 | Lead attribution | — | Core WorkItem | Lead Attribution | ⚠️ manual MVP | new |
| 26 | Demo access | — | — | Demo access note | ⚠️ manual MVP | new |
| 27 | Analytics | — | — | Reports | ❌ | manual metrics |
| 28 | Channel health | preflight HTTP checks | ephemeral | Channel Connection | ⚠️ | persist status |
| 29 | Button UI | telegram menus | — | Console UI | ✅ | new frontend |
| 30 | Error notifications | bot reply text | — | Reminder → Margosya | ⚠️ | webhook |

---

## 8. Business logic to preserve (migration-critical)

Эти правила **нельзя потерять** при переносе в Cabinet:

### 8.1 Fail-closed gates

| Gate | Source |
|------|--------|
| No content bank → no topic | `content_bank_selector._load_bank_context` |
| No approved topics → stop | `run_daily_content_topic` |
| Duplicate check failed → stop | `collect_usage_signatures` errors |
| All topics used → stop | `no_available_topics` |
| Pack exists for date+slug → stop | `pack_dir_exists` |
| Preflight failed → no approve | `approve_content_pack` checks |
| Approve required → no publish | `publish_approved` checks |
| Already published → block | `published_at` guards |
| Instagram image HTTP ≠ 200 → block | preflight |
| Pack not on origin/main → warn/block GHA publish | preflight WARN |
| Telegram text > 4096 → warn | preflight |

### 8.2 Topic selection algorithm

```text
approved topics
  → filter used (by topic_id / title match in packs + calendar)
  → filter business-chaos rubric if recent posts had chaos topics
  → pick least-used rubric
  → sort by topic id
```

**Cabinet:** воспроизвести как `TopicSelectorService` с DB queries вместо filesystem scan.

### 8.3 Pack status lifecycle

```text
draft / pending_approval
  → preflight (ephemeral)
  → approved (pack.yml status + channel statuses)
  → published (published_at per channel in yml + publish_log events)
```

**Cabinet statuses:** map 1:1 на `approve_status` + `publish_status` из product TZ.

### 8.4 Publish log event schema (interim)

```yaml
events:
  - at: ISO datetime
    channel: telegram | instagram | content_pack | ...
    status: published | approved | failed
    message_id / external_id: optional
    by: asem
    content_bank:
      topic_id: CB-...
```

**Cabinet:** `Publish Log` entity; сохранить совместимость полей для migration script.

---

## 9. Flexity scripts dependency map

Margosya вызывает Flexity scripts через `_run_flexity_script()`:

| Script area | Purpose | Cabinet MVP strategy |
|-------------|---------|---------------------|
| `scripts/content/publish_telegram.py` | TG dry-run + publish | Keep scripts; Cabinet triggers |
| Instagram publisher scripts | IG dry-run + publish | Keep scripts |
| `generate_insights.py` / similar | Site generation | Keep scripts |
| `generate_social_assets.py` | Auto visual | Optional trigger from preflight |
| GitHub Actions workflows | Live publish | Keep; Cabinet dispatches |

**MVP recommendation (from TZ):** Cabinet owns metadata; publish workers stay as scripts/GHA initially.

---

## 10. Test coverage inventory

ContentOps-related tests in `margosya-os/scripts/`:

| Test file | Covers |
|-----------|--------|
| `test_daily_content_topic_command.py` | Topic selection |
| `test_create_content_pack_from_text.py` | Pack factory |
| `test_content_pack_step_intake.py` | Step intake |
| `test_contentops_intake_contract.py` | Intake contract parsing |
| `test_content_ops_publish_commands.py` | Preflight/approve/publish |
| `test_visual_asset_upload.py` | Image attach |
| `test_telegram_contentops_menu.py` | Menu callbacks |

**Gap:** нет integration test Cabinet API (ещё не существует). При M6 — port key scenarios as Flexity backend tests.

---

## 11. Gap analysis (MVP vs as-is)

### 11.1 Already works — migrate, don't rewrite

| Capability | Action |
|------------|--------|
| Topic selector logic | Port to Flexity service |
| Pack file structure | Import into DB; optional git mirror |
| Preflight checklist | Port rules to Cabinet service |
| Publish via GHA | Cabinet triggers same workflows |
| Visual normalize | Reuse `visual_asset_attach` logic or call as lib |

### 11.2 Missing — build new in Cabinet

| Capability | Priority |
|------------|----------|
| PostgreSQL entities | P0 |
| Console UI (10 sections) | P0 |
| Content Plan calendar/list | P0 |
| Reminders | P1 |
| Lead Attribution manual | P1 (MVP) |
| Demo access notes | P1 (MVP) |
| Channel Connections UI | P2 |
| Margosya API | P0 for thin client |

### 11.3 Defer

| Capability | Why |
|------------|-----|
| TikTok live publish | Not daily ops |
| Auto AI generation | Out of MVP |
| Full scheduler + retries | Manual first |
| Object storage S3 | Interim file paths |
| Multi-tenant content | Dogfood flexity-sales only |

### 11.4 Transition risks

| Risk | Mitigation |
|------|------------|
| Dual SoT (DB + git packs) | Cabinet writes DB; export to git optional during transition |
| Breaking Margosya mid-migration | Feature flag: API vs filesystem |
| GHA publish expects repo files | Keep export step until publishers read API |
| Server path `/opt/flexity/coreops` | Document in M4 API deploy contract |

---

## 12. What remains in Margosya (confirmed by audit)

После Cabinet API:

| Keep in Margosya | Remove from Margosya (move to Cabinet) |
|------------------|----------------------------------------|
| Telegram polling / send_message | `content_pack_factory` filesystem writes |
| Reply + inline keyboards | `content_bank_selector` direct markdown read |
| Photo download from Telegram | `content_ops_publish` YAML mutations |
| Command parsing → API calls | Local JSONL intake state as SoT |
| User whitelist | Duplicate / preflight business rules |
| Notification formatting | `publish_log.yml` append |
| Emergency publish trigger | Pack status ownership |

---

## 13. Proposed API surface (preview for M4)

На основе аудита — минимальный contract:

```text
GET  /marketing/topics/suggested
GET  /marketing/topics
POST /marketing/packs
GET  /marketing/packs/{id}
PATCH /marketing/packs/{id}/channels/{channel}
POST /marketing/packs/{id}/media
POST /marketing/packs/{id}/preflight
POST /marketing/packs/{id}/approve
POST /marketing/packs/{id}/reject
POST /marketing/packs/{id}/publish
GET  /marketing/packs?status=draft|approved|published
GET  /marketing/publish-log/recent
GET  /marketing/content-plan?from=&to=
POST /marketing/attributions
GET  /marketing/reminders/pending
```

Детали — в M4.

---

## 14. Architecture classification

| Layer | Classification |
|-------|----------------|
| Marketing Cabinet module | `universal_module` (marketing/content) |
| Lead / Client | `platform_core` (existing CRM) |
| Margosya | External thin client (not Flexity module) |
| Publish scripts | Flexity infra scripts (interim) |
| Content bank markdown | `industry_template` seed / interim import |

---

## 15. Do not touch (M1 stop-list)

| # | Item |
|---|------|
| 1 | `margosya-os` production code |
| 2 | Telegram bot deploy |
| 3 | GitHub Actions workflows |
| 4 | Channel tokens / `.env` |
| 5 | Live publish |
| 6 | `flexity-content-bank.md` content (unless separate editorial task) |
| 7 | Core public inbound branch |
| 8 | Booking / Clinic / Trailers |

---

## 16. Recommended next steps

| Step | Deliverable | Approval |
|------|-------------|----------|
| **M2** | Data model draft — tables, FKs, Core link | HQ review |
| **M3** | UI wireframe plan — 10 sections | HQ review |
| **M4** | API contract — OpenAPI draft | HQ review |
| **M5** | MVP implementation plan — exact files | **Explicit HQ approval** |
| **M6** | First code slice | After M5 |

### M2 inputs from this audit

1. Use entity list from product TZ §6.
2. Add `pack_dir_name` / `slug` legacy fields for git import.
3. Map `publish_log.yml` events → `PublishLog` rows.
4. Map content bank YAML → `ContentTopic` seed.
5. Define `LeadAttribution.work_item_id` FK to Core.

---

## 17. HQ summary (M1)

| # | Item | Answer |
|---|------|--------|
| 1 | Margosya ContentOps mature? | **Yes** for daily TG/IG flow; partial for Threads/TikTok |
| 2 | Current SoT? | **Flexity git repo** (packs + content bank), not Margosya state |
| 3 | Features to move? | **30 items** in matrix §7; core 18 in MVP |
| 4 | Features to keep in bot? | Transport, buttons, photo intake, notifications |
| 5 | Biggest gap? | **No API/DB**, no Content Plan, no attribution, no reminders |
| 6 | Biggest risk? | Dual SoT during transition; breaking GHA publish chain |
| 7 | Next step? | **M2 Data model draft** |
| 8 | Implementation approval needed? | **Yes** (M5+) |

---

*Аудит выполнен read-only. Код, migrations, deploy, production и Telegram bot не изменялись.*
