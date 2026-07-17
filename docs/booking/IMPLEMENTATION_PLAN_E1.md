# Flexity Booking — Implementation Plan E1

**E1 = models + migrations only** (persistence layer).

**Status: E1 implemented and validated** (2026-07-02 closeout).

## Approval status

| Item | Status |
|------|--------|
| Documentation cleanup (B3–B5) | **Done** |
| Recorded E1 decisions (§2) | **Done** |
| Explicit approval to start E1 code | **Done** |
| E1 implementation | **Done** |
| Migration validation | **Done** (isolated + staging PostgreSQL) |

---

## E1 closeout (2026-07-02)

Delivered:

- `backend/app/modules/booking/` — enums + models (9 tables, `booking_*` prefix)
- `backend/alembic/versions/20250702_0012_phase12_booking_e1.py` — revision `0012_booking_e1`
- `backend/app/modules/models.py` — booking model imports
- `backend/tests/test_booking_models.py` — 8 tests

**Not touched:** routes, public/admin UI, auth, Telegram, seed (`module_registry`, `subscriptions`), marketplace, payments, external channels.

### Validation results

| Check | Result |
|-------|--------|
| `python -m compileall app/modules/booking` | Pass |
| `pytest tests/test_booking_models.py -v` | **8 passed** |
| Isolated migration `0012_booking_e1` upgrade | Pass — 9 `booking_*` tables created |
| Isolated migration downgrade `-1` | Pass — booking tables removed |
| Re-upgrade `head` | Pass — revision `0012_booking_e1` |
| Staging `alembic upgrade head` (PostgreSQL) | **Done** — revision `0012_booking_e1`, 9 `booking_*` tables |

**Staging command (operator):**

```bash
cd backend
# ensure .env DATABASE_URL points to staging PostgreSQL
python -m alembic upgrade head
python -m alembic current   # expect 0012_booking_e1
# optional downgrade test on staging if policy allows:
# python -m alembic downgrade -1 && python -m alembic upgrade head
```

---

## 1. Цель E1

Заложить persistence layer для Flexity Booking:

- SQLAlchemy models в `backend/app/modules/booking/`;
- одна Alembic migration с booking domain tables;
- unit tests на models/constraints;
- **без** business services, routes, frontend, Telegram, seed.

**Не входит в E1:** module_registry seed, subscription entitlements seed (→ **E1b**).

---

## 2. Recorded decisions (E1 approval cleanup)

Soft blockers B3–B5 закрыты документально. Решения обязательны для E1 code.

### 2.1 B3 — `booking_object_photos` storage

| Rule | Decision |
|------|----------|
| E1 required | `url` and/or `storage_path` on `booking_object_photos` |
| E1 optional | `document_file_id` nullable FK → Core `document_files` **only if** verified safe at E1 kickoff |
| Default E1 | **url/path only**; defer `document_files` FK to **E1b** if uncertain |
| Rationale | Core `document_files` exists, but coupling to documents module needs separate verification |

**E1 schema (minimum):**

```
booking_object_photos:
  id, tenant_id, bookable_object_id
  url          — required for MVP gallery (external or static path)
  storage_path — optional internal path
  alt_text, sort_order
  document_file_id — nullable; omit FK in migration if E1b deferred
  created_at
```

### 2.2 B4 — Commissions

| Table | E1 |
|-------|-----|
| `booking_commission_rules` | **In E1** |
| `booking_commission_accruals` | **Out of E1** — deferred to **E2** |

Accruals and payout logic are not part of persistence bootstrap.

### 2.3 B5 — Module registry / seed

| Deliverable | Phase | Approval |
|-------------|-------|----------|
| `module_registry` seed (`booking` module definition) | **E1b** | Separate micro-approval |
| Subscription features / entitlements seed | **E1b** | Separate micro-approval |
| E1 code | E1 | CR + this plan explicit approval |

**E1 must not modify** `module_registry/seed.py` or `subscriptions/seed.py`.

### 2.4 B6 — Table naming (closed)

All new booking domain tables **must** use `booking_*` prefix. No unprefixed domain tables in E1 migration.

---

## 3. Границы E1

