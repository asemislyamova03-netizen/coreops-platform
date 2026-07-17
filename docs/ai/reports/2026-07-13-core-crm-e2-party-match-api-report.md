# Report: Core CRM E2 — Contact Match API

**Дата:** 2026-07-13  
**Проект:** Flexity / `coreops-platform`  
**Тип:** Backend local slice (read-only Match API)  
**Статус:** ✅ **IMPLEMENTED (local)** — deploy не выполнялся  
**Prerequisite:** `docs/ai/plans/2026-07-13-core-crm-e2-contact-match-dedup-plan.md`

---

## Goal

Read-only `POST /api/v1/parties/match` — найти существующие Party по контактам (exact/weak), **без** create / merge / auto-link / WorkItem.

---

## Endpoint

```http
POST /api/v1/parties/match
Authorization: Bearer …
X-Tenant-ID: …
```

| Case | Result |
|------|--------|
| Empty / all-blank body | **422** |
| Valid contacts | **200** + `matches` + `query_normalized` |
| Side effects | none (no Party/WorkItem writes) |

Route registered **before** `GET /parties/{party_id}` to avoid shadowing.

---

## Matching

| Key | Strength | Storage |
|-----|----------|---------|
| phone | exact | `contact_methods` phone/mobile |
| email | exact | `contact_methods` email |
| whatsapp | exact | whatsapp (+ phone/mobile fallback by digits) |
| telegram_username | exact | `contact_methods` telegram (@ strip) |
| telegram_user_id | exact | telegram CM **numeric** value **or** `metadata_json.telegram.user_id` |
| name | weak | `display_name` contains (Python, Cyrillic-safe) |

Normalization: `backend/app/modules/parties/matching.py`  
Phone: digits only; `8XXXXXXXXXX` → `7…`; reject &lt; 10 digits.

---

## Response shape

```json
{
  "matches": [
    {
      "party_id": "…",
      "display_name": "…",
      "party_type": "person",
      "status": "active",
      "match_type": "exact",
      "score": 95,
      "matched_on": ["email", "phone"],
      "contact_methods": […],
      "recent_work_items": [{"id","title","status","updated_at"}]
    }
  ],
  "query_normalized": { "phone": "…", "email": "…", … }
}
```

- Exact hits first; weak never auto-link candidates for create (E3).
- Limits: exact ≤ 20, weak ≤ 5, recent work items ≤ 3.

---

## Files changed

| File | Change |
|------|--------|
| `backend/app/modules/parties/matching.py` | **New** — normalize/compare helpers |
| `backend/app/modules/parties/schemas.py` | Match request/response models + 422 validator |
| `backend/app/modules/parties/repository.py` | contact_methods by type, parties by ids, telegram metadata candidates, recent WorkItems |
| `backend/app/modules/parties/service.py` | `match_parties()` |
| `backend/app/modules/parties/routes.py` | `POST /match` |
| `backend/tests/test_party_match.py` | **New** — helpers + API cases |

---

## Tests

| Check | Result |
|-------|--------|
| `pytest tests/test_party_match.py -q` | **10 passed** |
| `compileall app/modules/parties` | ✅ |

Covered: normalize, 422 empty, phone/email, telegram username + metadata user_id, whatsapp, weak name, no create side-effect, tenant isolation, multi-party same phone.

---

## Not touched

- Frontend  
- Public inbound  
- Migrations  
- Deploy  
- Party merge / auto-link  

---

## Risks

| Risk | Mitigation |
|------|------------|
| Shared family phone → 2+ exact | UI must force pick (E3) |
| Full-table scan for telegram metadata / weak name | OK for small sales CRM; identities table later |
| Legacy unnormalized CM values | normalize both sides in app |

---

## Next recommended step

**E3** — CreateWorkItemModal: on blur phone/email → call match → «Похожий контакт найден» / «Использовать».

Deploy Match API — separate approval.

---

## HQ summary

| # | Item | Value |
|---|------|-------|
| 1 | **Status** | ✅ Implemented locally |
| 2 | **Endpoint** | `POST /api/v1/parties/match` |
| 3 | **Exact keys** | phone, email, whatsapp, telegram_username, telegram_user_id |
| 4 | **Weak** | name only |
| 5 | **Empty body** | 422 |
| 6 | **Creates Party/WorkItem** | ❌ No |
| 7 | **Merge/auto-link** | ❌ No |
| 8 | **Tests** | 10 passed |
| 9 | **Backend only** | ✅ |
| 10 | **Migrations** | ❌ No |
| 11 | **Deploy** | ❌ No |
| 12 | **Next** | E3 create-lead dedup UI |
