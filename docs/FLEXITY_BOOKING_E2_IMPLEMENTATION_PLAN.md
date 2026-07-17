# Flexity Booking — E2 Implementation Plan

**Название этапа:** `Booking Core Logic`  
**Дата плана:** 2026-07-02  
**Режим:** research + documentation_only (без кода)  
**Предшественник:** [E1b Closeout](./FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md) — `INTERNAL PRODUCT MODULE / E1b COMPLETE`  
**Change Request:** [CR-2026-07-02-001](./ai/CHANGE_REQUESTS.md#cr-2026-07-02-001-flexity-booking-industry-package)

**Approval status:** E2a **complete** (timezone + availability). E2b **complete** (hold + status machine + race protection). Closeout: [FLEXITY_BOOKING_E2B_CLOSEOUT_REPORT.md](./FLEXITY_BOOKING_E2B_CLOSEOUT_REPORT.md). Next: **E3a** internal/admin API slice (not public product).

---

## Task Classification

| Параметр | Значение |
|----------|----------|
| Project | Flexity |
| Category | industry_package (domain services layer) |
| Risk | medium–high |
| Intended scope | `backend/app/modules/booking/service/*`, repository, schemas, tests |
| Forbidden | routes, public API, UI, migrations (without micro-approval), payment flow, Telegram |

---

## 1. Current baseline after E1b

| Слой | Состояние |
|------|-----------|
| Persistence (E1) | 9 таблиц `booking_*`, migration `0012_booking_e1`, models + enums |
| Platform (E1b) | `booking` в module_registry; entitlements; demo seed CLI |
| Services | **E2 complete** — `timezone.py`, `availability.py`, `hold.py`, `order.py`, `repository.py` |
| Routes / API | **Нет** (E3a next) |
| UI | **Нет** |
| Tests | **39/39** (E1 8 + E1b 6 + E2a 14 + E2b 11) |

**Baseline-правило:** E2 строится поверх существующей схемы E1. Изменения моделей/миграций — только через отдельный micro-approval (`completed` enum, exclusion constraint).

---

## 2. E2 goal

Реализовать **базовую серверную бизнес-логику Booking** без UI и без публичного HTTP API.

После E2 разработчик/QA сможет:

- конвертировать local date/time territory → UTC instant;
- проверить доступность одного или нескольких объектов;
- создать hold с TTL из territory;
- перевести заказ по status machine;
- гарантировать atomic multi-object order;
- снизить риск double-booking через transactions/locking;
- вызывать сервисы из pytest (и позже — из E3/E4 routes).

**E2 не даёт** рабочего продукта для гостя или админа — только domain services.

---

## 3. Existing model audit

### 3.1 Что уже есть в `backend/app/modules/booking/`

| Файл | Содержание | Достаточно для E2? |
|------|------------|-------------------|
| `models.py` | 9 ORM-моделей, FK на Core | ✅ Схема достаточна |
| `enums.py` | Order/item/territory statuses | ⚠️ нет `completed` |
| `seed.py` | Demo graph (E1b) | ✅ для integration tests |
| `__init__.py` | маркер модуля | — |

**Нет:** `repository.py`, `service/`, `schemas.py`, `exceptions.py`, `routes/`.

### 3.2 Ключевые поля времени (E1)

| Уровень | Поля | Назначение |
|---------|------|------------|
| Territory | `timezone` (IANA), `default_check_in_time`, `default_check_out_time`, `hold_duration_minutes` | бизнес-правила |
| Object | `check_in_time`, `check_out_time` (nullable override) | local TIME override |
| Item | `check_in_date`, `check_out_date` (DATE), `check_in_at`, `check_out_at` (TIMESTAMPTZ UTC) | календарь + instant |
| Order | `hold_expires_at` (TIMESTAMPTZ UTC) | TTL hold |

CHECK constraint: `check_out_at > check_in_at` на `booking_items` — уже в БД.

Index: `ix_booking_items_object_interval (bookable_object_id, check_in_at, check_out_at)` — есть, но **нет exclusion constraint** для overlap.

### 3.3 Статусы (текущие enum)

**Order (`BookingOrderStatus`):**

```
draft → held → pending_payment → paid → confirmed
                ↘ cancelled
                ↘ expired
```

**Item (`BookingItemStatus`):** `active`, `cancelled`

**Отсутствует:** `completed` — lifecycle «после выезда» пока не формализован.

### 3.4 Пробелы модели для E2 (без обязательных миграций)

| Пробел | E2 подход |
|--------|-----------|
| Нет exclusion constraint | application-level locking + overlap query |
| Нет `completed` | computed helper `is_stay_completed(order, now)` |
| Нет maintenance-block таблицы | объекты `status=maintenance` не бронируются |
| Нет dedicated pricing service | snapshot `unit_price`/`line_total` при create (minimal) |

### 3.5 Связи Core (не дублировать)

| Core | Использование в E2 |
|------|-------------------|
| `tenants` | `tenant_id` isolation |
| `parties` | `guest_party_id` validation |
| `ModuleGuard` | `assert_enabled("booking")` в service entry |
| `EntitlementService` | `assert_feature("booking.orders.create")` при create |
| `AuditRecorder` | status transitions, hold create/expire |
| `finance` | **не** в E2 (nullable FK only) |

---

## 4. Timezone design

### 4.1 Принцип хранения

| Тип данных | Где | Зачем |
|------------|-----|-------|
| IANA timezone | `territory.timezone` | единый источник TZ для territory |
| Local TIME rules | territory defaults + object override | check-in/out по местному времени |
| Local DATE | `booking_item.check_in_date`, `check_out_date` | UI/calendar, отчёты |
| UTC instant | `check_in_at`, `check_out_at`, `hold_expires_at` | availability, overlap, сортировка |

**Правило:** все сравнения доступности и overlap — по **UTC instants** (`check_in_at`, `check_out_at`). Local DATE — производные от instants + territory TZ для отображения.

### 4.2 Где выполнять conversion

Новый модуль: `backend/app/modules/booking/service/timezone.py`

Использовать stdlib **`zoneinfo`** (без новых зависимостей).

| Функция | Вход | Выход |
|---------|------|-------|
| `resolve_effective_check_times(territory, object)` | territory + optional object | `(check_in_time, check_out_time)` local |
| `local_stay_to_utc_instant(local_date, local_time, tz_name)` | date, time, IANA | `datetime` UTC-aware |
| `build_item_interval(territory, object, check_in_date, check_out_date)` | dates + rules | `(check_in_at, check_out_at, nights)` |
| `utc_now()` | — | `datetime` UTC (для hold/expiry) |
| `is_valid_timezone(tz_name)` | string | bool |

**Алгоритм `build_item_interval`:**

1. `check_in_time` = `object.check_in_time` ?? `territory.default_check_in_time`
2. `check_out_time` = `object.check_out_time` ?? `territory.default_check_out_time`
3. `check_in_at` = combine(`check_in_date`, `check_in_time`) @ `ZoneInfo(territory.timezone)` → UTC
4. `check_out_at` = combine(`check_out_date`, `check_out_time`) @ same TZ → UTC
5. assert `check_out_at > check_in_at`
6. `nights` = calendar nights между dates (MVP: `check_out_date - check_in_date` в днях, min 1)

### 4.3 DST и drift — митигация

| Риск | Митигация |
|------|-----------|
| Ambiguous local time (DST fall-back) | `zoneinfo` raises `AmbiguousTimeError` → explicit policy: prefer `fold=0` или reject с `BookingTimezoneError` |
| Non-existent time (spring forward) | `zoneinfo` raises `NonExistentTimeError` → reject booking с понятной ошибкой |
| Territory TZ change после создания item | **E2:** immutable snapshot в item instants; смена TZ territory не пересчитывает старые items |
| Смешение naive/aware datetime | все service functions принимают/возвращают **timezone-aware UTC** |

### 4.4 Тесты timezone (обязательные)

- `Asia/Almaty` — обычные даты (primary MVP TZ)
- `UTC` — baseline
- Edge: checkout на следующий день после check-in
- DST edge case (опционально `Europe/Berlin` или `America/New_York`) — хотя бы 1 тест на non-existent/ambiguous

---

## 5. Availability design

### 5.1 Интервал и overlap

**Семантика интервала:** полуоткрытый `[check_in_at, check_out_at)` — checkout instant **не** блокирует следующий check-in в тот же момент.

**Overlap condition** (два интервала A, B):

```
A.check_in_at < B.check_out_at AND A.check_out_at > B.check_in_at
```

### 5.2 Какие order statuses блокируют слот

| Order status | Блокирует? | Условие |
|--------------|------------|---------|
| `held` | ✅ | `hold_expires_at > now_utc` |
| `held` | ❌ | `hold_expires_at <= now_utc` (эффективно expired, даже если status ещё не обновлён) |
| `pending_payment` | ✅ | всегда |
| `paid` | ✅ | всегда |
| `confirmed` | ✅ | всегда |
| `draft` | ❌ | не занимает слот (ещё не hold) |
| `cancelled` | ❌ | |
| `expired` | ❌ | |

### 5.3 Какие item statuses блокируют слот

| Item status | Блокирует? |
|-------------|------------|
| `active` | ✅ (если order blocking) |
| `cancelled` | ❌ |

### 5.4 Object / territory gates

| Проверка | Блокирует бронь? |
|----------|------------------|
| `bookable_object.status == active` | иначе `ConflictError` |
| `territory.status == active` | иначе `ConflictError` |
| `min_stay_nights` | E2: validate nights >= territory.min_stay_nights |

### 5.5 Multi-object availability

Вход: список `(bookable_object_id, check_in_date, check_out_date)`.

1. Для **каждого** item — `build_item_interval` → UTC instants
2. Для **каждого** item — overlap query по `bookable_object_id`
3. Если **любой** conflict → вернуть aggregate error (все конфликты, не только первый)
4. **Не создавать** order до успешной проверки всех items

### 5.6 Availability query (repository)

`BookingRepository.find_conflicting_items(object_id, check_in_at, check_out_at, exclude_order_id=None)`

Join `booking_items` → `booking_orders`, filter:

- same `bookable_object_id`
- item `status == active`
- order blocking per §5.2
- overlap per §5.1
- optional exclude current order (для re-hold / extend)

Возвращает список конфликтующих items (для 409 response в E3).

---

## 6. Hold design

### 6.1 Создание hold

**Flow (service-level, без HTTP):**

```
create_hold(cart) →
  1. validate territory/object gates
  2. availability check ALL items (atomic pre-check)
  3. BEGIN transaction
  4. lock objects (FOR UPDATE) or advisory lock
  5. re-check availability (double-check)
  6. create booking_order status=held
  7. create booking_items status=active
  8. hold_expires_at = now_utc + territory.hold_duration_minutes
  9. COMMIT
```

`hold_duration_minutes` — из `territory.hold_duration_minutes` (MVP default 30).

### 6.2 TTL и expiry

| Поле | Значение |
|------|----------|
| `hold_expires_at` | UTC instant при переходе в `held` |
| Default TTL | `territory.hold_duration_minutes` (30) |

**Expire logic** (`HoldService.expire_stale_holds(tenant_id | all)`):

- найти orders `status=held` AND `hold_expires_at <= now_utc`
- transition → `expired`
- items остаются `active` или → policy: items stay active but order expired (availability ignores per §5.2)
- audit event `booking_order.status_change`

**E2 delivery:** callable service method + pytest; **не** обязательно cron/scheduler в E2 (можно manual invoke / future task module).

### 6.3 Переходы после hold

| From | To | Trigger |
|------|-----|---------|
| `held` | `pending_payment` | guest submit / admin action (E4) |
| `held` | `expired` | TTL elapsed |
| `held` | `cancelled` | manual cancel |

**E2:** реализовать transitions как service methods; payment confirm — **E4**.

### 6.4 Race protection при hold

См. §9. Минимум E2: transaction + `SELECT ... FOR UPDATE` на `booking_bookable_objects` (или parent order row) + double-check availability внутри транзакции.

---

## 7. Status machine design

### 7.1 Order transitions (E2)

```
draft ──create_hold──► held
held ──submit──► pending_payment        [E2: method exists, no payment UI]
held ──expire──► expired                [auto]
held ──cancel──► cancelled              [manual]
pending_payment ──mark_paid──► paid     [E2: stub/manual service method]
paid ──confirm──► confirmed             [E2: stub]
pending_payment ──cancel──► cancelled
paid ──cancel──► cancelled              [policy: rare, admin only]
confirmed ──cancel──► cancelled         [policy: admin only, post-MVP rules]
```

**Terminal states:** `cancelled`, `expired`  
**Non-terminal active:** `held`, `pending_payment`, `paid`, `confirmed`

### 7.2 Manual vs automatic

| Transition | Тип |
|------------|-----|
| `held → expired` | **automatic** (expire job / lazy effective check) |
| `draft → held` | service (create_hold) |
| `held → pending_payment` | service (submit) |
| `* → cancelled` | **manual** (admin/user with permission — enforcement E4) |
| `paid → confirmed` | **manual** (admin confirm — E4) |

### 7.3 Item status sync

| Order event | Item effect |
|-------------|-------------|
| create hold | all items `active` |
| cancel order | all non-cancelled items → `cancelled` |
| expire order | items remain `active`; availability ignores via order status/TTL |

**E2:** явные правила в `BookingOrderService.cancel()` и `expire()`.

### 7.4 Enum `completed` — решение для E2

**Рекомендация E2:** **не добавлять** enum `completed` в E2.

Вместо этого:

```python
def is_order_stay_completed(order: BookingOrder, now_utc: datetime) -> bool:
    return (
        order.status == BookingOrderStatus.CONFIRMED
        and all(item.check_out_at <= now_utc for item in order.items if item.status == ACTIVE)
    )
```

| Вариант | Когда |
|---------|-------|
| Computed `is_stay_completed` | **E2 (recommended)** |
| Enum `completed` + migration | E2-opt или E4 — только при явном product approval |

---

## 8. Multi-object transaction design

### 8.1 Cart model (service DTO)

```python
@dataclass
class BookingCartItemInput:
    bookable_object_id: UUID
    check_in_date: date
    check_out_date: date

@dataclass
class BookingCartInput:
    territory_id: UUID
    guest_party_id: UUID
    source: BookingOrderSource
    items: list[BookingCartItemInput]
```

### 8.2 Transaction boundary

**Одна транзакция** на `create_hold` / `create_order`:

1. Pre-validate all items (outside or inside txn — see double-check)
2. Insert `booking_order`
3. Insert all `booking_items`
4. Commit — либо всё, либо rollback

**Правило:** при conflict на item #N — **не** создавать order и **не** создавать items 1..N-1.

### 8.3 Pricing (minimal E2)

- `unit_price` = `bookable_object.base_price` snapshot
- `line_total` = `unit_price * nights` (PER_NIGHT MVP)
- `order.subtotal` = sum(line_totals)
- Dynamic pricing / seasons — **post-MVP**

### 8.4 Validation order

1. territory active
2. all objects belong to territory
3. all objects active
4. guest party exists
5. timezone interval valid per item
6. min_stay_nights
7. availability all items
8. persist

---

## 9. Race condition protection

### 9.1 Уровни защиты

| Уровень | Механизм | E2 |
|---------|----------|-----|
| L1 Application | DB transaction | ✅ обязательно |
| L2 Locking | `SELECT FOR UPDATE` на objects | ✅ обязательно |
| L3 Double-check | повтор availability внутри txn | ✅ обязательно |
| L4 DB constraint | PostgreSQL `EXCLUDE USING gist` на tstzrange | E2-opt (миграция) |

### 9.2 Рекомендуемая стратегия locking (E2-min)

При `create_hold`:

```sql
SELECT id FROM booking_bookable_objects
WHERE id IN (:object_ids)
FOR UPDATE;
```

Порядок lock: сортировать `object_ids` ascending — защита от deadlock при multi-object.

### 9.3 E2-opt: exclusion constraint (отдельный micro-approval)

Миграция `0013_booking_e2_overlap` (опционально):

- PostgreSQL only
- Partial index: только blocking statuses
- Сложность: held + `hold_expires_at` требует expression index или materialized effective status

**Рекомендация:** начать E2 с L1–L3; exclusion constraint — отдельный spike после concurrency tests на staging PostgreSQL.

### 9.4 Concurrency tests

| Тест | Подход |
|------|--------|
| Sequential double hold | два `create_hold` подряд на тот же слот — второй 409 |
| Parallel holds | 2 threads / async sessions на PostgreSQL — один success, один conflict |
| SQLite pytest | sequential only; mark postgres test `@pytest.mark.postgres` |

---

## 10. Proposed service layer

### 10.1 Структура файлов

```
backend/app/modules/booking/
  exceptions.py          # BookingConflictError, BookingTimezoneError
  schemas.py             # internal DTOs (не HTTP response models)
  repository.py          # SQL queries, conflict lookup
  service/
    __init__.py
    timezone.py          # pure + territory helpers
    availability.py      # conflict detection
    hold.py              # create_hold, expire_stale_holds
    order.py             # status transitions, cancel, submit
```

**Позже (E3):** `routes/`, HTTP schemas — **не E2**.

### 10.2 Публичные service entrypoints (для будущих routes)

| Service | Method | Назначение |
|---------|--------|------------|
| `BookingTimezoneService` | `build_item_interval(...)` | conversion |
| `BookingAvailabilityService` | `check_cart(cart) -> conflicts` | pre-flight |
| `BookingHoldService` | `create_hold(cart) -> order` | hold + items |
| `BookingHoldService` | `expire_stale_holds(...)` | cleanup |
| `BookingOrderService` | `transition(order_id, target_status, ...)` | status machine |
| `BookingOrderService` | `cancel(order_id, ...)` | cancel |
| `BookingOrderService` | `submit_for_payment(order_id)` | held → pending_payment |

### 10.3 Private / internal

- overlap SQL в `repository.py`
- lock acquisition helpers
- `is_order_blocking(order, now)` — availability helper
- `is_order_stay_completed` — computed, не persist

### 10.4 Cross-cutting в services

```python
class BookingHoldService:
    def __init__(self, db: Session, tenant_id: UUID):
        self.modules = ModuleGuard(db, tenant_id)
        self.entitlements = EntitlementService(db, tenant_id)
        ...

    def create_hold(self, user: User | None, cart: BookingCartInput) -> BookingOrder:
        self.modules.assert_enabled("booking")
        self.entitlements.assert_feature("booking.orders.create")
        ...
```

Audit (ключевые события E2):

- `booking_order` create (hold)
- `booking_order` status_change (expire, cancel, submit)
- entity_type: `booking_order`, action via `AuditRecorder.audit_log`

---

## 11. Proposed tests

### 11.1 Новые test files

| File | Focus |
|------|-------|
| `tests/test_booking_timezone.py` | conversion, DST edges, invalid TZ |
| `tests/test_booking_availability.py` | overlap, blocking statuses, expired hold |
| `tests/test_booking_hold.py` | create_hold, TTL, expire |
| `tests/test_booking_order_service.py` | status transitions, cancel, multi-object |
| `tests/test_booking_concurrency.py` | parallel holds (postgres marker) |

### 11.2 Unit tests (минимум)

| # | Test case |
|---|-----------|
| T1 | `build_item_interval` Asia/Almaty — known UTC output |
| T2 | object override check-in/out times |
| T3 | overlap: adjacent stays `[d1,d2)` and `[d2,d3)` — no conflict |
| T4 | overlap: intersecting stays — conflict |
| T5 | held expired not blocking |
| T6 | confirmed blocking |
| T7 | cancelled item not blocking |
| T8 | multi-object: one conflict → no order created |
| T9 | multi-object: all free → order + N items |
| T10 | hold_expires_at set correctly from territory |
| T11 | expire_stale_holds transitions status |
| T12 | invalid checkout <= checkin rejected |
| T13 | maintenance object rejected |

### 11.3 Integration tests

- Использовать E1b `seed_demo` graph как fixture base
- Full flow: `create_hold` → `submit` → `cancel` без HTTP
- Optional invoice FK — уже есть в E1b; не дублировать

### 11.4 Regression

```bash
python -m pytest tests/test_booking_models.py tests/test_booking_seed.py -q
# + new E2 suites
```

Target: E1/E1b 23 tests remain green + ~25–35 new E2 tests.

---

## 12. Files likely to change

### 12.1 Обязательные (E2)

| File | Действие |
|------|----------|
| `backend/app/modules/booking/exceptions.py` | создать |
| `backend/app/modules/booking/schemas.py` | создать (internal DTOs) |
| `backend/app/modules/booking/repository.py` | создать |
| `backend/app/modules/booking/service/timezone.py` | создать |
| `backend/app/modules/booking/service/availability.py` | создать |
| `backend/app/modules/booking/service/hold.py` | создать |
| `backend/app/modules/booking/service/order.py` | создать |
| `backend/app/modules/booking/service/__init__.py` | создать |
| `backend/tests/test_booking_timezone.py` | создать |
| `backend/tests/test_booking_availability.py` | создать |
| `backend/tests/test_booking_hold.py` | создать |
| `backend/tests/test_booking_order_service.py` | создать |
| `docs/FLEXITY_BOOKING_E2_IMPLEMENTATION_PLAN.md` | этот документ |
| `docs/booking/README.md` | статус после E2 delivery |

### 12.2 Вероятные

| File | Действие |
|------|----------|
| `backend/tests/test_booking_concurrency.py` | создать |
| `backend/app/modules/booking/__init__.py` | export services marker |
| `docs/FLEXITY_BOOKING_E2_CLOSEOUT_REPORT.md` | после delivery |
| `docs/ai/CHANGE_REQUESTS.md` | E2 progress |

### 12.3 E2-opt (micro-approval)

| File | Действие |
|------|----------|
| `backend/alembic/versions/0013_booking_e2_overlap.py` | exclusion constraint |
| `backend/app/modules/booking/enums.py` | + `completed` |
| `backend/app/modules/booking/tasks.py` | scheduled expire job |

### 12.4 Запрещено в E2

| Zone | Причина |
|------|---------|
| `backend/app/main.py` routes | E3 |
| `platform-console/**` | E4 |
| `booking/models.py` (без approval) | frozen E1 |
| auth changes | E3 approval |
| finance payment flows | E4 |

---

## 13. Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Timezone/DST bugs | High | dedicated tests + explicit error types |
| R2 | Hold race / double booking | High | txn + FOR UPDATE + double-check |
| R3 | SQLite ≠ PostgreSQL locking | Medium | postgres concurrency tests on staging |
| R4 | Status drift order vs item | Medium | explicit cancel/expire rules §7.3 |
| R5 | Scope creep into routes/UI | Medium | strict E2 checklist in PR |
| R6 | `completed` enum pressure | Low | computed helper; defer migration |
| R7 | Expire job not running | Medium | lazy effective check in availability |
| R8 | Performance on overlap query | Low | existing index; EXPLAIN on staging |

---

## 14. Out of scope

| Область | Фаза |
|---------|------|
| Public / admin HTTP routes | E3–E4 |
| Frontend / mobile web | E3–E4 |
| Telegram notifications | E5 |
| Payment provider / webhooks | E4+ |
| Public booking page | E3 |
| Manual payment confirm UI | E4 |
| Commission accruals table | E2-opt / post-MVP |
| `booking_basic` industry template | deferred |
| Auth changes for unauthenticated slug | E3 |
| Online acquiring | post-MVP |
| Maintenance block calendar table | post-MVP (use object status) |

---

## 15. Step-by-step implementation order

| Step | Task | Depends on | Verify |
|------|------|------------|--------|
| 1 | Approval этого плана | — | HQ sign-off |
| 2 | `exceptions.py` + `schemas.py` | — | import check |
| 3 | `service/timezone.py` + tests | step 2 | T1–T2, T12 |
| 4 | `repository.py` — conflict queries | step 3 | unit query tests |
| 5 | `service/availability.py` + tests | step 4 | T3–T7, T13 |
| 6 | `service/hold.py` — create_hold | step 5 | T8–T10 |
| 7 | `service/hold.py` — expire_stale_holds | step 6 | T11 |
| 8 | `service/order.py` — transitions, cancel | step 6 | status tests |
| 9 | Audit hooks | step 8 | mock/spy AuditRecorder |
| 10 | Integration test full hold flow | step 9 | pytest |
| 11 | Concurrency test (postgres) | step 10 | staging CI optional |
| 12 | Docs closeout + CR update | all | E2 closeout report |

**Оценка:** 1–2 спринта при strict scope (без routes, без migrations).

---

## 16. Open questions

| # | Вопрос | Рекомендация E2 | Решить до code |
|---|--------|-----------------|----------------|
| Q1 | Добавлять enum `completed`? | Нет — computed helper | owner approval |
| Q2 | Exclusion constraint migration? | E2-opt после concurrency tests | staging spike |
| Q3 | Expire job: cron vs lazy-only? | Lazy in availability + explicit `expire_stale_holds` callable | E2 |
| Q4 | `draft` orders — кто создаёт? | Skip draft in MVP hold flow; create directly as `held` | confirm |
| Q5 | `min_stay_nights` per object или territory only? | territory only (E1 schema) | confirm |
| Q6 | PER_STAY pricing unit в E2? | validate enum exists; implement PER_NIGHT only | confirm |
| Q7 | Re-hold same cart after expire? | allow new order | default yes |
| Q8 | Postgres required for CI concurrency test? | optional marker, run on staging | infra |

---

## Связанные документы

- [FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md](./FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md)
- [FLEXITY_BOOKING_E2B_CLOSEOUT_REPORT.md](./FLEXITY_BOOKING_E2B_CLOSEOUT_REPORT.md)
- [FLEXITY_BOOKING_E1B_IMPLEMENTATION_PLAN.md](./FLEXITY_BOOKING_E1B_IMPLEMENTATION_PLAN.md)
- [FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md](./FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md)
- [booking/DATA_MODEL.md](./booking/DATA_MODEL.md)
- [booking/MVP_SCOPE.md](./booking/MVP_SCOPE.md)

---

## HQ Summary

1. **Current status:** `INTERNAL PRODUCT MODULE / E1b COMPLETE` — registry, entitlements, demo seed; 23/23 tests; no product API/UI.

2. **E2 goal:** Implement **Booking Core Logic** — timezone conversion, availability, hold, status machine, multi-object atomicity, race protection — services only, no routes/UI.

3. **Core logic to implement:** `timezone.py`, `availability.py`, `hold.py`, `order.py`, `repository.py`; overlap via UTC instants; hold TTL from territory; txn + FOR UPDATE; computed `is_stay_completed` (no `completed` enum in E2-min).

4. **Files likely to change:** new `booking/service/*`, `repository.py`, `schemas.py`, `exceptions.py`, 4–5 test files; optionally migration for exclusion constraint (E2-opt).

5. **Main risks:** timezone/DST errors; hold races; SQLite vs PostgreSQL locking; scope creep into E3.

6. **Test plan:** ~25–35 new tests — timezone edges, overlap/blocking rules, hold TTL/expire, multi-object atomicity, status transitions, optional postgres concurrency.

7. **Out of scope:** UI, public API, Telegram, payment provider, frontend/admin, auth changes.

8. **Open questions:** `completed` enum (defer), exclusion constraint (E2-opt), expire scheduler vs lazy, PER_STAY pricing, min_stay scope.

9. **Recommended next step:** Review and approve this E2 plan → then implement steps 2–12 in order; do not start routes until E2 closeout.
