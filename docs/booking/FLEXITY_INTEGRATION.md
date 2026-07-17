# Flexity Booking — интеграция с Flexity Core

Документ описывает переиспользование существующей платформы, объём нового модуля `booking` и решения, требующие **отдельного approval**.

## Task Classification

| Параметр | Значение |
|----------|----------|
| Project | Flexity |
| Category | industry_package (planning) |
| Risk | medium |
| Scope | `docs/booking/*`, future `backend/app/modules/booking/` |
| Forbidden | auth rewrite, migrations без approval, отдельный бренд |

---

## 1. Карта переиспользования

```
┌──────────────────────────────────────────────────────────────┐
│ Flexity Core                                                 │
│ tenants · auth · module_registry · subscriptions · settings    │
└────────────────────────────┬─────────────────────────────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
   parties              finance               workflows
   documents              audit              integrations
   catalog           entitlements         industry_templates
                             │
                             ▼
                ┌─────────────────────────┐
                │ Flexity Booking         │
                │ industry package        │
                └─────────────────────────┘
```

---

## 2. Что переиспользуется из Flexity Core

### 2.1 Tenants

- `tenant_id` на всех booking-таблицах;
- plan / industry_template для включения модуля;
- suspend tenant → блок публичной страницы.

### 2.2 Users / Roles

- JWT auth для admin panel;
- platform RBAC — coarse access;
- `User.id` в permissions и audit.

**Не создаём:** `booking_users`.

### 2.3 Parties

- Guest → create/find party по телефону;
- Owner → party + extension `owners`;
- контакты для documents и notifications.

**Не создаём:** `booking_clients`.

### 2.4 Finance

- `finance.invoices` — optional счёт после `pending_payment`;
- `finance.payments` — запись manual payment;
- `PaymentAllocation` — при необходимости.

**Не дублируем:** invoice/payment tables внутри booking. `booking_orders` — доменные, не finance orders.

### 2.5 Workflows

- optional `work_item_id` на booking_order;
- tasks: «подтвердить оплату», «заезд сегодня».

### 2.6 Documents / Templates

- voucher / подтверждение брони;
- post-MVP: договор аренды.

### 2.7 Audit

- `AuditRecorder` из `modules/audit`;
- entity_type `booking_*`;
- паттерн как в `FinanceService`.

### 2.8 Module guards

```python
# app/core/modules.py
ModuleGuard(db, tenant_id).assert_enabled("booking")
require_module("booking")  # FastAPI dependency
```

### 2.9 Entitlements

```python
# app/core/entitlements.py
EntitlementService.assert_feature("booking.orders.create")
require_feature("booking.public_page")
```

Seed (после approval): module `booking` + subscription features/limits.

### 2.10 Settings

| Уровень | Примеры |
|---------|---------|
| Tenant | Telegram bot token, defaults |
| Territory | `settings_json`: WhatsApp phone, payment instructions |
| Module registry | enable/disable booking |

---

## 3. Что дописать в `modules/booking`

Планируемая структура **после approval E1**:

```
backend/app/modules/booking/
  models.py              # domain models
  schemas.py
  repository.py
  service/
    availability.py      # availability service
    hold.py              # hold logic (30 min)
    booking_order.py
    commission.py
    map.py               # territory map + map_points
  routes/
    admin.py             # admin booking workflow
    public.py            # booking public page API
  permissions.py
  notifications/
    telegram.py          # Telegram bot integration (outbound)
  tasks.py               # hold expiry job
  seed.py
```

### 3.1 Domain models

Таблицы из [DATA_MODEL.md](./DATA_MODEL.md): territories, owners, bookable_objects, object_photos, map_points, booking_orders, booking_items, management_permissions, commission_rules.

### 3.2 Availability service

- свободные слоты по object + territory timezone;
- conflict detection confirmed + active holds;
- multi-object cart validation.

### 3.3 Hold logic

- soft lock 30 min;
- `hold_expires_at` UTC;
- expire job / cron;
- race → 409.

### 3.4 Territory map

- CRUD `map_points`, `map_config_json`;
- resolve object by map click;
- admin map editor API.

### 3.5 Booking public page

- unauthenticated routes by territory slug;
- cart, hold timer, guest party create;
- WhatsApp deep link data;
- source tracking (2gis, direct).

### 3.6 Admin booking workflow

- territory / object / owner CRUD;
- booking list, manual payment confirm;
- management_permissions;
- dashboard metrics.

### 3.7 Telegram bot integration

- outbound notifications (new booking, payment confirmed);
- `telegram_chat_id` on owners + admin config;
- через `integrations` module, не отдельный auth.

### 3.8 Не в scope первых этапов

| Компонент | Когда |
|-----------|-------|
| WhatsApp API | Post-MVP |
| Online payments | Post-MVP |
| Marketplace | Future |
| external_channels tables | Post-E1 |
| Public frontend UI | E3 plan |

---

## 4. Module registry entry (planned)

```json
{
  "code": "booking",
  "name": "Booking",
  "description": "Territory and object reservations",
  "default_mode": "internal",
  "dependencies_json": {
    "required": ["parties"],
    "recommended": ["finance", "documents", "integrations", "workflows"]
  }
}
```

---

## 5. Требует отдельного approval

| # | Решение |
|---|---------|
| 1 | **Код** модуля booking |
| 2 | **Migrations** / Alembic |
| 3 | **Auth changes** (public slug resolution, guest endpoints) |
| 4 | **WhatsApp API** (Meta Business) |
| 5 | **Online payments** (acquiring, webhooks) |
| 6 | **Marketplace** / cross-tenant catalog |
| 7 | **External channel integrations** (OTA, 2GIS API, sync) |
| 8 | **Separate brand** / standalone product |
| 9 | Новые **dependencies** (Telegram SDK, map libs) |
| 10 | **Tenant customization** layer (CR-2026-06-05-001) |
| 11 | Изменения **subscriptions** / billing для booking |
| 12 | **Automatic owner payout** / accounting |

Документация **не** считается approval для пунктов 1–12.

---

## 6. Порядок работ

1. ✅ Documentation pack (`docs/booking/`)
2. ✅ CR в CHANGE_REQUESTS.md
3. ⏳ Approval IMPLEMENTATION_PLAN_E1
4. ⏳ E1 code + migrations (только после п.3)
5. ⏳ E2–E6 — отдельные plans

---

## 7. Риски

| Риск | Mitigation |
|------|------------|
| Duplicate finance | FK only; no invoice lines in booking |
| TZ / DST bugs | Tests на границах; local time + UTC instant |
| Hold races | Row lock / exclusion constraint |
| Public API abuse | Rate limit; approval A3 |
| Scope creep | MVP_SCOPE out-of-scope list |

---

## 8. Связанные документы

- [README.md](./README.md)
- [PRODUCT_CONCEPT.md](./PRODUCT_CONCEPT.md)
- [MVP_SCOPE.md](./MVP_SCOPE.md)
- [DATA_MODEL.md](./DATA_MODEL.md)
- [IMPLEMENTATION_PLAN_E1.md](./IMPLEMENTATION_PLAN_E1.md)
- [../ai/CHANGE_REQUESTS.md](../ai/CHANGE_REQUESTS.md)
- [../ai/PRODUCT_ARCHITECTURE.md](../ai/PRODUCT_ARCHITECTURE.md)
