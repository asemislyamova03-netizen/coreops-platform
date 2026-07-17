# Flexity Booking — границы MVP

Документ фиксирует **минимальную** поставку для проверки product-market fit одной территории. Post-MVP пункты в первый релиз **не** входят; модель данных и API не должны им мешать.

## 1. Цель MVP

Запустить **одну** активную territory end-to-end:

```
2GIS / direct link → mobile public page → выбор объектов → hold 30 min
  → заявка → manual payment → подтверждение → Telegram ops
  → WhatsApp link для связи с оператором
```

## 2. In scope

### 2.1 Территория

| Требование | Детали |
|------------|--------|
| Одна active territory на tenant | Вторая territory в UI disabled/hidden |
| Timezone territory | IANA TZ; hold и UI в local time |
| Настройки | Название, slug, валюта, min stay nights, payment instructions |

### 2.2 Схема территории

| Требование | Детали |
|------------|--------|
| Карта | 2D схема; точки `map_points` |
| Объекты на схеме | Клик → карточка + календарь |
| Список | Fallback без карты (mobile) |

### 2.3 Объекты (`bookable_objects`)

| Требование | Детали |
|------------|--------|
| CRUD в админке | Название, код, статус (active/maintenance/unlisted) |
| Фото | `object_photos` — галерея на карточке |
| Check-in/out | Default territory + override per object (local time) |
| Цена | Base price; валюта territory |
| Владелец | Обязательная ссылка на `owner` |
| Multi-object | Несколько объектов в одной брони |

### 2.4 Владельцы (`owners`)

| Требование | Детали |
|------------|--------|
| Party extension | Owner = parties + booking metadata |
| Несколько owners | Список + фильтр по owner в админке |

### 2.5 Права управления объектами

| Требование | Детали |
|------------|--------|
| `management_permissions` | Scope: territory / owner / object |
| Роли | territory_admin, owner_viewer, owner_finance, platform_support |
| RBAC | Platform role → модуль; fine-grain → booking permissions |

### 2.6 Бронирование

| Требование | Детали |
|------------|--------|
| Multi-object booking | `booking_order` + N `booking_items` |
| Разные даты | Каждый item — свой check-in / check-out |
| Availability | Блок конфликтов; учёт confirmed + active hold |
| Hold 30 minutes | Soft hold + countdown в UI |
| Статусы | draft → held → pending_payment → paid → confirmed; cancelled / expired |

### 2.7 Оплата

| Требование | Детали |
|------------|--------|
| Manual confirmation | Admin «Оплата получена» → paid → confirmed |
| Реквизиты на странице | Без online gateway |
| Finance hook | Optional invoice/payment через finance module |

### 2.8 Telegram notifications

| Событие | Получатели |
|---------|------------|
| Новая бронь | territory_admin + owner |
| Оплата подтверждена | owner + admin |
| Hold истёк | post-MVP: guest email/SMS |

### 2.9 Admin panel

- Dashboard: заезды/выезды, pending payment, active holds.
- CRUD territory, map, objects, owners, permissions.
- Booking list; manual payment approve/reject.
- Audit feed (read-only).

### 2.10 Mobile public booking page

- Mobile web, без login.
- URL по slug territory.
- Карта, календарь, корзина, hold timer.
- Guest form → party (имя, телефон).

### 2.11 WhatsApp link

- Кнопка «Написать в WhatsApp» на публичной странице и в confirmation.
- Номер из `territories.settings_json`.
- **Без WhatsApp Business API.**

### 2.12 2GIS link

- Публичная booking URL размещается в карточке 2GIS вручную.
- `booking_orders.source` = `2gis` при referrer/UTM.
- **Без API 2GIS.**

## 3. Out of scope (явно не MVP)

| Область | Статус |
|---------|--------|
| WhatsApp API | Только deep link |
| Online payments | Manual only |
| Marketplace / public catalog | Future |
| Separate brand | Запрещено |
| Вторая+ territory в UI | Post-MVP |
| OTA / external channel sync | Future |
| Dynamic pricing | Post-MVP |
| Tenant customization (бренд) | CR layer |
| Auth changes для public | Отдельный approval |

## 4. Нефункциональные требования

| Область | Target |
|---------|--------|
| Hold integrity | Один active hold на object-interval; race → 409 |
| TZ | UTC storage; business rules из territory timezone |
| Audit | create/update/status через Core AuditRecorder |
| Module guard | `require_module("booking")` |
| Performance | Availability < 500 ms при ≤ 50 objects |

## 5. Критерии приёмки MVP

1. Admin создаёт territory, 3+ objects с фото, 2 owners, карту.
2. Guest с телефона бронирует 2 objects с разными датами.
3. Hold 30 min; после expiry — новый hold.
4. Admin подтверждает оплату → confirmed; Telegram owner получен.
5. Конфликт слота блокируется.
6. Owner видит только свои objects.
7. WhatsApp link открывается с pre-filled текстом.
8. Заказ с UTM `2gis` сохраняет source.
9. Audit фиксирует ключевые события.

## 6. Этапы после документации

| Этап | Результат |
|-------|-------------|
| **E1** | Models + migrations (plan only → approval → code) |
| **E2** | Availability + hold engine |
| **E3** | Public page + cart |
| **E4** | Admin + manual payment |
| **E5** | Telegram |
| **E6** | Hardening |

Детали E1: [IMPLEMENTATION_PLAN_E1.md](./IMPLEMENTATION_PLAN_E1.md).

## 7. Связанные документы

- [README.md](./README.md)
- [PRODUCT_CONCEPT.md](./PRODUCT_CONCEPT.md)
- [DATA_MODEL.md](./DATA_MODEL.md)
- [FLEXITY_INTEGRATION.md](./FLEXITY_INTEGRATION.md)
- [IMPLEMENTATION_PLAN_E1.md](./IMPLEMENTATION_PLAN_E1.md)
