# Implementation Plan: S3/E5 — Public inbound `/demo` → flexity-sales with match

**Дата:** 2026-07-13
**Проект:** Flexity / `coreops-platform`
**Тип:** documentation-only implementation plan
**Статус:** ⏸ **waiting for approval** (код / env / deploy / enable — **не трогать** в этой сессии)

**Prerequisites (already deployed on flexity-sales):**
- E1–E1.4 disposition + board/list UX
- E2 Match API `POST /parties/match`
- E3 CreateWorkItemModal match UI
- E4 LeadDetailModal party history

**Related docs:**
- `docs/ai/plans/2026-06-24-public-inbound-leads-runbook.md`
- `docs/ai/plans/2026-07-03-public-inbound-b2b-plan.md`
- `docs/ai/reviews/2026-07-03-public-inbound-b2b-local-smoke-report.md`
- `docs/ai/plans/2026-07-13-core-crm-e2-contact-match-dedup-plan.md`

**CRM:** https://flexity.asia/console/workspace/flexity-sales/crm
**Landing:** https://www.flexity.asia/demo/ (SUBMIT_URL → `https://flexity.asia/api/v1/public/leads`)

---

## Goal

Безопасно включить public inbound с `/demo` в tenant **flexity-sales** так, чтобы:

1. каждая заявка создавала **новый WorkItem**;
2. при **exact** phone/email match **переиспользовать** существующий Party (без дубля);
3. source/UTM сохранялись;
4. спам контролировался honeypot + (обязательный) rate limit + ручной disposition E1;
5. enablement был **явным** через env, не случайным.

E5 **не** делает merge Party, **не** auto-spam, **не** показывает match-детали анонимному клиенту.

---

## Classification

| Field | Value |
|-------|-------|
| **Project** | Flexity |
| **Category** | `documentation_only` now → later `universal_module` (public_leads + parties match) |
| **Risk** | **high** (public internet surface; PII; wrong Party link; spam flood) |
| **Intended scope (after approvals)** | `PublicLeadService` match-before-create + rate limit + env enable on server |
| **Forbidden now** | code, migrations, deploy, env changes, enabling inbound, live landing edits, prod test leads |

### Task Classification (coordinator)

1. **Project:** Flexity
2. **Category:** documentation_only
3. **Risk level:** high (for future enable; plan itself low)
4. **Intended scope:** this plan file only
5. **Forbidden scope:** production code/server/env/landing live
6. **Required plan:** documentation-only → this document

---

## 1. Current public inbound audit (facts)

### Endpoint / service

| Item | Status |
|------|--------|
| Path | `POST /api/v1/public/leads` |
| Router | `backend/app/api/v1/public_leads.py` |
| Service | `backend/app/modules/public_leads/service.py` → `PublicLeadService.create_lead` |
| Schemas | `PublicLeadCreate` / `PublicLeadResponse` |
| Included in API | ✅ `api_router.include_router(public_leads_router)` |
| Auth | ❌ public (no Bearer) |

### Server runtime (2026-07-13 read-only)

| Check | Result |
|-------|--------|
| `POST /public/leads` | **403** `Public lead capture is disabled` |
| `PUBLIC_LEADS_*` in `/opt/flexity/coreops/backend/.env` | **absent** (defaults: `enabled=false`) |
| Production accidentally enabled | ❌ no |

### Current create behavior (gap for E5)

Today, when enabled, service **always**:

1. `_create_party(...)` — **new Party every time**
2. `_create_work_item(...)` linked to that Party
3. optional Telegram notify (non-blocking)
4. returns `{ status, party_id, work_item_id }`

**No match-before-create.** This is why E5 exists.

### Env settings (`backend/app/core/config.py`)

