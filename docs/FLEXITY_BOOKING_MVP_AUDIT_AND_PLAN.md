# Flexity Booking — аудит и план первого этапа

**Дата аудита:** 2026-07-02  
**Режим:** только аудит и планирование (без новой бизнес-логики)  
**Проект:** Flexity (industry package `booking` внутри платформы)

---

## 1. Название и цель проекта

**Flexity Booking** — отраслевой модуль (industry package) внутри Flexity для коллективного бронирования территорий и объектов: домики, зоны, беседки, залы.

**Цель первого этапа:** запустить минимальный рабочий контур бронирования для одного клиента / одной территории — без полноценной PMS, без channel manager и без тяжёлого frontend. Контур должен быть архитектурно расширяемым: несколько объектов в одном заказе, индивидуальные заезд/выезд по объекту, корректная работа с timezone.

**Не является:** отдельным брендом, отдельным репозиторием или standalone Flask/FastAPI приложением.

---

## 2. Текущий статус

| Параметр | Состояние |
|----------|-----------|
| Product status | **`INTERNAL PRODUCT MODULE / E1b COMPLETE`** |
| Продуктовая фаза | Внутренний модуль Flexity — развитие в составе платформы |
| Техническая фаза | **E1 + E1b complete** |
| E1b | module_registry, entitlements, demo seed — **delivered** |
| E1b код | **Complete** |
| Change Request | [CR-2026-07-02-001](./ai/CHANGE_REQUESTS.md#cr-2026-07-02-001-flexity-booking-industry-package) |
| Миграция БД | `0012_booking_e1` — 9 таблиц `booking_*` (без новых миграций в E1b) |
| Staging | Миграция применена на PostgreSQL staging |
| API / UI | **Не начаты** |
| Seed / module_registry | **E1b delivered** — explicit demo CLI |
| Документация | Пакет `docs/booking/` + audit + E1b plan |

**Вывод:** E1 persistence и E1b platform enablement завершены. Рабочего продукта (UI/API) ещё нет. Следующий этап — **E2** (availability, hold, timezone).

---

## 3. Что уже найдено в коде

### 3.1 Модуль Booking

Расположение: `backend/app/modules/booking/`

| Файл | Назначение |
|------|------------|
| `models.py` | 9 SQLAlchemy-моделей (465 строк) |
| `enums.py` | Статусы, типы объектов, права |
| `__init__.py` | Маркер E1 persistence layer |

**Нет:** `schemas.py`, `repository.py`, `service/`, `routes/`, `seed.py`, `tasks.py`, `notifications/`.

### 3.2 Миграции

- `backend/alembic/versions/20250702_0012_phase12_booking_e1.py`
- Revision: `0012_booking_e1`, depends on `0011_phase11`
- Создаёт 9 таблиц с префиксом `booking_*`
- CHECK: `check_out_at > check_in_at` на `booking_items`
- Индексы: интервалы брони, hold expiry, уникальные slug/code

### 3.3 Регистрация моделей

Импорт в `backend/app/modules/models.py` — модели участвуют в SQLAlchemy metadata.

### 3.4 Тесты

`backend/tests/test_booking_models.py` — **8 тестов**, все проходят:

- регистрация таблиц в metadata;
- создание графа territory → owner → object → photo;
- уникальность slug territory;
- CHECK checkout > checkin;
- заказ без finance FK;
- **multi-object order** (2 items в одном order);
- commission rules без accruals table;
- FK на booking_items.

### 3.5 API, handlers, services

**Не найдено.** В `backend/app/main.py` нет регистрации booking routes. Поиск по `backend/app/**/routes/**` — 0 совпадений.

### 3.6 Frontend / admin

- `platform-console/` — **нет** упоминаний booking
- Отдельной папки `frontend/` в репозитории нет
- Admin-страниц бронирования **нет**

### 3.7 Seed-данные

- `module_registry/seed.py` — модуль `booking` **не зарегистрирован**
- `subscriptions/seed.py` — entitlements для booking **не добавлены**
- Демо-данные territory/objects **не созданы**

### 3.8 Связанная, но чужая логика

- `flexity_admin/migrations/.../consultation_bookings.py` — консалтинговые записи, **не относится** к Flexity Booking
- Trailers `vin_reservation` — складская резервация, **не относится**

### 3.9 Документация (уже существует)

| Документ | Содержание |
|----------|------------|
| [docs/booking/README.md](./booking/README.md) | Навигация, статус E1 |
| [docs/booking/PRODUCT_CONCEPT.md](./booking/PRODUCT_CONCEPT.md) | Продукт, акторы, каналы |
| [docs/booking/MVP_SCOPE.md](./booking/MVP_SCOPE.md) | Границы MVP |
| [docs/booking/DATA_MODEL.md](./booking/DATA_MODEL.md) | ER, правила времени |
| [docs/booking/FLEXITY_INTEGRATION.md](./booking/FLEXITY_INTEGRATION.md) | Core vs Booking |
| [docs/booking/IMPLEMENTATION_PLAN_E1.md](./booking/IMPLEMENTATION_PLAN_E1.md) | E1 closeout |

---

## 4. Какие сущности уже есть

### 4.1 Таблица соответствия требованиям

| Требуемая сущность | Есть в коде | Реализация |
|--------------------|-------------|------------|
| **tenant** | ✅ (Core) | `tenants` — FK на всех booking-таблицах |
| **client / customer** | ✅ (Core) | `parties` — `guest_party_id` на заказе; owner через `booking_owners.party_id` |
| **объект бронирования** | ✅ | `booking_bookable_objects` |
| **заказ / booking order** | ✅ | `booking_orders` |
| **позиция брони / booking item** | ✅ | `booking_items` (1 order → N items) |
| **календарь** | ⚠️ частично | Отдельной таблицы нет; доступность = вычисление по `booking_items` (сервис — E2) |
| **оплата** | ⚠️ ссылка | `booking_orders.invoice_id`, `payment_id` → Core `finance`; доменной оплаты нет |
| **статус брони** | ✅ | `BookingOrderStatus`, `BookingItemStatus` |
| **territory (контур)** | ✅ | `booking_territories` |
| **owner (владелец)** | ✅ | `booking_owners` |
| **права управления** | ✅ | `booking_management_permissions` |
| **фото объекта** | ✅ | `booking_object_photos` |
| **точка на карте** | ✅ | `booking_map_points` |
| **комиссии** | ⚠️ частично | `booking_commission_rules` есть; `booking_commission_accruals` — нет (E2) |

### 4.2 Статусы заказа (реализованные enum)

```
draft → held → pending_payment → paid → confirmed
                ↘ cancelled
                ↘ expired
```

**Замечание:** в продуктовом ТЗ упомянут статус `completed` — в текущем enum его **нет**. Ближайший аналог: `confirmed` + прошедший `check_out_at` (логика завершения — E2/E4).

### 4.3 Правила времени (заложены в схеме)

| Уровень | Поля | Тип |
|---------|------|-----|
| Territory | `timezone`, `default_check_in_time`, `default_check_out_time` | IANA + local TIME |
| Object | `check_in_time`, `check_out_time` (nullable override) | local TIME |
| Item | `check_in_date`, `check_out_date`, `check_in_at`, `check_out_at` | DATE local + TIMESTAMPTZ UTC |
| Order | `hold_expires_at` | TIMESTAMPTZ UTC |

Конвертация local → UTC instant **не реализована** (запланирована в E2 service layer).

### 4.4 Пользователи, роли и доступы

| Слой | Состояние |
|------|-----------|
| **Platform RBAC** (Core auth) | Существует; booking не подключён |
| **Booking fine-grain ACL** | Модель `booking_management_permissions` есть; enforcement **нет** |
| Scope types | `territory`, `owner`, `object` |
| Permissions | `view`, `manage`, `finance`, `notify` |
| Публичный доступ (guest без login) | **Не реализован**; требует отдельного approval (auth changes) |

### 4.5 Связь с Flexity Core

| Core-модуль | Связь с Booking |
|-------------|-----------------|
| `tenants` | `tenant_id` на всех таблицах |
| `parties` | guest + owner |
| `users` | permissions, audit mixin |
| `finance` (invoices, payments) | nullable FK на order |
| `workflows` (work_items) | nullable FK на order |
| `catalog` (catalog_items) | nullable FK на object |
| `audit` | через AuditRecorder (не отдельная booking-таблица) |
| `module_registry` | **не подключён** |
| `subscriptions` / entitlements | **не подключён** |
| `ModuleGuard` / `require_module` | инфраструктура есть в Core, booking не зарегистрирован |

---

## 5. Чего не хватает

### 5.1 Критично для рабочего MVP

| # | Компонент | Фаза |
|---|-----------|------|
| 1 | Module registry + entitlements seed | E1b |
| 2 | Availability service (проверка пересечений) | E2 |
| 3 | Hold logic + expire job (30 min) | E2 |
| 4 | Timezone conversion service (local time → UTC instant) | E2 |
| 5 | Booking order service (create, status transitions) | E2 |
| 6 | Admin API (CRUD territory, objects, orders) | E3–E4 |
| 7 | Public API (slug, cart, guest party) | E3 |
| 8 | Admin UI (хотя бы минимальная) | E4 |
| 9 | Public mobile web page | E3 |
| 10 | Manual payment confirmation flow | E4 |
| 11 | Audit events при смене статусов | E2–E4 |
| 12 | Demo / seed data для первого клиента | E1b+ |

### 5.2 Важно, но можно отложить

- Telegram notifications (E5)
- Commission accruals table (E2)
- Online payment gateway
- WhatsApp Business API
- OTA / 2GIS API sync
- Dynamic pricing
- Отдельная таблица «календарь блокировок» (maintenance blocks)

### 5.3 Архитектурные пробелы

- Нет DB exclusion constraint для overlap (только index; race conditions — E2)
- Нет partial unique «одна active territory на tenant» (application-level в E2)
- Нет статуса `completed` (решить: добавить enum или вычислять)
- Нет `booking_commission_accruals`
- Нет `external_channels` tables

---

## 6. Риски текущей архитектуры

| Риск | Описание | Severity | Митигация |
|------|----------|----------|-----------|
| **Timezone / DST** | Конвертация local TIME + DATE → UTC instant ещё не написана; ошибки на границах суток и DST | High | E2: dedicated `timezone.py` + тесты на Asia/Almaty, UTC, edge dates |
| **Hold races** | Два гостя могут одновременно забронировать слот без exclusion constraint | High | E2: row lock / advisory lock / exclusion constraint |
| **Multi-object partial failure** | Заказ с 2 items: один слот свободен, другой занят | Medium | E2: atomic validation всей корзины до создания hold |
| **Status drift** | Item status (`active`/`cancelled`) vs order status — нет sync logic | Medium | E2: явные правила каскада при cancel/expire |
| **No module guard** | Booking API без seed будет доступен всем tenant | Medium | E1b: module_registry + `require_module("booking")` |
| **Finance coupling** | Nullable FK есть, но нет сервиса создания invoice | Low (MVP) | E4: manual confirm без invoice; invoice optional |
| **Scope creep** | Богатая модель (owners, commissions, map) может затянуть MVP | Medium | Жёстко держать MVP_SCOPE; map/commission — minimal in v1 |
| **Public API abuse** | Unauthenticated endpoints | Medium | Rate limit + отдельный approval |
| **Нет completed status** | Клиент ожидает lifecycle до «выехал» | Low | Договориться: `confirmed` + past checkout или добавить enum в E2 |

---

## 7. Разделение Flexity Core и Booking module

```
┌─────────────────────────────────────────────────────────────────┐
│ Flexity Core                                                     │
│                                                                  │
│  tenants · users · auth/RBAC · parties · subscriptions          │
│  module_registry · entitlements · settings · audit               │
│  finance (invoices, payments) · workflows · documents          │
│  commercial proposals · projects · integrations                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ FK + services, не дублирование
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Flexity Booking (industry package)                               │
│                                                                  │
│  booking_territories · booking_owners · booking_bookable_objects │
│  booking_object_photos · booking_map_points                      │
│  booking_orders · booking_items                                  │
│  booking_management_permissions · booking_commission_rules       │
│                                                                  │
│  services: availability · hold · order · timezone · commission   │
│  routes: admin · public                                          │
│  notifications: telegram (через integrations)                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.1 Что живёт в Core (не дублировать в Booking)

| Сущность | Почему Core |
|----------|-------------|
| Tenant | Multi-tenancy платформы |
| User / platform roles | Единая аутентификация |
| Party (guest, owner legal entity) | Универсальный контрагент |
| Invoice / Payment | Универсальные финансы |
| Work item / task | Универсальные workflows |
| Audit log | Универсальный audit |
| Subscription / tariff | Платформенная монетизация |
| Commercial proposal | Продажа внедрения (flexity_admin / CRM) |
| Project | Управление внедрением клиента |

### 7.2 Что живёт в Booking (отраслевое)

| Сущность | Почему Booking |
|----------|----------------|
| Territory | Контур бронирования с timezone и правилами |
| Bookable object + type | Домик, зона, беседка |
| Per-object check-in/out | Override territory defaults |
| Booking order + items | Доменный заказ (не finance order) |
| Availability / hold | Отраслевая логика слотов |
| Map points | Схема территории |
| Owner extension | Владелец объектов + payout metadata |
| Management permissions | Fine-grain ACL объектов |
| Commission rules | Отраслевая комиссия |
| Booking-specific statuses | held, expired, pending_payment |

### 7.3 Правило границы

> `booking_orders` / `booking_items` — **доменные** сущности бронирования.  
> `invoices` / `payments` — **финансовые** сущности Core.  
> Связь через nullable FK, без копирования строк в finance tables.

---

## 8. Предлагаемая модель данных первого этапа

Модель **уже реализована в E1**. Для первого рабочего этапа (E1b → E2 → E3/E4) изменений схемы не требуется, кроме возможного:

- добавления статуса `completed` (если клиент настаивает) — миграция enum;
- `booking_commission_accruals` — отложить;
- exclusion constraint на интервалы — опционально в E2.

### 8.1 Ключевые связи (уже в коде)

```
Tenant
  └── BookingTerritory (timezone, defaults)
        ├── BookingBookableObject (per-object check-in/out, price)
        │     ├── BookingObjectPhoto
        │     └── BookingMapPoint
        └── BookingOrder (status, hold_expires_at)
              └── BookingItem[] (check_in_at, check_out_at, line_total)

Party ──► BookingOrder.guest_party_id
Party ──► BookingOwner ──► BookingBookableObject.owner_id

BookingOrder ──?──► Invoice (Core)
BookingOrder ──?──► Payment (Core)
```

### 8.2 Правило multi-object (подтверждено тестом)

Один `booking_orders` → несколько `booking_items` с разными `bookable_object_id` и разными датами. Тест `test_multi_object_booking_order` проходит.

### 8.3 Правило timezone (зафиксировано, реализация — E2)

1. Хранить instants в UTC (`timestamptz`).
2. Business rules брать из `territory.timezone` (IANA).
3. Check-in/out time — local TIME (territory default или object override).
4. При создании item: `check_in_at = combine(check_in_date, effective_check_in_time) @ territory_tz → UTC`.

---

## 9. MVP первого этапа

**Цель:** один клиент, одна territory, end-to-end бронирование с ручным подтверждением оплаты.

### 9.1 User journey (минимальный)

```
2GIS / прямая ссылка
  → mobile public page (territory slug)
  → выбор 1–N объектов + даты по каждому
  → hold 30 min
  → форма гостя (имя, телефон → party)
  → страница «ожидает оплаты» + реквизиты
  → админ: «оплата получена» → confirmed
  → (опционально) Telegram ops
```

### 9.2 In scope первого этапа (после согласования с клиентом)

| # | Функция | Примечание |
|---|---------|------------|
| 1 | Справочник объектов | CRUD в admin API |
| 2 | Настройки объекта | name, type, active, check-in/out, capacity, description |
| 3 | Territory settings | timezone, currency, hold 30 min, payment instructions |
| 4 | Создание заказа | order + items |
| 5 | Multi-object в одном заказе | Уже в модели |
| 6 | Даты/время по каждой позиции | per-item check_in_at / check_out_at |
| 7 | Проверка пересечений | E2 availability service |
| 8 | Статусы | draft → held → pending_payment → paid → confirmed; cancelled, expired |
| 9 | Admin API / простая страница | Список броней, confirm payment |
| 10 | Public API + mobile web | Cart, hold timer, guest form |
| 11 | Оплата | Manual confirm; invoice_id optional |
| 12 | Timezone | С первого сервисного слоя (E2) |

### 9.3 Технические подэтапы (рекомендуемая нарезка)

| Подэтап | Содержание | Оценка сложности |
|---------|------------|------------------|
| **E1b** | module_registry seed, entitlements, demo seed territory | Низкая |
| **E2** | timezone utils, availability, hold, order service, status machine, tests | Высокая |
| **E3** | Public API + minimal mobile web (карта/список, cart, hold) | Высокая |
| **E4** | Admin API + minimal admin UI, manual payment, audit hooks | Средняя |
| **E5** | Telegram notifications | Низкая–средняя |
| **E6** | Hardening, load, edge cases | Средняя |

### 9.4 Критерии приёмки MVP (из MVP_SCOPE)

1. Admin создаёт territory, 3+ objects, 2 owners.
2. Guest с телефона бронирует 2 objects с разными датами.
3. Hold 30 min; после expiry — слот снова доступен.
4. Admin подтверждает оплату → confirmed.
5. Конфликт слота блокируется (409).
6. Owner видит только свои objects (permissions).
7. WhatsApp deep link работает.
8. Source `2gis` сохраняется при UTM.
9. Audit фиксирует ключевые события.

---

## 10. Что отложить на потом

| Область | Когда |
|---------|-------|
| Полноценная PMS (housekeeping, channel manager) | Post-MVP |
| Booking.com / Airbnb sync | Future |
| Online acquiring / webhooks | После выбора провайдера |
| WhatsApp Business API | Post-MVP |
| 2GIS API integration | Post-MVP (MVP: manual link + UTM) |
| Мобильное нативное приложение | Не планируется в MVP |
| Dynamic pricing / сезоны | Post-MVP |
| CRM-маркетинг, бонусы | Universal modules Flexity |
| Marketplace / cross-tenant catalog | Future |
| Tenant customization (бренд, шаблоны) | CR layer, не в MVP |
| Commission accruals / owner payout | E2+ / post-MVP |
| Сложная аналитика | Post-MVP |
| Auth changes для публичного slug | Отдельный micro-approval в E3 |
| Большой frontend без утверждённого UX | Не начинать |

---

## 11. Рекомендуемый порядок разработки

### Шаг 0 — Завершено (E1 + E1b)

- [x] E1 persistence
- [x] E1b implementation plan
- [x] E1b platform enablement (registry, entitlements, demo seed)
- [x] Internal Flexity product module status

### Шаг 1 — E2 (следующий; **не начат**)

1. `service/timezone.py` — local ↔ UTC
2. `service/availability.py` — conflict detection
3. `service/hold.py` — create hold, expire job
4. `service/booking_order.py` — create order, status transitions
5. Unit + integration tests
6. Audit hooks через Core AuditRecorder

**Без UI.** Проверка через pytest + возможно minimal internal API.

### Шаг 2 — E3 (публичный контур)

1. Public routes by territory slug (unauthenticated — отдельный approval)
2. Cart + hold timer API
3. Guest party create/find by phone
4. Minimal mobile web page (list fallback; map — если успеваем)

### Шаг 4 — E4 (админ + оплата)

1. Admin CRUD: territory, objects, owners, permissions
2. Booking list + filters
3. Manual payment confirm → paid → confirmed
4. Optional finance invoice creation
5. Minimal admin UI (можно в platform-console)

### Шаг 5 — E5 + E6

1. Telegram notifications
2. Hardening, rate limits, monitoring
3. Пилот на первом клиенте

---

## 12. Открытые вопросы к клиенту

### Продуктовые

1. **Сколько территорий** на старте? (MVP: одна; модель допускает N)
2. **Сколько владельцев (owners)** и нужен ли им отдельный кабинет в v1?
3. **Нужен ли статус `completed`** (после выезда) или достаточно `confirmed`?
4. **Типы объектов:** домики, беседки, зоны — полный список?
5. **Ценообразование:** только per_night или есть почасовые/посуточные объекты?
6. **Минимальный срок** (min_stay_nights) — общий или per object?
7. **Карта территории** — обязательна в v1 или достаточно списка?
8. **Канал привлечения:** только 2GIS + прямая ссылка?

### Операционные

9. **Кто подтверждает оплату** — один админ или несколько ролей?
10. **Реквизиты оплаты** — статичные или разные per territory?
11. **Telegram** — обязателен в v1 или можно отложить?
12. **WhatsApp** — только deep link или нужен API?
13. **Язык UI** — RU only или KZ/EN?

### Технические / юридические

14. **Платёжный провайдер** — когда ожидается? (MVP = manual)
15. **Часовой пояс** первой territory — `Asia/Almaty`?
16. **Персональные данные гостей** — согласие, хранение, срок?
17. **Договор / оферта** — нужен ли PDF voucher в v1?
18. **SLA hold** — 30 минут финально?

### Коммерческие

19. **Дата старта разработки** после подписания?
20. **Пилотный период** — сколько объектов, какой трафик?
21. **Бюджет на v1** — согласован ли scope E1–E4?

---

## 13. Краткий summary для Flexity HQ

Flexity Booking — **внутренний** industry package внутри Flexity. **E1 + E1b complete:** persistence (`0012_booking_e1`), module registry, entitlements, demo seed CLI. Рабочего продукта (UI/API) нет. Следующий этап — **E2 Booking Core Logic** (availability, hold, timezone).

---

## HQ Summary

1. **Current status:** `INTERNAL PRODUCT MODULE / E1b COMPLETE`. E1 persistence + E1b platform enablement done. 23 tests passing. No product UI/API.

2. **Existing code:** `backend/app/modules/booking/` (models, enums, seed); module_registry + entitlements; `scripts/seed_booking_demo.py`; migration `0012_booking_e1`; CR-2026-07-02-001.

3. **MVP scope:** One territory, multi-object booking, per-object dates, 30-min hold, conflict check, manual payment, minimal public mobile page + admin, timezone from day one.

4. **Main risks:** Timezone conversion not implemented; hold race conditions; status `completed` missing from enum; scope creep from rich data model.

5. **Core dependency:** tenants, parties, users/RBAC, finance, audit, module_registry, subscriptions — connected via E1b.

6. **Booking module scope:** E1b baseline done; E2 services (availability/hold/timezone); E3–E4 routes/UI.

7. **Open product questions (MVP tuning):** Territory count, owner portal, completed status, map vs list, payment flow, Telegram priority.

8. **Recommended next step:** Create and approve **E2** implementation plan (`Booking Core Logic`).

---

## Связанные документы

- [docs/booking/README.md](./booking/README.md)
- [docs/FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md](./FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md)
- [docs/booking/MVP_SCOPE.md](./booking/MVP_SCOPE.md)
- [docs/booking/DATA_MODEL.md](./booking/DATA_MODEL.md)
- [docs/booking/IMPLEMENTATION_PLAN_E1.md](./booking/IMPLEMENTATION_PLAN_E1.md)
- [docs/ai/CHANGE_REQUESTS.md](./ai/CHANGE_REQUESTS.md)
