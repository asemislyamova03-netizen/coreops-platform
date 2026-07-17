# Flexity Booking — документация

## Что это

**Flexity Booking** — **внутренний продуктовый industry package** внутри платформы Flexity для бронирования территорий, объектов и управления владельцами с разными правами доступа.

Это **не** отдельный бренд, **не** разовый клиентский сервис под одного заказчика и **не** зависимость от approval внешнего клиента. Booking развивается как часть платформы Flexity и использует ядро: tenants, parties, finance, audit, module guards и entitlements.

## Текущий статус

| Параметр | Значение |
|----------|----------|
| Product status | **`INTERNAL PRODUCT MODULE / E2b COMPLETE`** |
| Техническая фаза | **E1** persistence + **E1b** platform enablement + **E2a** timezone/availability + **E2b** hold/status |
| E2a | timezone conversion, UTC overlap, multi-object availability check |
| E2b | hold TTL, lazy expire, status machine, row locking, atomic multi-object hold |
| E3a (next) | internal/admin API slice (create_hold, GET order, status routes) |
| Продукт UI/API | **Нет** — public API, frontend, admin UI не начаты |

Change Request: [CR-2026-07-02-001](../ai/CHANGE_REQUESTS.md#cr-2026-07-02-001-flexity-booking-industry-package)

## Навигация

| Документ | Назначение |
|----------|------------|
| [PRODUCT_CONCEPT.md](./PRODUCT_CONCEPT.md) | Продуктовая концепция, каналы, эволюция |
| [MVP_SCOPE.md](./MVP_SCOPE.md) | Границы первой поставки |
| [DATA_MODEL.md](./DATA_MODEL.md) | Сущности, связи, правила времени |
| [FLEXITY_INTEGRATION.md](./FLEXITY_INTEGRATION.md) | Переиспользование Core, guardrails |
| [IMPLEMENTATION_PLAN_E1.md](./IMPLEMENTATION_PLAN_E1.md) | План этапа E1 (models + migrations planning) |
| [FLEXITY_BOOKING_E1B_IMPLEMENTATION_PLAN.md](../FLEXITY_BOOKING_E1B_IMPLEMENTATION_PLAN.md) | План E1b (module_registry + entitlements + demo seed) |
| [FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md](../FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md) | E1b closeout report |
| [FLEXITY_BOOKING_E2_IMPLEMENTATION_PLAN.md](../FLEXITY_BOOKING_E2_IMPLEMENTATION_PLAN.md) | План E2 (Booking Core Logic) |
| [FLEXITY_BOOKING_E2B_CLOSEOUT_REPORT.md](../FLEXITY_BOOKING_E2B_CLOSEOUT_REPORT.md) | E2b closeout report |
| [FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md](../FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md) | Аудит и roadmap MVP |

## Demo seed (explicit CLI only)

```bash
cd backend
python -m scripts.seed_booking_demo --tenant-slug <tenant-slug>
```

Не подключается к `seed_on_startup`.

## Следующий шаг

**E3a — Internal/Admin API Slice** ([E2b closeout](../FLEXITY_BOOKING_E2B_CLOSEOUT_REPORT.md#11-recommendation-for-e3a), [план E2](../FLEXITY_BOOKING_E2_IMPLEMENTATION_PLAN.md)).

Scope E3a: internal/admin `create_hold`, `GET order`, status transition routes, HTTP `require_module` / `require_feature`, базовые API tests.

**Не начинать** public booking page, frontend, payment provider или Telegram в E3a.

E2b завершён: hold + status machine + race protection (domain/service layer only).
