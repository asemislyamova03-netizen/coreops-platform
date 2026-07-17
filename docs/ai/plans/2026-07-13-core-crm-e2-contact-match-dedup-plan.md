# Implementation Plan: Core CRM E2 — Contact match / dedup (Match API)

**Дата:** 2026-07-13
**Проект:** Flexity / `coreops-platform`
**Тип:** documentation-only implementation plan
**Статус:** ⏸ **waiting for approval** (код / migrations / deploy — не трогать)
**Prerequisites:** E1–E1.4 deployed on `flexity-sales`; audit
`docs/ai/reviews/2026-07-10-lead-dedup-spam-identities-audit.md`

**CRM URL:** https://flexity.asia/console/workspace/flexity-sales/crm

---

## Goal

Подготовить и (после approval) реализовать **read-only Match API** для поиска существующих Party по контактным данным.

MVP:

- найти Party по phone / email / telegram / whatsapp;
- вернуть **exact** и (опционально) **weak** matches;
- объяснить, по какому ключу совпало;
- **не** создавать Party;
- **не** создавать WorkItem;
- **не** объединять (merge) Party автоматически;
- **не** трогать public inbound в этом slice.

Каждое новое обращение остаётся новым WorkItem; Party переиспользуется только после явного выбора пользователя (UI — E3).

---

## Classification

| Field | Value |
|-------|-------|
| **Project** | Flexity |
| **Category** | `universal_module` (parties) |
| **Risk** | medium (false positive party link if misused; PII in match logs) |
| **Scope** | backend Match API + unit tests; **no migration**; **no frontend in E2** |
| **Forbidden** | migrations, party merge, public inbound enable, auto-link, deploy without approval |

---

## Product model (confirmed)

| Entity | Role |
|--------|------|
| **Party** | человек / организация |
| **WorkItem** | обращение / лид / заявка |
| **ContactMethod** | phone / email / mobile / telegram / whatsapp / other |
| **Relation** | many WorkItems → one Party |

**Не создавать** отдельный «справочник лидов».

---

## Current state (facts)

| Area | Today |
|------|--------|
| Search | `GET /parties?search=` → **только** `display_name ILIKE` |
| Phone/email unique | ❌ нет unique на `(tenant_id, method_type, value)` |
| Match API | ❌ нет |
| Merge API | ❌ нет |
| Public inbound | всегда `_create_party()` — новый Party |
| Storage | `contact_methods` + `parties.metadata_json` |
| Instagram enum | ❌ нет; convention `other` + `label=instagram` |
| Disposition (E1) | уже есть: close/reopen + disposition codes |

**Key files (read-only for plan):**

- `backend/app/modules/parties/routes.py`
- `backend/app/modules/parties/service.py`
- `backend/app/modules/parties/repository.py`
- `backend/app/modules/parties/models.py`
- `backend/app/modules/parties/schemas.py`
- `backend/app/core/enums.py` (`ContactMethodType`)
- `backend/app/modules/public_leads/service.py` (out of E2 scope)

---

## 1. Match API proposal

### Endpoint

```http
POST /api/v1/parties/match
```

**Почему POST, не GET:**

- несколько идентификаторов в одном запросе (phone + email + telegram…);
- body удобнее для нормализации и будущих полей;
- не логируется в access logs как query string с PII.

**Auth / tenancy:** тот же guard, что у parties module:

```python
ctx: TenantContext = Depends(require_module("parties"))
```

Поиск **строго** в рамках `ctx.tenant.id`.

### Почему не расширять `GET /parties?search=`

| Approach | Verdict |
|----------|---------|
| `GET /parties?phone=&email=` | слабо: нормализация, multi-match, strength, explanations |
| `POST /parties/match` | ✅ dedicated contract, exact/weak, match reasons |
| Search only by name | уже есть; слабый сигнал |

### Request body (MVP)

