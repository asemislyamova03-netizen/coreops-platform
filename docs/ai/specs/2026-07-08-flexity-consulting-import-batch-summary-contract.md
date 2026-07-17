# Flexity Consulting Import Batch Summary Contract (C1)

**Дата:** 2026-07-08  
**Статус:** C1 local readiness contract  
**Режим:** documentation-only

---

## Purpose

Определить единый batch-level audit summary контракт для будущего импорта legacy Consulting данных в Core, без запуска import script в C1.

---

## Contract fields

- `id` — UUID batch summary.
- `tenant_id` — tenant, в который планируется импорт.
- `created_by_user_id` — оператор импорта (nullable).
- `source_system` — ожидаемо `consult_app`.
- `started_at` / `finished_at`.
- `total_source_rows`.
- `total_imported_rows`.
- `total_skipped_rows`.
- `total_error_rows`.
- `total_review_rows`.
- `status_mapping_warnings`.
- `entities[]`:
  - `entity`
  - `source_count`
  - `imported_count`
  - `skipped_count`
  - `error_count`
  - `review_count`
- `notes` (nullable).

---

## Validation rules

1. Все totals неотрицательные.
2. `total_imported_rows + total_skipped_rows + total_error_rows <= total_source_rows`.
3. `status_mapping_warnings` >= 0 и обычно равно числу review-случаев по статусам.
4. `entities` содержит только технические агрегаты, без raw business/PII values.

---

## C1 outcome

В C1 контракт зафиксирован на уровне схемы/сервиса для локальной валидации readiness.
Фактическая генерация batch summary в реальном import pipeline остаётся в C2+.