| Setting | Default | Role |
|---------|---------|------|
| `PUBLIC_LEADS_ENABLED` | `false` | master switch |
| `PUBLIC_LEADS_TARGET_TENANT_ID` | null | flexity-sales UUID |
| `PUBLIC_LEADS_PIPELINE_ID` | null | sales pipeline |
| `PUBLIC_LEADS_STAGE_ID` | null | `new_lead` stage |
| `PUBLIC_LEADS_CREATED_BY_USER_ID` | null | system actor for created_by |
| `PUBLIC_LEADS_ALLOWED_ORIGINS` | `""` | CORS + origin check list |
| `PUBLIC_LEADS_TELEGRAM_BOT_TOKEN` | null | optional notify |
| `PUBLIC_LEADS_TELEGRAM_CHAT_ID` | null | optional notify |

### Consent / honeypot / validation (`PublicLeadCreate`)

| Rule | Behavior |
|------|----------|
| `consent_accepted` | must be `true` else validation error |
| `website` (honeypot) | must be empty else validation error |
| phone **or** email | required |
| message **or** process_area | required |
| name | required |

### Origin / CORS

- If `Origin` header present → must be in `PUBLIC_LEADS_ALLOWED_ORIGINS` (rstrip `/`).
- If `Origin` **missing** → currently **allowed** (documented risk from B2b).
- CORS middleware only registered when allowed origins list non-empty.

### Telegram

- Optional via `PublicLeadTelegramNotifier`.
- Failure is logged; does **not** roll back Party/WorkItem.
- Out of E5 product scope to redesign; keep optional.

### Rate limiting

- ❌ **not implemented** in `public_leads`.
- B2b plan already marked **B2b-1b as production blocker**.
- E5 must treat rate limit as **required before enable**, not optional polish.

---

## 2. Server target IDs (flexity-sales) — confirmed 2026-07-13

Read-only DB capture on production server (**do not use local UUIDs**):

| Target | Value |
|--------|-------|
| **Tenant** | `90553fe9-22d1-458d-ab84-c7353f2d80e2` (`flexity-sales`, status `TRIAL`) |
| **Pipeline** | `67132e1a-5be1-40ec-8908-01ecf199091b` (`flexity_sales`, «Воронка продаж Flexity», default) |
| **Stage `new_lead`** | `8cf199a0-3bc4-42e9-b83e-4db6c5f1a1d2` («Новый лид») |
| **Created-by user** | `79d2a7cb-b8dc-489e-a4e6-d0c9bd18d370` (`asemislyamova03@gmail.com`, `TENANT_OWNER`, active) |

Re-verify these IDs immediately before any enablement (stages can be recreated).

---

## 3. Match-before-create design

### Principle

Reuse E2 matching logic **internally** (call `PartyService.match_parties` / shared matching helpers with target tenant_id).
Do **not** call HTTP Match API from public client.
Do **not** return match candidates to the browser.

### Exact match (phone / email)

If any **exact** hit on phone and/or email (whatsapp only if form later sends it; `/demo` phone field is stored as `phone` today):

1. Pick best exact Party (highest score / first exact from E2 ordering).
2. **Do not** create Party.
3. Create new WorkItem with `primary_party_id = matched.party_id`.
4. Store attribution in WorkItem `custom_fields_json` / description.
5. Add internal note in description or custom field, e.g.
   `Public demo form matched existing contact` + `matched_on=[phone|email]`.
6. Audit metadata: `party_reused=true`, `match_type=exact`.

Ambiguity (multiple exact Parties):

- MVP: pick top exact by E2 order; log warning with party ids in audit/server log (not public response).
- Later CR: human review queue.

### No match

1. Create new Party (current `_create_party`).
2. Create WorkItem linked to it.
3. Audit: `party_reused=false`.

### Weak match only (name)

**Recommended MVP: Option C (safe create + mark candidates)**

| Option | Behavior | Verdict |
|--------|----------|---------|
| A | create Party + `possible_duplicate=true` flag only | weak signal, no candidates |
| B | WorkItem without Party | ❌ breaks CRM/E4 |
| **C** | create **new** Party + WorkItem; store weak candidate party ids in WorkItem `custom_fields_json` (e.g. `possible_match_party_ids`) | ✅ **recommended** |

