# Marketing Cabinet / ContentOps Cabinet — Product TZ

**Дата:** 2026-07-03  
**Проект:** Flexity / `coreops-platform`  
**Ветка / направление:** Marketing Cabinet / ContentOps Cabinet — product TZ  
**Категория:** `documentation_only`  
**Статус:** product specification — **код не менялся, implementation не начиналась**

**HQ decision (2026-07):** прекращаем стратегию бесконечной доработки Маргоси как основной системы. Marketing Cabinet / ContentOps Cabinet внутри Flexity становится **source of truth** для контент-операций. Маргося остаётся **Telegram thin client**.

**Связанные документы:**
- [FLEXITY_HQ_STRUCTURE_CONTENT_CABINET_PLAN.md](../../FLEXITY_HQ_STRUCTURE_CONTENT_CABINET_PLAN.md)
- [FLEXITY_CORE_HQ_FUNNEL_DECISION_MEMO.md](../../FLEXITY_CORE_HQ_FUNNEL_DECISION_MEMO.md)
- [FLEXITY_ASSEMBLY_WORKING_CONTOUR_PLAN.md](../../FLEXITY_ASSEMBLY_WORKING_CONTOUR_PLAN.md)
- [docs/content/flexity-content-bank.md](../../content/flexity-content-bank.md)
- [margosya-os/docs/MARGOSYA_CONTENTOPS_RUNBOOK.md](https://github.com/) — interim runbook (отдельный репозиторий)

---

## Task Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `documentation_only` |
| **Risk level** | low (только документ) |
| **Intended scope** | `docs/ai/plans/2026-07-03-marketing-content-cabinet-product-tz.md` |
| **Forbidden scope** | код, migrations, production, deploy, publish, env/secrets, Telegram bot, Core public inbound, Booking / Clinic / Trailers |
| **Required plan** | product TZ (этот документ) |

---

## 1. Product vision

### 1.1 Что такое Marketing Cabinet

**Marketing Cabinet** — рабочий кабинет Асем для управления маркетингом, контентом, публикациями и входящим интересом внутри Flexity.

Это не отдельная CRM и не автономный контент-генератор. Это **операционный интерфейс** поверх Flexity Core, который закрывает ежедневный цикл:

```text
контент → публикация → реакция → лид → диагностика → клиент
```

### 1.2 Главная идея

Асем должна работать **без помощника** в рутине контента и маркетинга:

| Задача | Как помогает кабинет |
|--------|----------------------|
| Планировать контент | Content Plan, Topics, Calendar |
| Публиковать | Publication Packs, Preflight, Approve, Publish Queue |
| Отслеживать реакции | Publish Log, manual/social lead intake |
| Видеть, что работает | Простая эффективность контента (MVP — manual metrics) |
| Регистрировать интерес | Lead Attribution, связь с Core |
| Передавать лиды в Core | WorkItem в `flexity-sales`, без второй CRM |

### 1.3 Позиционирование

| Было (interim) | Становится (target) |
|----------------|---------------------|
| Маргося = основной интерфейс ContentOps | Marketing Cabinet = source of truth |
| Markdown content bank + repo packs | PostgreSQL metadata + UI |
| Команды `/preflight_*`, `/publish_*` в Telegram | UI + API; Маргося — thin client |
| `publish_log.yml` в git | Publish Log в Flexity + audit |

### 1.4 Принципы продукта

1. **Fail-closed:** нет approved topic → нет draft pack; нет approve → нет publish.
2. **Single source of truth:** все статусы, планы, packs, media metadata — в Flexity.
3. **No duplicate CRM:** лиды создаются в Core как `WorkItem`, не в Marketing Cabinet.
4. **Dogfooding:** первый пользователь — Асем (`flexity-sales` tenant).
5. **Parallel development:** кабинет развивается параллельно с Core, подключается через leads, sources, campaigns, content attribution.

---

## 2. Role in Flexity ecosystem

### 2.1 Слои экосистемы

```text
                         ┌─────────────────────────────────────┐
                         │         Асем (владелец)              │
                         └───────────┬─────────────┬───────────┘
                                     │             │
                         Console UI  │             │  Telegram
                                     ▼             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        FLEXITY CORE (source of truth)                     │
│  ┌─────────────┐  ┌──────────────────────┐  ┌─────────────────────────┐ │
│  │ HQ Cabinet  │  │  Marketing Cabinet    │  │  Universal modules      │ │
│  │ flexity-    │  │  offer·campaign·      │  │  CRM·documents·finance  │ │
│  │ sales       │  │  content·attribution  │  │  audit·workflows        │ │
│  └──────┬──────┘  └──────────┬───────────┘  └─────────────────────────┘ │
│         │                    │                                            │
│         └────────────────────┴───────────────────────────────────────────│
│                    PostgreSQL (+ object storage для media)                 │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        ┌──────────┐     ┌────────────┐    ┌─────────────┐
        │ Website  │     │  Margosya  │    │  Channels   │
        │ Insights │     │  thin      │    │ TG·IG·      │
        │ /demo    │     │  client    │    │ Threads·etc │
        └──────────┘     └────────────┘    └─────────────┘
```

### 2.2 Flexity Core

**Ответственность:** бизнес-операции, клиенты, продажи, внедрение.

| Область | Сущности / модули |
|---------|-------------------|
| Лиды | `WorkItem` + `Party` (`party_role=lead`) |
| Клиенты | `Party` (`party_role=client`) |
| Проекты | WorkItem type / Project (TBD) |
| Tenants | `flexity-sales` (internal) → real tenant клиента |
| Задачи | Activities / WorkItem tasks |
| Документы | `DocumentInstance` (КП, договоры) |
| Продажи | CRM kanban, stages, conversion |

**Правило:** Core **не** хранит draft-тексты Instagram и очередь публикаций — это Marketing Cabinet. Core **хранит** lead, client, project и ссылки на attribution metadata.

### 2.3 Marketing Cabinet

**Ответственность:** маркетинговый контур от offer до attribution.

| Область | Сущности |
|---------|----------|
| Offer | Что продаём, CTA, target audience |
| Campaign | Период, каналы, цель, UTM |
| Content Plan | Календарь, слоты, статусы |
| Topics | Approved ideas из content bank |
| Publication Packs | Тексты по каналам + media |
| Media | Assets, preview, usage |
| Publish Queue | Scheduled / ready / failed |
| Channels | Telegram, Instagram, Insights, Threads |
| Attribution | source, campaign, content_slug → lead |
| Effectiveness | Простые метрики (MVP — manual) |

### 2.4 Content Cabinet (подмодуль)

**Content Cabinet** — практическая часть Marketing Cabinet для ежедневного производства контента.

Можно рассматривать как:
- **подмодуль** Marketing Cabinet (рекомендуется для MVP), или
- отдельный UI-раздел внутри того же tenant workspace.

| Подсистема | Назначение |
|------------|------------|
| Content Plan | Календарь / list, anti-duplicate |
| Media Library | Approved assets, provenance |
| Publication Packs | Draft → approve → publish |
| Publish Queue | Очередь и retries |
| Channel Connections | Токены, health, scopes |
| Reminders | Approval, пропущенный слот, failed publish |

**Interim (до модуля):** `docs/content/flexity-content-bank.md`, `landing/content/content-packs/`, Margosya commands.

### 2.5 Margosya

**Роль:** Telegram thin client — mobile remote control.

| Делает | Не делает |
|--------|-----------|
| Быстрый выбор темы | Не хранит content plan |
| Отправка текстов / фото в draft | Не является source of truth |
| Approve / reject | Не создаёт лиды |
| Напоминания | Не содержит бизнес-логику publish |
| Статус последнего pack | Не придумывает темы |
| Emergency publish command | Не дублирует CRM |

**Target:** Margosya вызывает **Flexity Marketing Cabinet API**, а не владеет pack state.

### 2.6 Website / Insights

**Роль:** публичный входной слой.

| Компонент | Назначение |
|-----------|------------|
| Landing | Позиционирование, CTA |
| Diagnosis page | Вход в диагностику → Lead |
| Lead forms | `/demo/`, embedded forms → Core API |
| Insights articles | SEO-контент из publication packs |
| Traffic source | UTM, content_slug, campaign ref |

**Правило:** сайт — rendered front. Source of truth для контента — Marketing Cabinet; для лидов — Core.

---

## 3. What moves from Margosya into Marketing Cabinet

Весь перечисленный функционал должен жить в Marketing Cabinet (UI + API + PostgreSQL metadata). Маргося только вызывает API и показывает статусы.

### 3.1 Планирование и темы

| Функция Margosya (сейчас) | Куда переезжает |
|---------------------------|-----------------|
| `/daily_content_topic` — выбор темы | Topics list + selector в Content Plan |
| `/daily_content_topic_next` — другая тема | Topic rotation / duplicate check в кабинете |
| Topic status (approved / used) | `Content Topic.status`, `used_at` |
| Content bank reference (`topic_id`) | Import / sync из `flexity-content-bank.md` → Topics DB |
| Anti-duplicate за день | Content Plan rules + preflight |

### 3.2 Создание и редактирование pack

| Функция | Куда переезжает |
|---------|-----------------|
| Пошаговый intake: Telegram → Instagram → Threads → Insights | Publication Pack detail — text fields per channel |
| `/create_content_pack_from_text` (legacy) | Pack create form / paste-all mode |
| `---contentops-intake---` contract parsing | API endpoint `POST /packs` (Margosya → API) |
| Content pack slug, date, title, angle | Pack metadata в кабинете |
| Draft / pending_approval / approved status | Pack workflow states |

### 3.3 Медиа

| Функция | Куда переезжает |
|---------|-----------------|
| `/attach_visual_asset <slug>` | Media Library upload + link to pack |
| Visual preview | Media Asset preview в UI |
| Public URL для Instagram | Channel-specific media ref + storage status |
| `visual.yml` metadata | Media Asset fields |

### 3.4 Preflight, approve, publish

| Функция | Куда переезжает |
|---------|-----------------|
| `/preflight_content_pack <slug>` | Preflight action в UI + API |
| Preflight checklist (gates, duplicate, visual) | Preflight status + report view |
| `/approve_content_pack <slug>` | Approve button + audit |
| `/publish_approved <slug>` | Publish now / schedule |
| `/publish_insights_site <slug>` | Publish to Insights channel |
| Publish to Telegram | Channel publish via queue |
| Publish to Instagram | Channel publish via queue |
| Scheduled publish later | Publish Queue Item `scheduled_at` |

### 3.5 Логи и статусы

| Функция | Куда переезжает |
|---------|-----------------|
| `/last_content_pack` | Dashboard + Packs list (last) |
| `/list_content_drafts` | Packs filter: draft |
| `/recent_publish_log` | Publish Log view |
| `publish_log.yml` events | Publish Log entity в PostgreSQL |
| Error status после failed publish | Publish Queue Item.error + retry |
| Retry publish | Publish Queue retry action |

### 3.6 Напоминания

| Функция | Куда переезжает |
|---------|-----------------|
| «Сегодня нет публикации» | Reminder entity + Dashboard alert |
| «Нужно approve» | Reminder + pending approve widget |
| «Publish failed» | Reminder + failed publish widget |

### 3.7 Interim assets (миграция данных)

| Сейчас | Target |
|--------|--------|
| `landing/content/content-packs/<slug>/` | Publication Pack records + optional git mirror (transition) |
| `docs/content/flexity-content-bank.md` | Content Topics import / sync |
| `landing/www/assets/social/` | Media Library (object storage later) |
| Margosya local state / JSONL | Удалить как source of truth; только API cache |

---

## 4. What remains in Margosya

Маргося **остаётся** как Telegram thin client для мобильных и быстрых действий.

### 4.1 Сценарии использования

| Сценарий | Поведение |
|----------|-----------|
| Нет доступа к компьютеру | Выбор темы, отправка текста, загрузка фото через Telegram |
| Быстрый approve / reject | Inline buttons → API `POST /packs/{id}/approve` или `reject` |
| Напоминание «сегодня нет публикации» | Push от Flexity Reminder service → Margosya notification |
| Уведомление «publish failed» | Webhook / poll status → alert в Telegram |
| Уведомление «нужно approve» | Pending approve reminder |
| Публикация по расписанию | Flexity scheduler triggers publish; Margosya только подтверждает статус |
| Быстрый статус «последний pack» | `GET /packs/last` → formatted message |
| Emergency / fallback publish | Explicit command с HQ guard; вызывает API, не локальную логику |

### 4.2 Архитектурные правила Margosya

```text
Асем (Telegram)
    → Margosya (transport + UI)
        → Flexity Marketing Cabinet API
            → PostgreSQL (source of truth)
            → Publish workers / channel adapters
```

| Правило | Детали |
|---------|--------|
| **API-first** | Все create/update/publish — через Flexity API |
| **No local SoT** | Margosya не хранит pack state как primary |
| **Read topics from Cabinet** | Не читать markdown bank напрямую (target) |
| **Fail-closed** | API unavailable → сообщение об ошибке, не fallback на local pack |
| **Audit** | Approve/publish через API → audit module |

### 4.3 Команды Margosya (target mapping)

| Команда (interim) | Target API |
|-------------------|------------|
| `/daily_content_topic` | `GET /topics/suggested?date=...` |
| Step intake texts | `PATCH /packs/{id}/channels/{channel}` |
| `/attach_visual_asset` | `POST /packs/{id}/media` |
| `/preflight_content_pack` | `POST /packs/{id}/preflight` |
| `/approve_content_pack` | `POST /packs/{id}/approve` |
| `/publish_approved` | `POST /packs/{id}/publish` |
| `/publish_insights_site` | `POST /packs/{id}/publish?channel=insights` |
| `/last_content_pack` | `GET /packs/last` |
| `/recent_publish_log` | `GET /publish-log/recent` |

---

## 5. Main user flows

### Flow A — создать публикацию из кабинета

**Актор:** Асем (desktop, Console UI)

```text
1. Открыть Marketing Cabinet (tenant: flexity-sales)
2. Выбрать дату в Content Plan
3. Выбрать тему (из approved Topics) или создать plan item
4. Выбрать каналы: Telegram, Instagram, Threads, Insights
5. Написать / вставить тексты по каналам
   (опционально: AI assist — не MVP)
6. Загрузить медиа (image для Instagram feed)
7. Запустить Preflight
   → duplicate check, required fields, visual gate
8. Approve (self-approve для Асем)
9. Publish now ИЛИ Schedule на datetime
10. Смотреть статус в Publish Queue / Publish Log
```

**Результат:** pack в статусе `published` (или `scheduled`), записи в Publish Log, topic `used_at` обновлён.

### Flow B — создать публикацию через Маргосю

**Актор:** Асем (mobile, Telegram)

```text
1. Открыть Telegram → Margosya
2. «Выбрать тему дня» → API возвращает suggested topic
3. Пошагово отправить тексты (TG / IG / Threads / Insights)
   ИЛИ одним блоком (legacy contract)
4. Загрузить фото (если нужно)
5. Margosya создаёт draft pack через API
6. Marketing Cabinet хранит pack (source of truth)
7. Preflight / Approve — через кнопки в Telegram ИЛИ позже в UI
8. Publish идёт через Cabinet API + publish workers
9. Margosya показывает статус (polling / push)
```

**Результат:** тот же pack, что и в Flow A. UI и Telegram — два интерфейса к одному объекту.

### Flow C — контент дал интерес

**Актор:** Потенциальный клиент → Асем

```text
1. Публикация опубликована (Telegram / Instagram / Insights)
2. Человек написал в DM / оставил заявку / перешёл на сайт
3. В Marketing Cabinet фиксируется attribution:
   - channel (telegram, instagram, website, manual)
   - content_slug / pack_id
   - campaign_id (если есть)
   - topic_id
4. Асем создаёт lead в Core (или public inbound API создаёт автоматически)
5. Lead Attribution связывает lead_id ↔ pack_id ↔ campaign
6. Лид попадает в flexity-sales CRM kanban
7. Позже «Сделать клиентом» (guided conversion в Core)
```

**MVP:** manual social lead intake + manual attribution fields. Auto — позже.

### Flow D — демо-доступ

**Актор:** Асем → заинтересованный лид

```text
1. Лид заинтересовался (из Flow C)
2. В Core CRM или Marketing Cabinet виден источник (campaign / content / channel)
3. Асем выдаёт demo access на 24–36 часов
4. Demo связано с:
   - lead_id / work_item_id
   - campaign_id
   - content_pack_id (source content)
5. Статус demo: active → expired / converted / revoked
6. После demo — follow-up task в Core
```

**MVP:** manual issue + notes + `expires_at`. Automatic invite link — later.

---

## 6. Core entities / concepts

Будущие сущности Marketing Cabinet. Имена — draft; финальная схема — в M2 (Data model draft).

### 6.1 Marketing Offer

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `title` | Название предложения |
| `description` | Описание ценности |
| `target_audience` | Целевая аудитория |
| `cta` | Call to action |
| `linked_diagnosis` | Ссылка на diagnosis flow / page |
| `status` | draft / active / archived |
| `tenant_id` | `flexity-sales` (MVP) |

### 6.2 Campaign

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `offer_id` | FK → Marketing Offer |
| `name` | Название кампании |
| `period_start`, `period_end` | Период |
| `channels` | Список каналов |
| `budget` | Optional |
| `goal` | leads / awareness / demo / conversion |
| `status` | planned / active / completed / paused |
| `utm_params` | UTM template для attribution |

### 6.3 Content Topic

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID (maps to `CB-YYYY-MM-DD-NNN`) |
| `title` | Заголовок темы |
| `rubric` | Рубрика из content bank |
| `angle` | Угол подачи |
| `status` | idea / approved / used / archived |
| `priority` | Для сортировки selector |
| `reusable` | Можно ли использовать повторно |
| `used_at` | Дата последнего использования |
| `source_idea` | Откуда идея (brainstorm, news, manual) |
| `channels` | Рекомендуемые каналы |

### 6.4 Content Plan Item

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `date` | Плановая дата публикации |
| `topic_id` | FK → Content Topic |
| `channels` | Планируемые каналы |
| `status` | planned / in_progress / done / skipped |
| `campaign_id` | Optional FK |
| `pack_id` | Optional FK → Publication Pack |

### 6.5 Publication Pack

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `slug` | URL-safe identifier |
| `topic_id` | FK → Content Topic |
| `campaign_id` | Optional FK |
| `planned_date` | Дата |
| `texts` | JSON: `{telegram, instagram, threads, insights}` |
| `media_asset_ids` | Список FK → Media Asset |
| `preflight_status` | not_run / passed / failed |
| `preflight_report` | JSON checklist results |
| `approve_status` | draft / pending / approved / rejected |
| `approved_at`, `approved_by` | Audit |
| `publish_status` | not_started / partial / published / failed |
| `tenant_id` | Scope |

### 6.6 Media Asset

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `file_ref` | Storage key / path |
| `type` | image / video (later) |
| `preview_url` | Signed URL |
| `channel_usage` | instagram_feed / telegram / etc |
| `storage_status` | pending / stored / failed |
| `visibility` | public / private |
| `pack_id` | Linked pack |
| `alt_text`, `format` | Metadata |
| `uploaded_by` | User ref |

### 6.7 Publish Queue Item

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `pack_id` | FK |
| `channel` | telegram / instagram / insights / threads |
| `scheduled_at` | Nullable (null = immediate) |
| `status` | ready / scheduled / publishing / published / failed |
| `retries` | Count |
| `error` | Last error message |
| `external_id` | Platform message/post id |

### 6.8 Channel Connection

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `channel_type` | telegram / instagram / insights / threads |
| `account_name` | Channel / page name |
| `health_status` | healthy / degraded / down |
| `token_status` | valid / expiring / invalid |
| `last_check_at` | Timestamp |
| `scopes` | Permissions (no secret in DB row — ref to vault) |
| `tenant_id` | Scope |

### 6.9 Publish Log

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `pack_id` | FK |
| `channel` | Channel type |
| `published_at` | Timestamp |
| `external_url` | Link to post / article |
| `status` | success / failed |
| `error` | If failed |
| `metadata` | Platform-specific ids |

### 6.10 Lead Attribution

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `lead_id` | FK → Core WorkItem |
| `party_id` | FK → Core Party |
| `channel` | Source channel |
| `content_slug` | Pack slug / article slug |
| `pack_id` | FK → Publication Pack |
| `campaign_id` | Optional FK |
| `source` | website / telegram / instagram / manual / referral |
| `first_touch_at` | Timestamp |
| `last_touch_at` | Timestamp |
| `utm_json` | UTM parameters |

### 6.11 Reminder

| Поле | Тип / описание |
|------|----------------|
| `id` | UUID |
| `type` | no_publication_today / needs_approve / publish_failed / custom |
| `due_at` | When to fire |
| `message` | Text for notification |
| `target_pack_id` | Optional |
| `target_campaign_id` | Optional |
| `status` | pending / sent / dismissed |
| `delivery_channel` | console / margosya / both |

---

## 7. MVP scope

MVP — первый рабочий срез Marketing Cabinet для Асем (`flexity-sales`), без multi-client SaaS.

### 7.1 Входит в MVP

| # | Capability | Детали |
|---|------------|--------|
| 1 | **Content Topics list** | Import из content bank; статусы approved/used |
| 2 | **Content Plan calendar/list** | Плановые даты + topic + status |
| 3 | **Publication Pack detail** | CRUD draft pack |
| 4 | **Text fields per channel** | Telegram, Instagram, Threads, Insights |
| 5 | **Media upload** | Placeholder / link к existing visual asset logic; file path или signed URL |
| 6 | **Preflight status** | Run preflight + show report (reuse checklist rules) |
| 7 | **Approve status** | Self-approve flow |
| 8 | **Publish status** | Manual trigger publish (может делегировать existing scripts initially) |
| 9 | **Publish Log view** | История публикаций по pack/channel |
| 10 | **Manual source attribution** | Поля на lead note / attribution record |
| 11 | **Manual social lead intake** | «Написал в Instagram» → create/link lead |
| 12 | **Link to Core lead** | `work_item_id`, `party_id` на attribution |
| 13 | **Demo access note/status** | Manual: status + expires_at + notes |
| 14 | **Margosya integration contract draft** | API spec M4; bot не переписывается в MVP slice |

### 7.2 MVP tenant и UI

- **Tenant:** `flexity-sales` only
- **UI path (draft):** `/console/workspace/flexity-sales/marketing/*` или отдельный Marketing section в workspace
- **User:** Асем (owner); роли — см. Open Questions

### 7.3 MVP publish strategy

Допустим **гибрид** на первом срезе:

```text
Marketing Cabinet (metadata SoT)
    → publish action
    → existing scripts (publish_telegram.py, instagram publisher, generate_insights)
    → write back Publish Log to Cabinet
```

Полная замена scripts на in-process publishers — **не MVP**.

### 7.4 MVP storage

- **Metadata:** PostgreSQL
- **Media:** interim — file path / public URL / link to `landing/www/assets/social/`; full object storage — later

---

## 8. Not MVP / later

Явно **не включать** в первый этап:

| # | Capability | Почему later |
|---|------------|--------------|
| 1 | Full ads integration (Meta Ads, Yandex Direct) | Отдельный продуктовый track |
| 2 | Meta Inbox API | Сложная интеграция, не блокер daily ops |
| 3 | WhatsApp Business API | Нет канала в текущем flow |
| 4 | TikTok live publish | Template exists, publish — later |
| 5 | Advanced analytics | Premature; manual metrics first |
| 6 | Auto AI content generation | Асем + ChatGPT вне Flexity; AI assist — CR |
| 7 | Self-service SaaS | Сначала dogfood для Асем |
| 8 | Client white-label | Tenant customization — CR only |
| 9 | Billing | Не блокер HQ funnel |
| 10 | Complex object storage | S3-compatible layer — отдельный slice |
| 11 | Full scheduler with retries across all channels | MVP = manual/semiauto publish |
| 12 | Multi-client content cabinet | Один tenant в MVP |
| 13 | Client-owned storage | Enterprise feature |

---

## 9. UI sections

Будущие разделы Marketing Cabinet в Console.

### 9.1 Dashboard

| Widget | Содержание |
|--------|------------|
| Today's content | Plan item на сегодня + pack status |
| Pending approve | Packs в `pending` |
| Failed publish | Queue items с error |
| New leads from content | Recent attributions |
| Demo access active | Active demo grants |

### 9.2 Content Plan

- Calendar view **или** list view (calendar — open question для MVP)
- Статусы: planned / in_progress / done / skipped
- Filters: date range, rubric, campaign, channel

### 9.3 Topics

| Tab | Содержание |
|-----|------------|
| Ideas | Новые идеи (status=idea) |
| Approved | Готовые к использованию |
| Used | С `used_at` |
| Reusable | Флаг reusable=true |
| Manual input | Добавить тему вручную |

### 9.4 Packs

| Filter | Содержание |
|--------|------------|
| All | Все packs |
| Draft | approve_status=draft |
| Approved | approve_status=approved |
| Published | publish_status=published |
| Failed | publish_status=failed |

Pack detail: texts, media, preflight, approve, publish actions.

### 9.5 Media Library

- Images (MVP)
- Videos (later)
- Linked packs
- Upload + preview

### 9.6 Publish Queue

| Tab | Содержание |
|-----|------------|
| Ready | Готовы к publish |
| Scheduled | С `scheduled_at` |
| Published | Успешные |
| Failed | С error + retry button |

### 9.7 Channels

| Channel | MVP |
|---------|-----|
| Telegram | ✅ |
| Instagram | ✅ |
| Insights (site) | ✅ |
| Threads | ✅ (text only; publish manual/semiauto) |
| TikTok | Later (placeholder) |

Channel detail: connection status, last check, token status (без показа secret).

### 9.8 Leads from Content

- Source, channel, campaign, content_slug
- Link to Core WorkItem / Party
- Manual create attribution
- Manual social intake form

### 9.9 Reports

MVP — простые счётчики:

- Posts published (by channel, by period)
- Leads linked
- Demo access issued
- Manual reactions count (field)

### 9.10 Settings

- Channel connections
- Reminder rules
- Publishing rules (fail-closed gates)
- Content bank sync (manual import MVP)

---

## 10. Integration with Core

### 10.1 Принципы

| Принцип | Реализация |
|---------|------------|
| Tenant-aware | Все marketing entities с `tenant_id` |
| First tenant | `flexity-sales` (internal sales tenant) |
| Leads in Core | `WorkItem` + `Party`; не отдельная lead table |
| Marketing context in Cabinet | source, campaign, content_slug, pack_id |
| Core context | party, project, documents, tasks |
| No Marketing CRM | Не строить kanban лидов в Marketing Cabinet |

### 10.2 Связка через IDs

```yaml
# На WorkItem (Core) — metadata_json или dedicated attribution link
attribution:
  pack_id: "<uuid>"
  campaign_id: "<uuid>"
  topic_id: "<uuid>"
  content_slug: "ai-v-gossektore"
  source: "instagram"
  utm:
    campaign: "july-build-in-public"
    content: "CB-2026-06-28-015"

# На Lead Attribution (Marketing Cabinet)
core:
  work_item_id: "<uuid>"
  party_id: "<uuid>"
```

### 10.3 Потоки интеграции

```text
Website POST /api/v1/public/leads
    → Core: Party + WorkItem
    → Marketing Cabinet: create Lead Attribution (async или manual link)

Marketing Cabinet: manual social lead
    → Core: create WorkItem API
    → Marketing Cabinet: Lead Attribution

Core: «Сделать клиентом»
    → Party role lead → client
    → Attribution preserved for analytics
```

### 10.4 Что не дублировать из Core

- Party / Client card
- CRM kanban
- Document instances (КП)
- Finance / payments
- Project management

Marketing Cabinet показывает **ссылку** на Core entity, не копирует её.

---

## 11. Integration with Margosya

### 11.1 Контракт (target)

**Margosya MUST:**

| Action | API |
|--------|-----|
| Получать suggested topics | `GET /api/v1/marketing/topics/suggested` |
| Создавать draft pack | `POST /api/v1/marketing/packs` |
| Обновлять тексты канала | `PATCH /api/v1/marketing/packs/{id}/channels/{channel}` |
| Загружать media | `POST /api/v1/marketing/packs/{id}/media` |
| Запускать preflight | `POST /api/v1/marketing/packs/{id}/preflight` |
| Approve / reject | `POST /api/v1/marketing/packs/{id}/approve` |
| Запускать publish | `POST /api/v1/marketing/packs/{id}/publish` |
| Получать status | `GET /api/v1/marketing/packs/{id}` |
| Получать reminders | `GET /api/v1/marketing/reminders/pending` |

**Marketing Cabinet MUST:**

| Responsibility | Детали |
|----------------|--------|
| Хранить pack | PostgreSQL — source of truth |
| Хранить статусы | preflight, approve, publish |
| Хранить publish log | Все events |
| Отдавать Margosya | Только API responses + notification webhooks |
| Auth | Service token / user delegation для bot |

### 11.2 Transition period

Пока API не готов:

```text
Margosya → repo packs (interim) ← Marketing Cabinet reads/syncs
```

После M6:

```text
Margosya → API only (repo packs = optional export mirror)
```

### 11.3 Notification flow

```text
Marketing Cabinet: event (needs_approve, publish_failed, no_publication)
    → Reminder record
    → Margosya webhook / poll
    → Telegram message to Асем
```

---

## 12. Integration with Website / Insights

### 12.1 Insights pipeline

```text
Publication Pack (insights text)
    → publish action (channel=insights)
    → generate_insights.py (interim) / CMS API (future)
    → landing/www/insights/<slug>.html
    → Publish Log: external_url
    → Pack linked to live article
```

### 12.2 Lead forms

```text
Visitor on /demo/ or Insights CTA
    → form with hidden fields: content_slug, utm_*, campaign_ref
    → POST /api/v1/public/leads
    → Core: WorkItem
    → Marketing Cabinet: Lead Attribution (auto when API ready)
```

### 12.3 Attribution on site

| Field | Source |
|-------|--------|
| `content_slug` | Article slug / pack slug |
| `utm_campaign` | Campaign UTM |
| `utm_content` | topic_id or pack_id |
| `referrer` | HTTP referrer |

### 12.4 What Marketing Cabinet shows

- Какая статья / пост produced interest
- Click-through from Insights to lead (when tracking available)
- Manual: «этот пост в Telegram принёс 3 DM»

---

## 13. Demo access

Часть sales/marketing activation — связка контента с product trial.

### 13.1 Lifecycle

```text
Lead interested
    → Асем issues demo access (24–36h)
    → status: active
    → expires OR converted OR revoked
    → follow-up task in Core
```

### 13.2 Statuses

| Status | Meaning |
|--------|---------|
| `none` | Demo не выдавался |
| `active` | Доступ открыт, не истёк |
| `expired` | Время вышло |
| `converted` | Стал клиентом |
| `revoked` | Досрочно отозван |

### 13.3 Linkage

```yaml
demo_access:
  lead_id: "<work_item_id>"
  campaign_id: "<optional>"
  pack_id: "<source content>"
  issued_at: "2026-07-10T10:00:00+05:00"
  expires_at: "2026-07-11T22:00:00+05:00"
  status: active
  notes: "Выдан после поста про AI в госсекторе"
```

### 13.4 MVP vs future

| MVP | Future |
|-----|--------|
| Manual issue в UI | Automatic invite link |
| Notes + expires_at | Tenant provisioning hook |
| Status field | Email/Telegram notification |

---

## 14. Analytics MVP

Простой вариант без BI-слоя.

### 14.1 Метрики MVP

| Metric | Source |
|--------|--------|
| Posts published | Publish Log count |
| By channel | Group by channel |
| Leads linked | Lead Attribution count |
| Consultations | Manual flag on WorkItem stage |
| Demo access issued | Demo access records |
| Clients converted | Party role client + attribution |
| Reactions / messages | Manual count field per pack |

### 14.2 MVP UI

- Reports section: таблица / simple counters
- Pack detail: manual «reactions: 5 DMs, 2 comments»
- Dashboard widgets: totals за 7 / 30 дней

### 14.3 Не строить в MVP

- Funnel visualization
- ROI by campaign
- Auto pull from Meta Insights API
- Cohort analysis
- A/B testing

---

## 15. Storage & Security notes

### 15.1 Storage model

| Layer | Technology | Content |
|-------|------------|---------|
| Metadata | PostgreSQL (`coreops`) | All marketing entities, statuses, attribution |
| Object storage | S3-compatible (later) | Images, video, attachments |
| Interim media | File path + public URL | `landing/www/assets/social/` |

### 15.2 Security requirements

| Requirement | Details |
|-------------|---------|
| Tenant isolation | Row-level `tenant_id`; MVP = single tenant |
| Signed URLs | Temporary media access |
| Public / private media | Instagram feed = public URL required; drafts = private |
| Size limits | Per-upload cap (e.g. 10MB image MVP) |
| Audit | Approve, publish, lead create → audit module |
| No secrets in repo | Channel tokens in vault / env only |
| Channel tokens protected | Channel Connection stores ref, not plaintext |
| API auth | Margosya uses scoped service credentials |

### 15.3 Fail-closed rules (carry from content bank)

- No approved topic → no pack create
- No preflight pass → no approve
- No approve → no publish
- No visual for Instagram → Instagram gate fails
- Duplicate topic same day → preflight warning / block

---

## 16. Implementation phases

### M0 — Product TZ ✅

**Текущий документ.** Ждём HQ decision перед любым кодом.

### M1 — Audit Margosya features

| Deliverable | Описание |
|-------------|----------|
| Read-only audit | Все команды, flows, state files |
| Feature matrix | Margosya fn → Cabinet entity mapping |
| Gap analysis | Что не покрыто MVP |

**Output:** `docs/ai/research/2026-07-XX-margosya-to-cabinet-audit.md`

### M2 — Data model draft

| Deliverable | Описание |
|-------------|----------|
| ER diagram | Сущности из раздела 6 |
| Table draft | Поля, indexes, tenant_id |
| Core link spec | FK / metadata_json strategy |

**Output:** `docs/ai/plans/2026-07-XX-marketing-cabinet-data-model-draft.md`  
**No migrations.**

### M3 — UI wireframe plan

| Deliverable | Описание |
|-------------|----------|
| Screen list | 10 UI sections |
| Wireframe descriptions | Без кода |
| Navigation map | Console integration |

**Output:** `docs/ai/plans/2026-07-XX-marketing-cabinet-ui-wireframes.md`

### M4 — API contract draft

| Deliverable | Описание |
|-------------|----------|
| REST endpoints | Marketing Cabinet ↔ Margosya ↔ Core |
| Request/response schemas | OpenAPI draft |
| Auth model | Service token + user context |

**Output:** `docs/ai/plans/2026-07-XX-marketing-cabinet-api-contract.md`

### M5 — MVP implementation plan

| Deliverable | Описание |
|-------------|----------|
| Exact files | Backend module, routes, UI |
| Test plan | pytest + manual smoke |
| Rollback notes | Revert strategy |
| Scope guard | What is NOT in slice |

**Output:** `docs/ai/plans/2026-07-XX-marketing-cabinet-mvp-implementation-plan.md`  
**Requires separate HQ approval.**

### M6 — First implementation slice

| Deliverable | Описание |
|-------------|----------|
| Code | Only after M5 approval |
| First slice | Likely: Topics + Pack CRUD + manual publish log |

**Requires HQ approval. Not started.**

---

## 17. Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| 1 | **Слишком большой scope** | Затяжка, no shipping | Strict MVP; M1–M5 before code |
| 2 | **Дублирование Core CRM** | Две системы лидов | Lead = WorkItem only; attribution link |
| 3 | **Сломать рабочую Маргосю** | Потеря daily publish | Parallel run; API transition; no big-bang |
| 4 | **Хранение токенов** | Security breach | Vault ref; no plaintext in DB |
| 5 | **Privacy** | PII in content / leads | Tenant isolation; minimal data in marketing |
| 6 | **Нет помощника — overload** | Асем burnout | UI-first; reminders; simple flows |
| 7 | **Too much manual attribution** | Неточная аналитика | Accept for MVP; auto later |
| 8 | **Premature analytics** | Wasted effort | Manual metrics only in MVP |
| 9 | **Неготовый storage layer** | Blocked media | Interim file paths; S3 later |
| 10 | **Core instability** | Cabinet on shaky base | Parallel dev; loose coupling via IDs |
| 11 | **Repo packs vs DB drift** | Two sources during transition | Cabinet SoT; repo as export mirror only |

---

## 18. Stop-list

**Сейчас не делать** (до отдельного HQ approval на каждый пункт):

| # | Stop | Reason |
|---|------|--------|
| 1 | Implementation | M0 only |
| 2 | Migration | No schema change |
| 3 | Deploy | Documentation phase |
| 4 | Production changes | — |
| 5 | Moving bot logic to Cabinet | Margosya stays thin |
| 6 | Changing Telegram bot code | Forbidden scope |
| 7 | Publishing | No live publish from this TZ |
| 8 | Channel token changes | Security |
| 9 | Billing | Out of scope |
| 10 | White-label | CR only |
| 11 | Industry modules | Booking / Clinic / Trailers |
| 12 | Core public inbound changes | Separate track |
| 13 | env / secrets changes | Forbidden |

---

## 19. Open questions

Вопросы для HQ decision перед M1–M5:

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Marketing Cabinet — отдельный module или часть Core UI? | A) `backend/app/modules/marketing/` B) Section in workspace only | A + workspace UI section |
| 2 | Какие каналы в MVP publish? | Telegram + Instagram + Insights (Threads text-only?) | TG + IG + Insights auto; Threads manual |
| 3 | Где хранить media на первом этапе? | A) File path interim B) S3 from day 1 | A — interim paths |
| 4 | Как связывать pack и lead? | A) Lead Attribution table B) metadata_json only | A with Core IDs |
| 5 | Нужен ли calendar view в MVP? | A) List only B) Calendar | B if low cost; else list first |
| 6 | Какие роли пользователей? | Owner only / editor / viewer | MVP: owner (Асем) only |
| 7 | Как клиентам потом выдавать доступ? | Separate tenant / read-only dashboard | Out of MVP; dogfood first |
| 8 | Content bank sync — manual or auto? | Import button vs scheduled sync | Manual import MVP |
| 9 | Publish — in-process or scripts? | Keep scripts initially vs new workers | Scripts + log writeback MVP |
| 10 | Margosya API auth model? | Service account vs user OAuth | Service account with audit |

