# Flexity Booking — Implementation Plan E1b

**Дата:** 2026-07-02  
**Режим:** documentation_only (план без кода)  
**Предшественник:** [E1 complete](./booking/IMPLEMENTATION_PLAN_E1.md) — models + migration `0012_booking_e1`  
**Связанный аудит:** [FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md](./FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md)  
**Change Request:** [CR-2026-07-02-001](./ai/CHANGE_REQUESTS.md#cr-2026-07-02-001-flexity-booking-industry-package)  
**Approval status:** E1b **implemented** (2026-07-02). **Product status:** `INTERNAL PRODUCT MODULE / E1b COMPLETE`. Следующий этап — **E2** (availability + hold + timezone) после отдельного approval.

---

## Task Classification

| Параметр | Значение |
|----------|----------|
| Project | Flexity |
| Category | industry_package (internal product module — platform enablement only) |
| Risk | low–medium |
| Intended scope | seed files, tests, optional industry template config |
| Forbidden | migrations, routes, services (business), frontend, auth changes |

---

## 1. Цель E1b

**Включить Flexity Booking как внутренний industry package платформы** — без перехода к продуктовой разработке (API, availability, UI).

Booking — **внутренний продуктовый модуль Flexity**, а не отдельный клиентский проект и не зависимость от внешнего commercial approval.

E1b отвечает на вопрос: *«Как платформа узнаёт, что модуль Booking существует, и как tenant получает к нему доступ?»*

После E1b:

- модуль `booking` зарегистрирован в `module_registry`;
- subscription features/limits описывают права tenant;
- demo seed создаёт минимальный граф данных для ручной проверки;
- связи с Core (tenant, parties, finance FK) проверены тестами;
- `ModuleGuard` и `EntitlementService` готовы к использованию в E2+.

**E1b не даёт** рабочего продукта для гостя или админа — только платформенное включение модуля.

---

## 2. Границы E1b

### In scope

| # | Deliverable |
|---|-------------|
| 1 | Запись `booking` в `MODULE_DEFINITIONS` |
| 2 | Features и limits в `subscriptions/seed.py` |
| 3 | Обновление порядка включения модулей (`enable_modules_ordered`) |
| 4 | `booking/seed.py` — idempotent demo graph |
| 5 | Сервис-обёртка `BookingSeedService` (или функции в `seed.py`) |
| 6 | Тесты: registry, entitlements, demo seed, Core FK |
| 7 | Опционально: industry template `booking_basic` (отдельный micro-approval) |
| 8 | Документация closeout в `docs/booking/README.md` |

### Out of scope (явно не E1b)

| Область | Фаза |
|---------|------|
| Новые Alembic-миграции | Не E1b (схема E1 достаточна) |
| `document_file_id` FK на photos | E1b-opt / отдельный micro-approval |
| Routes / public / admin API | E3–E4 |
| Availability, hold, timezone services | E2 |
| Frontend / platform-console pages | E3–E4 |
| Telegram, payments flow | E5 / E4 |
| Auth changes для public slug | E3 |
| Автозапуск demo seed на `seed_on_startup` | Запрещено — только explicit script/API |
| Изменения billing / production deploy | Запрещено |

---

## 3. Module registry

### 3.1 Текущее состояние

Файл: `backend/app/modules/module_registry/seed.py`

Сейчас зарегистрированы 8 модулей: `parties`, `crm`, `catalog`, `documents`, `finance`, `accounting`, `integrations`, `ai`.  
**Модуля `booking` нет.**

При создании tenant вызывается `provision_tenant_modules()` — для каждого definition создаётся `tenant_module` со статусом `disabled`. Новый tenant **не увидит** booking, пока definition не добавлен.

### 3.2 Предлагаемая запись

Добавить в `MODULE_DEFINITIONS`:

```python
{
    "code": "booking",
    "name": "Booking",
    "description": "Territory and object reservations, holds and multi-object orders",
    "default_mode": "internal",
    "dependencies_json": {
        "required": ["parties"],
        "recommended": ["finance", "documents", "integrations", "workflows"],
    },
}
```

### 3.3 Правила зависимостей

| Зависимость | Тип | Обоснование |
|-------------|-----|-------------|
| `parties` | **required** | `guest_party_id`, `booking_owners.party_id` |
| `finance` | recommended | nullable `invoice_id`, `payment_id` на order |
| `documents` | recommended | будущие voucher / подтверждения |
| `integrations` | recommended | Telegram notifications |
| `workflows` | recommended | nullable `work_item_id` |

**Поведение `ModuleGuard`:** включить `booking` без `parties` → `409 ModuleDependencyError` (паттерн как у `crm` — см. `test_enable_module_with_dependency_check`).

### 3.4 Порядок включения модулей

Файл: `backend/app/modules/module_registry/service.py` → `_sort_module_codes`

Сейчас priority list не содержит `booking`. При `apply_plan_modules` / `enable_modules_ordered` booking может включиться **до** `parties`, что сломает dependency check.

**Действие E1b:** добавить `"booking"` в priority **после** `parties` и **до** или **после** `crm` (рекомендация: после `finance`, т.к. finance — recommended, не required):

```python
priority = [
    "parties",
    "catalog",
    "crm",
    "documents",
    "finance",
    "booking",      # ← добавить
    "accounting",
    "integrations",
    "ai",
]
```

### 3.5 Как tenant получает модуль

Два пути (оба уже есть в Core, E1b только наполняет данные):

| Путь | Механизм |
|------|----------|
| **A. Plan assignment** | `POST /api/v1/tenants` с `plan_code` → `apply_plan_modules` |
| **B. Manual enable** | `POST /api/v1/tenants/{id}/modules/booking/enable` (provider staff) |

E1b должен обновить хотя бы один plan (см. §4). Без этого путь A не включит booking автоматически.

**Важно:** после деплоя E1b `main.py` при `seed_on_startup=True` вызовет `ModuleRegistryService.seed_definitions()` — definition `booking` появится в каталоге автоматически. Demo seed (`booking/seed.py`) в startup **не** подключается.

### 3.6 Проверка после включения (API)

```http
GET  /api/v1/modules/registry              → booking в списке definitions
GET  /api/v1/tenants/{id}/modules          → booking со status trial/enabled
POST /api/v1/tenants/{id}/modules/parties/enable
POST /api/v1/tenants/{id}/modules/booking/enable   → 200
```

Access-check endpoint для booking **не существует** в E1b (будет в E2 вместе с routes). В E1b проверка — через `ModuleGuard` в unit-тесте.

---

## 4. Entitlements

### 4.1 Текущее состояние

Файл: `backend/app/modules/subscriptions/seed.py`

Features привязаны к `module_code`. Планы (`starter`, `business`, `enterprise`) задают `default_modules_json` и списки features.

**Booking features отсутствуют.**

### 4.2 Предлагаемые features (минимальный набор E1b)

| Feature code | module_code | Назначение | Когда проверять |
|--------------|-------------|------------|-----------------|
| `booking.territories.manage` | booking | CRUD territory (admin) | E4 |
| `booking.objects.manage` | booking | CRUD objects, owners, map | E4 |
| `booking.orders.create` | booking | Создание заказа / hold | E2–E3 |
| `booking.orders.read` | booking | Просмотр броней | E4 |
| `booking.orders.confirm_payment` | booking | Manual payment confirm | E4 |
| `booking.public.page` | booking | Публичная страница (unauthenticated) | E3 |

E1b регистирует features в каталоге. Реальные `require_feature(...)` появятся в E2–E4.

### 4.3 Предлагаемые usage limits (опционально, MVP-friendly)

| limit_code | period | starter | business | enterprise |
|------------|--------|---------|----------|------------|
| `booking.orders` | monthly | — | 500 | unlimited (no row) |
| `booking.bookable_objects` | — | — | 50 | unlimited |

Limits можно добавить в E1b как заготовку; enforcement — в E2+.

### 4.4 Распределение по планам

**Рекомендация E1b:**

| Plan | Изменение |
|------|-----------|
| `starter` | **Не добавлять** booking (фокус CRM) |
| `business` | Добавить `booking` в `default_modules_json`; features: `booking.orders.read`, `booking.objects.manage` |
| `enterprise` | Все `booking.*` features + `booking` в modules |

Альтернатива (если нужен отдельный pilot plan для internal tenant): plan `booking_pilot` — **только по owner approval**, не в default E1b.

### 4.5 Цепочка проверки entitlement

```
require_feature("booking.orders.create")
  → EntitlementService.assert_feature
    → plan_has_feature(feature_code)
    → modules.assert_enabled(feature.module_code)  # booking
```

Тест-паттерн: `test_entitlement_feature_check` в `test_entitlements.py`.

### 4.6 E1b entitlement tests (план)

1. Feature `booking.orders.create` существует после `seed_catalog`.
2. Tenant на plan `business` с booking modules → `assert_feature` проходит для read/manage.
3. Tenant на plan `starter` → `assert_feature("booking.orders.create")` → `FeatureNotEntitledError`.

---

## 5. Demo seed

### 5.1 Цель

Минимальный **идемпотентный** граф данных для проверки, что E1 persistence + Core FK работают в связке с включённым модулем.

Не заменяет production onboarding tenant; предназначен для internal validation модуля.

### 5.2 Файл и структура

Создать: `backend/app/modules/booking/seed.py`

Опираться на уже проверенный граф из `backend/tests/test_booking_models.py` → `_bootstrap_booking_graph` (1 territory, 1 owner, 1 object + photo; расширить до 2 owners / 3 objects для demo).

### 5.3 Минимальный demo graph

| Сущность | Кол-во | Пример |
|----------|--------|--------|
| Tenant | 1 | slug: `booking-demo` (или привязка к существующему pilot tenant) |
| Territory | 1 | `main-camp`, timezone `Asia/Almaty`, status `active` |
| Owner parties | 2 | Owner One, Owner Two |
| BookingOwner | 2 | по одному на party |
| BookableObject | 3 | cabin-1, cabin-2, gazebo-1 (типы CABIN, CABIN, ZONE) |
| ObjectPhoto | 1–3 | url placeholder на cabin-1 |
| MapPoint | 2–3 | координаты на схеме |
| BookingOrder | 1 | status `draft`, без items (или 1 held order — на выбор) |
| BookingItem | 0–2 | опционально для демо multi-object |
| Invoice / Payment | **нет** | FK nullable; отдельный smoke в тесте |

### 5.4 Идемпотентность

| Правило | Реализация |
|---------|------------|
| Upsert by natural key | `(tenant_id, code)` для territory; `(territory_id, code)` для objects |
| Повторный запуск | не дублирует записи |
| Tenant | искать по slug; не создавать tenant если не передан флаг `--create-tenant` |

### 5.5 Способ запуска (после реализации E1b)

**Не** подключать к `main.py` `seed_on_startup`.

Варианты:

| Способ | Когда |
|--------|-------|
| `python -m scripts.seed_booking_demo --tenant-slug booking-demo` | Локально / staging |
| Вызов из pytest fixture | CI |
| `IndustryTemplateService.apply_to_tenant` + booking seed hook | Если будет `booking_basic` template |

### 5.6 Связь с industry template `booking_basic` (опционально)

Отдельный micro-approval. Если включён:

Файл: `backend/app/modules/industry_templates/seed.py`

```python
BOOKING_BASIC = {
    "code": "booking_basic",
    "name": "Бронирование (базовый)",
    "default_modules": ["parties", "booking", "finance"],
    "default_roles": [...],
    "labels_config": {
        "entities": {
            "booking_order": "Бронь",
            "bookable_object": "Объект",
        },
    },
    # без pipelines на E1b
}
```

`apply_to_tenant` включит modules; **booking domain seed** — отдельным шагом `BookingSeedService.seed_demo(tenant_id)`.

**Рекомендация:** E1b без `booking_basic`; template — E1b-opt после пилота.

---

## 6. Проверка связей с Core

### 6.1 Матрица FK (уже в E1 models)

| Booking поле | Core таблица | ondelete | E1b demo seed |
|--------------|--------------|----------|---------------|
| `*.tenant_id` | `tenants` | CASCADE | tenant существует |
| `guest_party_id` | `parties` | RESTRICT | party PERSON создан |
| `booking_owners.party_id` | `parties` | RESTRICT | 2 owner parties |
| `invoice_id` | `invoices` | SET NULL | null в demo |
| `payment_id` | `payments` | SET NULL | null в demo |
| `work_item_id` | `work_items` | SET NULL | null в demo |
| `catalog_item_id` | `catalog_items` | SET NULL | null в demo |
| `created_by_user_id` | `users` | — | optional null |
| permissions `user_id` | `users` | CASCADE | не в demo seed E1b |

### 6.2 Тесты связей (план для E1b code)

| Тест | Ожидание |
|------|----------|
| `test_demo_seed_creates_graph` | territory + 3 objects + 2 owners |
| `test_demo_seed_idempotent` | второй вызов — те же id, нет дублей |
| `test_order_without_finance_links` | уже есть в E1; включить в seed suite |
| `test_booking_requires_parties_module` | enable booking без parties → 409 |
| `test_booking_module_in_registry` | `"booking" in registry codes` |
| `test_booking_features_in_catalog` | feature codes exist |
| `test_optional_invoice_fk` | создать invoice в finance → привязать к order → OK |

### 6.3 Finance smoke (без payment flow)

E1b только проверяет, что **nullable FK работает**:

1. Создать `Invoice` через `FinanceService` / repository для demo tenant.
2. Присвоить `booking_order.invoice_id`.
3. Commit + read back.

Полный payment confirm flow — **E4**.

---

## 7. Что будет видно после включения E1b

### 7.1 Platform operator (provider staff)

| Где | Что увидит |
|-----|------------|
| `GET /api/v1/modules/registry` | Модуль **Booking** в каталоге |
| `GET /api/v1/tenants/{id}/modules` | Строка `booking` (disabled → trial после enable/plan) |
| `GET /api/v1/plans` | Booking features в business/enterprise |
| DB | Demo rows в `booking_*` после explicit seed script |

### 7.2 Tenant user

| Где | Что увидит |
|-----|------------|
| Platform console | **Ничего нового** — UI для booking нет |
| API | **Нет** booking endpoints |

### 7.3 Разработчик / QA

| Проверка | Результат |
|----------|-----------|
| `ModuleGuard.assert_enabled("booking")` | OK после enable |
| `EntitlementService.has_feature("booking.orders.read")` | зависит от plan |
| SQL query `booking_territories` | demo territory после seed |
| pytest E1 + E1b suites | green |

### 7.4 Чего не будет (ожидаемо)

- Публичная страница бронирования
- Календарь доступности
- Hold timer
- Admin dashboard броней
- Telegram
- Запись в audit по booking events (нет сервисов)

---

## 8. Команды и тесты (после реализации E1b)

### 8.1 Обязательные проверки

```bash
cd backend

# Синтаксис
python -m compileall app/modules/booking app/modules/module_registry app/modules/subscriptions

# E1 regression
python -m pytest tests/test_booking_models.py -v

# E1b new/updated
python -m pytest tests/test_booking_seed.py tests/test_modules.py tests/test_entitlements.py -v

# Full backend smoke (если время)
python -m pytest -q --tb=short
```

### 8.2 Ручная проверка на staging (operator)

```bash
cd backend
python -m alembic current          # ожидается 0012_booking_e1 (без новых миграций)

# Перезапуск app → seed_definitions подтянет booking (seed_on_startup)
# Или вручную в shell:
# ModuleRegistryService(db).seed_definitions()
# SubscriptionService(db).seed_catalog()

python -m scripts.seed_booking_demo --tenant-slug <pilot-slug>   # после создания скрипта
```

```bash
# API smoke (curl / httpie) — provider token
GET  /api/v1/modules/registry
GET  /api/v1/tenants/{tenant_id}/modules
POST /api/v1/tenants/{tenant_id}/modules/parties/enable
POST /api/v1/tenants/{tenant_id}/modules/booking/enable
```

### 8.3 SQL sanity check

```sql
SELECT code FROM module_definitions WHERE code = 'booking';
SELECT module_code, status FROM tenant_modules WHERE module_code = 'booking';
SELECT count(*) FROM booking_territories;
SELECT count(*) FROM booking_bookable_objects;
```

---

## 9. Файлы, потенциально затронутые при разработке E1b

### 9.1 Обязательные

| Файл | Действие |
|------|----------|
| `backend/app/modules/module_registry/seed.py` | + booking definition |
| `backend/app/modules/module_registry/service.py` | + `booking` в `_sort_module_codes` |
| `backend/app/modules/subscriptions/seed.py` | + FEATURES, обновить PLANS |
| `backend/app/modules/booking/seed.py` | **создать** — DEMO constants + seed functions |
| `backend/tests/test_booking_seed.py` | **создать** |
| `backend/tests/test_modules.py` | + assert `booking` in registry |
| `backend/tests/test_entitlements.py` | + booking feature checks |
| `docs/booking/README.md` | статус E1b |
| `docs/ai/CHANGE_REQUESTS.md` | E1b progress |

### 9.2 Вероятные

| Файл | Действие |
|------|----------|
| `backend/scripts/seed_booking_demo.py` | **создать** — CLI entrypoint |
| `docs/FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md` | ссылка на E1b plan |

### 9.3 Опциональные (micro-approval)

| Файл | Действие |
|------|----------|
| `backend/app/modules/industry_templates/seed.py` | + `booking_basic` template |
| `backend/alembic/versions/...` | + `document_file_id` на photos |
| `backend/app/modules/booking/models.py` | FK document_files |

### 9.4 Запрещено трогать в E1b

| Файл / зона | Причина |
|-------------|---------|
| `backend/app/main.py` routes | E3+ |
| `backend/app/modules/auth/**` | отдельный approval |
| `platform-console/**` | E4 |
| `.env`, deploy, nginx | запрещено |
| `booking/models.py` (без approval) | схема E1 frozen |

---

## 10. Риски

| # | Риск | Severity | Митигация |
|---|------|----------|-----------|
| R1 | `test_provision_tenant_modules_on_create` ожидает `>= 8` modules — станет 9 | Low | Обновить assertion или проверять наличие `booking` |
| R2 | Booking в enterprise plan включает все features — раздувание trial | Low | Явный список features, не `FEATURES` целиком |
| R3 | Demo seed на startup загрязнит prod | High | **Только explicit script**, не `main.py` |
| R4 | `_sort_module_codes` без booking — enable plan ломается | Medium | Обязательный пункт E1b |
| R5 | Ожидание UI после E1b | Medium | HQ comms: E1b = platform enablement only |
| R6 | `booking_basic` template раздувает scope | Medium | Вынести в E1b-opt |
| R7 | Existing tenants без re-provision — нет строки tenant_modules для booking | Medium | Документировать: re-run provision или enable вручную |
| R8 | document_files FK — неverified coupling | Low | Отложить в E1b-opt |

---

## 11. Критерии готовности E1b

### 11.1 Registry

- [ ] `booking` в `MODULE_DEFINITIONS`
- [ ] `GET /api/v1/modules/registry` возвращает booking
- [ ] Enable booking без parties → 409
- [ ] Enable booking после parties → 200, status `enabled` или `trial`
- [ ] `booking` в `_sort_module_codes` priority list

### 11.2 Entitlements

- [ ] Минимум 6 feature codes с `module_code: booking` в каталоге (см. §4.2)
- [ ] Plan `business` (или approved pilot plan) включает `booking` module
- [ ] `EntitlementService` тест: entitled / not entitled

### 11.3 Demo seed

- [ ] Idempotent seed: 1 territory, 2 owners, 3 objects
- [ ] Повторный запуск не создаёт дубликаты
- [ ] Timezone territory = `Asia/Almaty`
- [ ] Per-object check-in/out override на ≥1 object
- [ ] Seed **не** в `seed_on_startup`

### 11.4 Core links

- [ ] Все FK demo graph валидны
- [ ] Order без invoice/payment — OK
- [ ] Optional: order с invoice_id — OK

### 11.5 Regression

- [ ] E1 tests (8/8) pass
- [ ] `compileall` pass
- [ ] Нет новых миграций (unless E1b-opt approved)
- [ ] Нет routes / frontend / auth changes

### 11.6 Documentation

- [ ] `docs/booking/README.md` — статус E1b complete
- [ ] CR-2026-07-02-001 обновлён
- [ ] HQ informed: product contour still not ready

---

## 12. Порядок реализации (после approval)

| Шаг | Задача | Зависимости |
|-----|--------|-------------|
| 1 | Approval этого плана | HQ + client gate |
| 2 | `module_registry/seed.py` + `_sort_module_codes` | — |
| 3 | `subscriptions/seed.py` features + plans | шаг 2 |
| 4 | Тесты registry + entitlements | шаги 2–3 |
| 5 | `booking/seed.py` + tests | E1 models |
| 6 | `scripts/seed_booking_demo.py` | шаг 5 |
| 7 | Staging: seed_catalog + demo script | deploy policy |
| 8 | Docs closeout | все шаги |

**Оценка:** 1 короткий спринт (2–4 dev-days) при строгом scope.

---

## 13. Rollback

E1b не меняет схему БД — откат без Alembic downgrade.

| Шаг | Действие |
|-----|----------|
| 1 | Revert коммит E1b (seed + tests + docs) |
| 2 | Перезапуск app → `seed_definitions` / `seed_catalog` пересоздадут каталог без `booking` (upsert по code) |
| 3 | Строки `tenant_modules` с `module_code='booking'` — останутся в БД; при необходимости удалить вручную или disable через API |
| 4 | Demo rows в `booking_*` — удалить SQL или оставить (не влияют на Core) |
| 5 | Regression: `pytest tests/test_booking_models.py` — должен остаться green (E1 не трогаем) |

Риск отката: **низкий**. Нет миграций, нет production routes.

---

## 14. Approval checklist

### Документация (этот план)

- [x] План E1b reviewed и принят (2026-07-02)
- [x] Подтверждено: без миграций, routes, UI
- [ ] Подтверждён plan для entitlements (business vs booking_pilot) — при реализации
- [ ] Решение по `booking_basic` template: deferred (E1b-opt)

### Код (E1b complete)

- [x] Owner approval — `approve E1b`
- [x] CR-2026-07-02-001 — E1b implementation delivered

---

## 15. Связанные документы

- [FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md](./FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md)
- [FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md](./FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md)
- [booking/IMPLEMENTATION_PLAN_E1.md](./booking/IMPLEMENTATION_PLAN_E1.md)
- [booking/FLEXITY_INTEGRATION.md](./booking/FLEXITY_INTEGRATION.md)
- [booking/MVP_SCOPE.md](./booking/MVP_SCOPE.md)
- [ai/CHANGE_REQUESTS.md](./ai/CHANGE_REQUESTS.md)

---

## HQ Summary

1. **Goal of E1b:** Register `booking` as a Flexity industry package in module_registry and subscriptions, add idempotent demo seed, verify Core FK links — so tenants can be entitled to Booking without building API/UI yet.

2. **Files likely to change:** `module_registry/seed.py`, `module_registry/service.py`, `subscriptions/seed.py`, new `booking/seed.py`, new `scripts/seed_booking_demo.py`, tests (`test_booking_seed.py`, updates to `test_modules.py`, `test_entitlements.py`), docs closeout.

3. **What will be enabled:** Module definition visible in registry; tenant can enable `booking` (after `parties`); plan features for booking; demo territory/objects in DB after explicit seed script; `ModuleGuard` / `EntitlementService` ready for E2+.

4. **What remains out of scope:** Migrations, routes, availability/hold services, public/admin UI, Telegram, payment flows, auth changes, auto demo seed on startup, `booking_basic` industry template (unless separately approved).

5. **Risks:** Scope expectations (no UI after E1b); existing tenants need manual re-provision; plan module ordering bug if `_sort_module_codes` not updated; demo seed must not run on production startup.

6. **Estimated complexity:** **Low** — seed data and tests only, no schema changes, no business services. ~2–4 dev-days with strict scope.

7. **Recommended next action:** Plan and approve **E2** (availability + hold + timezone services).