Rationale:

- Auto-linking on weak name is dangerous for public traffic.
- Creating a new Party keeps intake reliable.
- Operators see history only after E3-style reuse or future merge; E4 helps once Party is correct.
- Optional UI later can surface «возможный дубль» in LeadDetailModal (out of E5 MVP).

Do **not** auto-reuse Party on weak match in E5.

---

## 4. Source mapping

| Today in `PublicLeadService` | CRM dictionary |
|------------------------------|----------------|
| hardcoded `source="public_demo_form"` | canonical code **`website_demo`** («Сайт / демо-заявка») |
| Party metadata `source: public_demo_form` | alias map already: `public_demo_form` → `website_demo` |

### Recommendation

- Change WorkItem `source` to **`website_demo`** (canonical).
- Keep alias so old records still label correctly.
- Party metadata may keep `inbound_channel: public_demo_form` for technical provenance **or** also move to `website_demo` — prefer one canonical `website_demo` + `form_name: demo`.
- **No new source code** → no template seed change required if `website_demo` already applied on tenant (it is in `FLEXITY_SALES_LEAD_SOURCES`).

---

## 5. UTM / attribution storage

Already designed in current service:

| Field | WorkItem `custom_fields_json` | Party `metadata_json` | Description body |
|-------|-------------------------------|------------------------|------------------|
| utm_* | ✅ | ✅ | — |
| referrer | ✅ | ✅ | — |
| source_page | ✅ | ✅ | ✅ |
| company / process_area / message | ✅ | ✅ | message/process |
| consent_accepted | — | ✅ | — |

### E5 additions (recommended)

WorkItem custom fields (no migration if stored in JSON):

- `form_name`: `"demo"`
- `inbound_channel`: `"website_demo"`
- `party_match`: `"exact" | "none" | "weak_only"`
- `matched_on`: e.g. `["phone"]` when exact
- `possible_match_party_ids`: list[str] when weak_only (Option C)
- `match_note`: short RU/EN operator note when exact reused

Optional later: formal CustomFieldDefinition seed — **not required** for MVP JSON.

Consent timestamp: not stored as dedicated field today; MVP can add `consent_accepted_at` ISO timestamp at create time into WorkItem custom_fields (no migration).

---

## 6. Spam / disposition relationship

| Layer | MVP |
|-------|-----|
| Honeypot `website` | ✅ already |
| Consent | ✅ already |
| Rate limit | ❌ must add before enable |
| Auto disposition=spam | ❌ not in E5 |
| Operator close as spam (E1) | ✅ already in CRM |
| Future spam scoring | Change Request later |

Public inbound creates **open** WorkItem in `new_lead`. Асем closes spam via E1.

---

## 7. Landing `/demo` changes

### Current form (already wired)

| Aspect | Status |
|--------|--------|
| `SUBMIT_URL` | `https://flexity.asia/api/v1/public/leads` |
| Fields | name, phone, email, company, process_area, message, consent, honeypot |
| UTM from query | ✅ |
| referrer / source_page | ✅ |
| Success/error UX | ✅ generic (no Party ids shown in UI) |
| preferred_channel | not collected (OK) |

### Landing change needed for E5?

| Change | Needed? |
|--------|---------|
| Point to API | ❌ already |
| Capture UTM | ❌ already |
| Honeypot/consent | ❌ already |
| Maxlength align with schema | optional polish (HTML allows longer than API in some fields) |
| Hide API ids from success | ❌ form already ignores body |
| Live landing edit before backend match | ❌ not required for match logic |

**Recommendation:** no live landing change in first code slice. Optional later maxlength alignment only.

---

## 8. Env / deployment plan (safe enablement)

### Hard rule

Never enable with wrong/local UUIDs. Never enable without rate limit.

### Phased rollout