### In scope

| # | Deliverable |
|---|-------------|
| 1 | Models для E1 tables (§4) |
| 2 | Alembic migration `YYYYMMDD_booking_e1.py` |
| 3 | Repository skeleton (read-only list/get) — optional minimal |
| 4 | Unit tests: model constraints, FK, unique indexes |
| 5 | `python -m compileall` + pytest model tests |

### Out of scope (не E1)

| Область | Phase |
|---------|-------|
| `booking_commission_accruals` | **E2** |
| `module_registry` seed | **E1b** |
| Subscription entitlements seed | **E1b** |
| `document_files` FK on object photos (if deferred) | **E1b** |
| Availability service | E2 |
| Hold logic / expire job | E2 |
| Admin + public API routes | E3–E4 |
| Telegram integration | E5 |
| Frontend (admin, public page) | E3–E4 |
| Finance invoice/payment creation | E4 |
| external_channels tables | Post-MVP |
| WhatsApp API | Post-MVP |
| Marketplace | Future |
| Auth changes for public slug | E3 (отдельный approval) |

---

## 4. Новые таблицы (E1 migration)

**Naming rule:** all tables use `booking_*` prefix.

| Table | E1 |
|-------|-----|
| `booking_territories` | Yes |
| `booking_owners` | Yes |
| `booking_bookable_objects` | Yes |
| `booking_object_photos` | Yes — url/path; see §2.1 |
| `booking_map_points` | Yes |
| `booking_orders` | Yes |
| `booking_items` | Yes |
| `booking_management_permissions` | Yes |
| `booking_commission_rules` | Yes |
| `booking_commission_accruals` | **No — E2** |

### Не создавать в E1

- `booking_commission_accruals`
- `external_channel_connections`
- `external_booking_refs`
- `booking_audit_logs` (use Core audit)

---

## 5. Core tables — переиспользуются (FK only)

| Core table | Usage in booking |
|------------|------------------|
| `tenants` | `tenant_id` FK |
| `users` | `created_by_user_id`, permissions |
| `parties` | `guest_party_id`, `booking_owners.party_id` |
| `invoices` | `booking_orders.invoice_id` nullable |
| `payments` | `booking_orders.payment_id` nullable |
| `work_items` | `booking_orders.work_item_id` nullable |
| `document_files` | optional nullable FK on photos — **E1b if deferred** |
| Audit | via AuditRecorder, no new table |

**Finance rule:** `booking_orders` / `booking_items` are domain entities. Invoices and payments stay in **finance** — not duplicated.

---

## 6. Key constraints (migration)

| Constraint | Table | Rule |
|------------|-------|------|
| UNIQUE | `booking_territories` | `(tenant_id, code)`, `(tenant_id, slug)` |
| UNIQUE | `booking_bookable_objects` | `(territory_id, code)` |
| UNIQUE | `booking_map_points` | `(bookable_object_id)` |
| UNIQUE | `booking_management_permissions` | `(tenant_id, user_id, scope_type, scope_id, permission)` |
| CHECK | `booking_items` | `check_out_at > check_in_at` |
| INDEX | `booking_items` | `(bookable_object_id, check_in_at, check_out_at)` |
| INDEX | `booking_orders` | `(tenant_id, status, hold_expires_at)` |

**Hold exclusion:** full exclusion constraint optional E2; E1 — index only.

**Single active territory:** application check in E2; partial unique index deferred.

---

## 7. Time fields (E1 schema)

| Field | Storage |
|-------|---------|
| `default_check_in_time`, `check_in_time` | `TIME` — local territory |
| `check_in_date`, `check_out_date` | `DATE` — local calendar |
| `check_in_at`, `check_out_at`, `hold_expires_at` | `TIMESTAMPTZ` — UTC |
| `created_at`, `updated_at` | `TIMESTAMPTZ` — UTC |

Conversion logic — E2. Multi-object preserved via `booking_orders` 1→N `booking_items`.

---

## 8. Files to touch (after explicit approval)