```json
{
  "name": "Иван",
  "phone": "+7 777 123 45 67",
  "email": "ivan@example.com",
  "telegram_username": "@ivan",
  "telegram_user_id": "123456789",
  "whatsapp": "+77771234567"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | no | only for **weak** name hint |
| `phone` | no | exact after normalize |
| `email` | no | exact after normalize |
| `telegram_username` | no | exact after normalize |
| `telegram_user_id` | no | exact string match |
| `whatsapp` | no | exact after phone-like normalize |

**Validation:**

- хотя бы один из: `phone`, `email`, `telegram_username`, `telegram_user_id`, `whatsapp`
  (если только `name` → вернуть empty exact + optional weak, или `400` с ясным сообщением — **рекомендация: 200 + empty exact, weak name optional**);
- max lengths как у ContactMethod (`value` ≤ 320).

### Response body (MVP)

```json
{
  "exact_matches": [
    {
      "party_id": "uuid",
      "display_name": "Иван Петров",
      "party_type": "person",
      "status": "active",
      "matched_on": ["phone", "email"],
      "match_strength": "exact",
      "contact_methods_preview": [
        { "method_type": "phone", "value": "+77771234567", "is_primary": true },
        { "method_type": "email", "value": "ivan@example.com", "is_primary": false }
      ],
      "open_work_items_count": 1
    }
  ],
  "weak_matches": [
    {
      "party_id": "uuid",
      "display_name": "Иван",
      "matched_on": ["name"],
      "match_strength": "weak",
      "contact_methods_preview": [],
      "open_work_items_count": 0
    }
  ],
  "query_normalized": {
    "phone": "7771234567",
    "email": "ivan@example.com",
    "telegram_username": "ivan",
    "telegram_user_id": "123456789",
    "whatsapp": "7771234567"
  }
}
```

**Rules:**

- `exact_matches` — только exact keys;
- `weak_matches` — **только name** (ILIKE / prefix), **never** auto-link candidate for create;
- один Party не дублируется в обоих списках (если exact — только в exact);
- limit: `exact_matches` ≤ 20, `weak_matches` ≤ 5;
- `open_work_items_count` — optional nice-to-have (count WorkItems with `primary_party_id` and non-terminal / `in_progress|open`); можно отложить в E2.1 если усложняет.

---

## 2. Normalization rules

Вынести в чистые функции (testable):

| Input | Normalize | Match against ContactMethod |
|-------|-----------|-----------------------------|
| **email** | `strip().lower()` | `method_type=email`, compare normalized stored value (normalize both sides in app) |
| **phone** | digits only; if starts with `8` and len=11 → treat as `7…`; drop leading country formatting | `method_type IN (phone, mobile)` |
| **whatsapp** | same as phone | `method_type=whatsapp` **or** phone/mobile if same digits (document: prefer whatsapp type first, then phone/mobile as exact) |
| **telegram_username** | strip, lower, remove leading `@` | `method_type=telegram`, value equals username **or** `@username` after normalize |
| **telegram_user_id** | strip digits/string as-is | `method_type=telegram` value exact **OR** `parties.metadata_json.telegram.user_id` (JSON path) |
| **name** | strip; ILIKE `%name%` on `display_name` | weak only |

**Important:** DB values today are **not** pre-normalized. E2 нормализует **в Python** при сравнении (или SQL functions), без migration / backfill.

**Performance note:** для tenant с малым числом parties (sales CRM) допустим:

1. query candidate ContactMethods by `tenant_id` + `method_type IN (...)`;
2. filter in Python by normalized value;

или SQL `regexp_replace` for phone digits — preferred if Postgres available and tests cover it.

**MVP recommendation:** repository method that loads candidates by type + tenant, normalize in service. If too slow later → add `normalized_value` column (E-later / identities table).

---

## 3. Matching logic (exact vs weak)

### Exact (auto-suggest eligible)

Priority order for `matched_on` labeling (same Party can match multiple):

1. `telegram_user_id`
2. `email`
3. `phone` (incl. mobile)
4. `whatsapp`
5. `telegram_username`

### Weak (warning only)

- `display_name` ILIKE / contains — **never** alone for auto-link in E3.

### Ambiguous cases

| Case | Behavior |
|------|----------|
| 0 exact | empty `exact_matches` |
| 1 exact | single suggestion |
| 2+ exact | return all; UI must force user pick (E3) |
| exact + weak for same party | only in `exact_matches` |
| same phone on 2 parties | return both exact — user decides |

**No scoring merge / no auto-pick “best” Party in E2.**

---

## 4. WhatsApp / Instagram / Telegram storage mapping

| Channel | E2 match source | Later |
|---------|-----------------|-------|
| Phone | `contact_methods` phone/mobile | identities table |
| Email | `contact_methods` email | — |
| WhatsApp | `contact_methods` whatsapp (+ fallback phone digits) | wa_id |
| Telegram username | `contact_methods` telegram | — |
| Telegram user_id | telegram CM value **or** `metadata_json.telegram.user_id` | `party_external_identities` |
| Instagram | **out of E2 request body** (optional later: `instagram_username` → `other`+label) | enum or identities |

E2 request **не требует** Instagram field in MVP; document as E2.1 / E4.

---

## 5. Scope of E2 implementation (after approval)

### In scope

| Item | Detail |
|------|--------|
| Schema | `PartyMatchRequest`, `PartyMatchResponse`, `PartyMatchHit` |
| Service | `PartyMatchService` or methods on `PartyService` |
| Repository | query helpers for contact_methods by types |
| Route | `POST /parties/match` |
| Normalization helpers | phone/email/telegram |
| Tests | unit + API tests |
| Docs | this plan + short report after build |

### Out of scope (explicit)

| Item | When |
|------|------|
| Frontend CreateWorkItemModal | **E3** |
| LeadDetailModal previous WorkItems | **E4** |
| Public inbound match-before-create | **E5** (only when inbound approved) |
| Party merge API | **E-later** |
| Alembic / `party_external_identities` | **E-later** |
| Deploy | separate approval |
| Changing disposition / CRM board | already E1–E1.4 |

---

## Scope — files

### Files to modify (after approval)

| File | Change |
|------|--------|
| `backend/app/modules/parties/schemas.py` | Match request/response models |
| `backend/app/modules/parties/service.py` | `match_parties()` orchestration |
| `backend/app/modules/parties/repository.py` | candidate ContactMethod / Party queries |
| `backend/app/modules/parties/routes.py` | `POST /match` (**before** `/{party_id}` route!) |
| `backend/app/modules/parties/matching.py` | **New** — normalize + compare helpers |
| `backend/tests/test_party_match.py` | **New** — exact/weak/edge cases |

### Files not to touch

- migrations / alembic
- `public_leads/**`
- `platform-console/**` (E3)
- env, nginx, deploy scripts
- Margosya, Booking, Clinic, Trailers
- disposition / workflows (E1 already done)

**Route order warning:** FastAPI must register `/parties/match` **before** `/parties/{party_id}`, иначе `match` распарсится как UUID → 422.

---

## Steps (implementation after approval)

### Step 1 — Normalization helpers + unit tests

1. Create `matching.py` with:
   - `normalize_email`
   - `normalize_phone_digits`
   - `normalize_telegram_username`
   - `normalize_telegram_user_id`
2. Pure unit tests (no DB).

### Step 2 — Repository candidates

1. `list_contact_methods_for_match(tenant_id, method_types: list)`
   or per-type queries joining Party (active preferred; include all non-deleted).
2. Optional: weak name search reusing existing `display_name ILIKE`.

### Step 3 — Service `match_parties`

1. Normalize input.
2. Collect Party IDs per exact key.
3. Aggregate `matched_on` per party.
4. Build response; exclude weak if already exact.
5. Load contact_methods preview for hits.

### Step 4 — Route + OpenAPI

1. `POST /parties/match`
2. Module entitlement `parties`
3. No audit write for match MVP (or light audit — decide: **skip audit in E2** to reduce noise; document).

### Step 5 — API tests

Cases:

| # | Case | Expect |
|---|------|--------|
| 1 | phone match | 1 exact, matched_on includes phone |
| 2 | email match | exact |
| 3 | phone format variants (`+7`, `8`, spaces) | same party |
| 4 | telegram username `@User` vs `user` | exact |
| 5 | telegram_user_id | exact |
| 6 | whatsapp | exact |
| 7 | no contacts given, only name | weak only or empty exact |
| 8 | two parties same phone | 2 exact |
| 9 | tenant isolation | other tenant not returned |
| 10 | empty body contacts | 200 empty or 422 — pick one & test |

### Step 6 — Report (no deploy until approved)

`docs/ai/reports/YYYY-MM-DD-core-crm-e2-party-match-api-report.md`

---

## Tests / checks

```bash
cd backend
python -m pytest tests/test_party_match.py -q
python -m compileall app/modules/parties
```

Manual (local API):

1. Create Party A with phone + email.
2. `POST /parties/match` with same phone → exact.
3. Match with only wrong phone → empty exact.
4. Match with name substring → weak only.
5. Confirm OpenAPI shows `/parties/match`.

---

## Risks

| Risk | Mitigation |
|------|------------|
| False exact link (shared family phone) | E2 returns candidates only; E3 requires user confirm; never auto-merge |
| Unnormalized legacy values | normalize both sides; document imperfect historical data |
| `telegram` CM stores both username and user_id | prefer metadata for user_id; match both patterns carefully |
| Route shadowing `{party_id}` | declare `/match` before `/{party_id}` |
| PII in logs | avoid logging full request body |
| Performance at scale | accept Python normalize for MVP; identities table later |
| WhatsApp = phone ambiguity | return matched_on clearly (`whatsapp` vs `phone`) |

---

## Rollback

- Revert parties match files; no migration to undo.
- Deploy rollback = previous backend artifacts (if ever deployed).

---

## Sequence after E2

```text
E2 Match API (this plan)
  → E3 CreateWorkItemModal: blur → match → “Использовать контакт”
  → E4 LeadDetailModal: previous WorkItems + identity fields
  → E5 public inbound: match-before-create (when inbound approved)
  → E-later: party_external_identities + merge
```

**Default next after E2 code:** E3 frontend dedup UX (not deploy of public inbound).

---

## Approval

**Status: waiting for approval**

После approval — реализовать только Steps 1–5 (backend + tests).
Frontend / public inbound / migrations / deploy — отдельные approvals.

---

## HQ summary (quick)

| # | Item | Answer |
|---|------|--------|
| 1 | **Root problem** | Public/manual intake can create duplicate Parties; no contact search beyond name |
| 2 | **E2 goal** | Read-only Match API; exact/weak; no create/merge |
| 3 | **Endpoint** | `POST /api/v1/parties/match` |
| 4 | **Exact keys** | phone, email, telegram_username, telegram_user_id, whatsapp |
| 5 | **Weak key** | display_name only |
| 6 | **Migration** | ❌ No for E2 |
| 7 | **Frontend** | ❌ Not in E2 (→ E3) |
| 8 | **Public inbound** | ❌ Not in E2 (→ E5) |
| 9 | **Files** | parties schemas/service/repository/routes + `matching.py` + tests |
| 10 | **Next slice after approve** | Implement Match API Steps 1–5 |
| 11 | **Then** | E3 create-lead dedup UI |