| Phase | Action | `PUBLIC_LEADS_ENABLED` |
|-------|--------|------------------------|
| **E5-A** | Implement match-before-create + tests locally | false |
| **E5-B** | Implement rate limit + harden public response | false |
| **E5-C** | Deploy backend (still disabled); set UUID env vars; origins | **false** |
| **E5-D** | HQ enable approval → set `ENABLED=true`; one marked test lead | true |
| **E5-E** | Verify CRM List/Board + Party reuse + E4 history; keep or disable | true/false |

### Production env block (draft — apply only after E5-C approval)

```env
PUBLIC_LEADS_ENABLED=false
PUBLIC_LEADS_TARGET_TENANT_ID=90553fe9-22d1-458d-ab84-c7353f2d80e2
PUBLIC_LEADS_PIPELINE_ID=67132e1a-5be1-40ec-8908-01ecf199091b
PUBLIC_LEADS_STAGE_ID=8cf199a0-3bc4-42e9-b83e-4db6c5f1a1d2
PUBLIC_LEADS_CREATED_BY_USER_ID=79d2a7cb-b8dc-489e-a4e6-d0c9bd18d370
PUBLIC_LEADS_ALLOWED_ORIGINS=https://www.flexity.asia,https://flexity.asia
# optional Telegram — separate approval
```

After UUID wiring, restart coreops with **enabled still false**, confirm still **403**.

Test lead title/message must be clearly marked, e.g. `E5 TEST — delete after smoke`.

---

## 9. Security / abuse controls

| Control | MVP requirement |
|---------|-----------------|
| Master disable flag | ✅ |
| Origin allowlist | ✅ set before enable |
| Require Origin? | **Recommend yes for prod** (reject missing Origin) — small hardening in E5-B |
| Honeypot | ✅ |
| Consent | ✅ |
| Rate limit | **Required** before enable (IP-based, e.g. N/min on `/public/leads`) |
| Public response | **Do not expose Party PII/match details**; prefer `{ "status": "created" }` only (drop `party_id` from public response or keep opaque ack) |
| Match internals | server-side only |
| Cross-tenant | targets fixed env tenant; match must use that tenant_id only |
| Detailed errors to client | keep generic 4xx; no stack traces |
| Audit log | keep create audit + match metadata |
| Telegram | optional; no secrets in repo |

**Note:** Current `PublicLeadResponse` returns `party_id` + `work_item_id`. Landing ignores them, but any client can read them. E5-B should shrink response for production safety (breaking change only for API consumers — landing OK).

---

## 10. Tests plan

### Unit / API tests (local)

1. `ENABLED=false` → 403
2. Invalid payload (no consent / honeypot filled / no phone&email) → 422
3. Exact email match → same `party_id`, new `work_item_id`, no extra Party
4. Exact phone match → reuse Party
5. No match → new Party + WorkItem
6. Weak name only → new Party + `possible_match_party_ids` set; **not** auto-link
7. WorkItem tenant/pipeline/stage/source=`website_demo` correct
8. UTM/custom fields stored
9. Public response does not include match candidates / contact methods
10. Cross-tenant: match cannot return other tenant Party
11. Rate limit trips after threshold (when implemented)

### Manual smoke (only after enable approval)

1. Disabled still 403 before flip
2. One test submit from allowed origin
3. Appears in flexity-sales CRM `new_lead`
4. Second submit same phone/email → **same Party**, second WorkItem; E4 history shows first
5. Close as spam via E1 works
6. Kindergarten unchanged

---

## 11. Rollback

| Lever | Action |
|-------|--------|
| Fastest | `PUBLIC_LEADS_ENABLED=false` + restart coreops |
| Code | revert public_leads service deploy from backup |
| Landing | only if landing was changed (MVP expects no change) |
| DB | no migration; optionally delete/close marked test WorkItem+Party with explicit HQ approval |

No alembic rollback required for E5 MVP (JSON fields only).

---

