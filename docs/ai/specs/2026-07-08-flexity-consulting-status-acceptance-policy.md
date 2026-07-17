# Flexity Consulting Status Acceptance Policy (C1)

**Дата:** 2026-07-08  
**Статус:** C1 policy baseline  
**Режим:** documentation-only

---

## Purpose

Зафиксировать policy для обработки legacy статусов до C2 import script planning.

---

## Accepted mappings

### Orders -> Work Items

- `COMPLETED` -> `won`
- `IN_PROGRESS` -> `in_progress`
- `CONTRACT_PENDING` -> `open`
- `CANCELLED` -> `cancelled`
- unknown/`NULL` -> fallback `open` + `needs_review`

### Order stages

- `NOT_STARTED` -> `not_started`
- `DONE` -> `done`
- unknown/`NULL` -> `needs_review`

### Contracts -> Documents

- `SIGNED` -> `signed`
- `COMPLETED` -> `archived`
- `ON_REVIEW` -> `sent_for_review`
- `CANCELLED` -> `cancelled`
- unknown/`NULL` -> fallback `draft` + `needs_review`

### Payments

- `INCOME` -> `direction=incoming`, `status=completed`
- `EXPENSE` -> `direction=outgoing`, `status=completed`
- unknown/`NULL` -> `direction=needs_review`, `status=pending`

---

## Acceptance thresholds

1. Любой unknown/unmapped статус обязан попадать в review bucket.
2. Импорт не может silently нормализовать неизвестный статус в финальный бизнес-статус без флага review.
3. Если доля status review выше согласованного порога (определяется перед C2), batch блокируется для ручной проверки.

---

## C1 boundary

Policy утверждает только mapping contract и fallback стратегию.
Реальное применение policy в import script остаётся вне C1.