---

## 20. HQ summary

### 1. Path

```text
M0 Product TZ (this doc)
    → HQ decision
    → M1 Margosya audit
    → M2 Data model
    → M3 UI wireframes
    → M4 API contract
    → M5 MVP implementation plan
    → HQ approval
    → M6 First code slice
```

### 2. Product decision

**Marketing Cabinet / ContentOps Cabinet внутри Flexity — source of truth** для контент-плана, тем, packs, media, preflight, approve, publish, очереди, каналов, статусов и attribution.

**Маргося — Telegram thin client**, не основная система.

### 3. What moves from Margosya

Topic selection, pack creation, texts per channel, media upload, preflight, approve, publish (all channels), publish log, drafts list, reminders, error/retry — **всё в Marketing Cabinet**.

### 4. What remains in Margosya

Mobile quick actions: topic pick, text/photo intake, approve/reject, reminders, status checks, scheduled publish notifications, emergency publish command — **через Flexity API**.

### 5. MVP scope

Topics list, content plan, pack detail with 4 channel texts, media placeholder, preflight/approve/publish status, publish log, manual attribution, manual social lead intake, Core lead link, demo access notes, Margosya API contract draft.

### 6. Core integration

Tenant `flexity-sales`; leads as `WorkItem` + `Party`; Marketing Cabinet stores attribution; linkage via `work_item_id`, `party_id`, `pack_id`, `campaign_id`; **no separate CRM**.

### 7. Margosya integration

Bot becomes API client; Cabinet owns all state; transition period allows repo pack sync until API live.

### 8. Risks

Scope creep, CRM duplication, breaking Margosya, token security, manual attribution burden, storage readiness.

### 9. Recommended next step

1. **HQ review this TZ** — approve product direction.
2. **M1:** Read-only audit Margosya → feature mapping document.
3. Continue Core + DevOps per [FLEXITY_DEVOPS_CONTROL_LOG.md](../../FLEXITY_DEVOPS_CONTROL_LOG.md) in parallel.

### 10. Does implementation need separate approval?

**Yes.**

Любой код (M6), migrations, API deploy, Margosya bot changes, publish pipeline changes — только после approved M5 implementation plan + explicit HQ go.

---

*Документ подготовлен без изменений кода, миграций, deploy, production, Telegram bot и env/secrets.*