## 12. Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| Spam flood when enabled | high | rate limit gate; honeypot; quick disable |
| Wrong Party exact collision (shared phone) | medium | exact-only reuse; audit matched_on; operator can re-link manually later |
| Weak name false link if ignored recommendation | high | **forbid** weak auto-link |
| Origin header absent bypass | medium | require Origin in prod |
| `party_id` leakage in response | medium | shrink response in E5-B |
| UUID drift after template re-apply | medium | re-capture IDs before enable |
| Telegram failure noise | low | already non-blocking |
| Source label mismatch `public_demo_form` | low | switch to `website_demo` |

---

## 13. Recommended implementation slices

| Slice | Scope | Enable? |
|-------|-------|---------|
| **E5-A** | Match-before-create in `PublicLeadService`; source=`website_demo`; custom match fields; tests | no |
| **E5-B** | Rate limit + require Origin + public response harden | no |
| **E5-C** | Deploy backend disabled + write UUID env + origins; verify 403 | no |
| **E5-D** | HQ enable + one marked test lead + CRM/E4 verify | yes (temporary) |
| **E5-E** | Keep enabled or disable; optional landing maxlength polish | decision |

**Do not** mix Marketing / Telegram product work / merge UI / currency / stages admin into these slices.

### Likely files (code phase — not now)

| File | E5-A/B |
|------|--------|
| `backend/app/modules/public_leads/service.py` | match-before-create |
| `backend/app/modules/public_leads/schemas.py` | response harden (optional) |
| `backend/app/api/v1/public_leads.py` | rate-limit dependency |
| `backend/tests/test_public_leads*.py` | new/extended tests |
| server `.env` | E5-C/D only |
| `landing/www/demo/index.html` | optional later only |

### Files not to touch

- console CRM E1–E4 (already done)
- Match API contract (reuse internally)
- migrations / alembic
- Booking / Clinic / Trailers / Margosya / Marketing Cabinet

---

## Approval

**Status:** ⏸ waiting for approval

Next approval should specify which slice to implement first (**recommend E5-A**, still disabled).
Separate HQ approvals required for: rate-limit approach, env wiring, and **enable**.

---

## HQ summary (plan)

| # | Item | Answer |
|---|------|--------|
| 1 | **Current public inbound status** | Exists in main; **disabled** on server (403); no `PUBLIC_LEADS_*` in prod `.env` |
| 2 | **Existing endpoint/service** | `POST /api/v1/public/leads` → `PublicLeadService` (always new Party today) |
| 3 | **Server IDs** | Tenant / pipeline / `new_lead` / owner user **confirmed** (§2) |
| 4 | **Match-before-create recommendation** | Internal E2 match; exact → reuse Party; weak → Option C new Party + candidate ids |
| 5 | **Exact match behavior** | New WorkItem on existing Party; note + audit; no duplicate Party |
| 6 | **Weak match behavior** | Create new Party; store `possible_match_party_ids`; **no auto-link** |
| 7 | **Source mapping** | Use canonical **`website_demo`** (alias keeps `public_demo_form`) |
| 8 | **UTM/attribution storage** | Keep WorkItem custom_fields + Party metadata; add match/form fields in JSON |
| 9 | **Landing `/demo` changes** | **Not required** for MVP (already posts to prod API) |
| 10 | **Env/deploy plan** | Code first (disabled) → wire UUIDs disabled → enable only after rate limit + HQ |
| 11 | **Security/abuse** | honeypot/consent/origin + **mandatory rate limit** + shrink public response + no match leak |
| 12 | **Tests needed** | disabled/validation/exact/weak/no-match/tenant/source/UTM/response/rate-limit |
| 13 | **Rollback** | `PUBLIC_LEADS_ENABLED=false` (+ optional code revert) |
| 14 | **Risks** | spam flood, wrong exact link, Origin bypass, response UUID leak |
| 15 | **Recommended slices** | E5-A match → E5-B rate-limit/harden → E5-C env wire → E5-D enable smoke |