| File | Action |
|------|--------|
| `backend/app/modules/booking/models.py` | create |
| `backend/app/modules/booking/__init__.py` | create |
| `backend/app/modules/models.py` | import booking models |
| `backend/alembic/versions/YYYYMMDD_booking_e1.py` | create |
| `backend/tests/test_booking_models.py` | create |

### Forbidden in E1

- `backend/app/modules/module_registry/seed.py` — **E1b**
- `backend/app/modules/subscriptions/seed.py` — **E1b**
- `backend/app/main.py` route registration
- `frontend/**`
- `auth/**` changes
- `.env`, deployment config

### E1b files (separate micro-approval, not E1)

| File | Action |
|------|--------|
| `backend/app/modules/module_registry/seed.py` | add `booking` module |
| `backend/app/modules/subscriptions/seed.py` | booking features/limits |
| E1 migration add-on (optional) | `document_file_id` FK on photos |

---

## 9. Test plan (E1)

| Test | Expected |
|------|----------|
| Migration up/down | Clean on empty DB |
| FK integrity | Cannot insert orphan `booking_item` |
| Unique territory slug | Duplicate → error |
| `booking_item` dates | check_out > check_in |
| Tenant isolation | All booking tables have `tenant_id` |
| Nullable finance FKs | Order without invoice OK |
| `booking_object_photos` | url/path required; no accruals table |

```bash
cd backend
python -m pytest tests/test_booking_models.py -v
python -m compileall app/modules/booking
```

---

## 10. Rollback strategy

1. **Alembic downgrade:** `alembic downgrade -1` removes booking E1 tables.
2. **Code rollback:** revert PR; remove booking import from `modules/models.py`.
3. **Data:** E1 on staging only until E2 validated.
4. **Seed:** not in E1 — no seed rollback needed for E1.

No destructive ops on Core tables.

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Table naming conflict | Mandatory `booking_*` prefix (§2.4) |
| FK to finance | Nullable FKs; names verified: `invoices`, `payments`, `work_items` |
| Over-scoping E1 | Accruals, seed, document_files FK explicitly out |
| TZ schema wrong | Align with DATA_MODEL time rules |
| Photos storage creep | url/path only in E1 unless kickoff confirms document_files FK |

---

## 12. Acceptance criteria (E1 done)

- [x] E1 tables exist per §4 (no accruals)
- [x] All tables use `booking_*` prefix
- [x] `booking_object_photos` supports url/path
- [x] Migration applies and rolls back (isolated validation)
- [x] Models registered in SQLAlchemy metadata
- [x] Model tests pass (8/8)
- [x] No routes, auth, frontend, seed changes

---

## 13. Approval checklist

### Documentation decisions (closed)

- [x] B3: object photos — url/path in E1; `document_files` FK → E1b if uncertain
- [x] B4: `booking_commission_accruals` → E2; rules only in E1
- [x] B5: module_registry + entitlements seed → E1b
- [x] B6: mandatory `booking_*` table prefix
- [x] Finance FK targets verified: `invoices`, `payments`, `work_items`, `parties`, `tenants`, `users`

### E1 approval and delivery (closed)

- [x] CR-2026-07-02-001 approved for **E1 implementation**
- [x] This plan explicitly approved
- [x] E1 code merged: models, migration, tests
- [x] Isolated migration upgrade / downgrade / re-upgrade validated
- [x] Staging PostgreSQL `alembic upgrade head` — revision `0012_booking_e1`

**Status:** **E1 complete** — code, tests, isolated migration, staging validated.

---

## 14. Phase map (reference)

| Phase | Scope |
|-------|-------|
| **E1** | Models + migration (this plan) |
| **E1b** | module_registry seed, entitlements seed, optional document_files FK |
| **E2** | availability, hold, `booking_commission_accruals` |
| **E3–E5** | public page, admin, Telegram |

---

## 15. Связанные документы

- [README.md](./README.md)
- [DATA_MODEL.md](./DATA_MODEL.md)
- [MVP_SCOPE.md](./MVP_SCOPE.md)
- [FLEXITY_INTEGRATION.md](./FLEXITY_INTEGRATION.md)
- [../ai/CHANGE_REQUESTS.md](../ai/CHANGE_REQUESTS.md)
