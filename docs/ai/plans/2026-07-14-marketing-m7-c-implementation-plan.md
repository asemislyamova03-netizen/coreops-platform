# Implementation Plan — Marketing M7-C Preflight v2

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Category:** `universal_module` (marketing) — wait for HQ approval before code  
**Risk:** medium (changes approval gate quality rules; no migration; keep approve semantics)  
**Baseline:** production M6+M7-A+M7-B live @ alembic **0015**

**Related:**
- Product: `docs/ai/plans/2026-07-14-marketing-m7-c-preflight-v2-plan.md`
- Parent M7: `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md`
- Planning report: `docs/ai/reports/2026-07-14-marketing-m7-c-planning-report.md`

---

## Goal

Extend Marketing pack preflight to validate strategic topic context + text/media quality signals, store an additive report v2 in existing `preflight_report_json`, improve Preflight tab UX — **without** publish/Margosya/migration.

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | universal_module (marketing) |
| Risk | medium |
| Migration | **none** |
| Forbidden | publish/export/Margosya, alembic, env, CRM/inbound/landing, smoke cleanup, DB schema |

---

## Current state (read-only verified)

### Backend

| Item | Location / behavior |
|------|---------------------|
| Engine | `backend/app/modules/marketing/service/approval.py` → `run_preflight` |
| Route | `POST /api/v1/marketing/packs/{pack_id}/preflight` |
| Schemas | `PreflightIssue`, `PreflightCheckItem`, `PreflightRequest`, `PreflightResponse` in `schemas.py` |
| Storage | `MarketingPublicationPack.preflight_report_json` (JSON), `preflight_status`, `preflight_at` |
| Status update | errors → `FAILED` + pack `preflight_failed`; else `PASSED` + `ready_for_approval` (overall `warning` if warnings) |
| Approve | requires `preflight_status == passed` (`MarketingPreflightNotPassedError`) |
| Topic metadata helper | `topic_metadata.extract_editorial_fields` (M7-A) — reuse |
| Nested topic on pack | M7-B `_topic_summary` already exposes editorial fields |

### Frontend

| Item | Location |
|------|----------|
| Preflight tab | `packDetail/PackDetailPreflightTab.tsx` — raw codes lists |
| Approval tab | `PackDetailApprovalTab.tsx` — `canApprove = preflight_status === "passed"` |
| Types | `types/marketing.ts` preflight types |
| Soft completeness | M7-B `marketingPackContext.ts` — **do not** couple as enforcement |

### Tests

- `backend/tests/test_marketing_preflight_approval.py` — empty fail / text pass / approve / cross-tenant

---

## Recommended gate split

| Gate | Scope | Why |
|------|-------|-----|
| **M7-C1** | Backend rules + schemas + tests | Highest risk; can ship/API-smoke alone |
| **M7-C2** | FE Preflight UX (RU labels, verdict, links) | Depends on C1 response shape |
| **M7-C3** | Prod deploy + smoke/closeout | Separate HQ as usual |

**Recommendation:** split **C1 → C2 → C3**.  
Do **not** merge C1+C2 into one PR unless C1 lands green and HQ wants a combined small package.

Alternative (if HQ prefers speed): one PR with BE+FE after C1 rules freeze — still one deploy. Default plan assumes **split**.

---

## Backend plan (M7-C1)

### Files likely to change

```text
backend/app/modules/marketing/service/approval.py
backend/app/modules/marketing/schemas.py
backend/tests/test_marketing_preflight_approval.py
```

Optional (preferred if `approval.py` grows):

```text
backend/app/modules/marketing/service/preflight_rules.py   # NEW pure helpers
backend/tests/test_marketing_preflight_v2.py               # NEW focused cases
```

**Do not change:** alembic, models columns, publish services, routes path (keep same endpoint), approval approve/reject semantics.

### Schema changes (additive)

Extend `PreflightResponse` / stored JSON with optional fields (defaults so old clients ignore):

| Field | Type | Notes |
|-------|------|-------|
| `version` | `"2"` | report version |
| `passed` | `bool` | `True` iff no blockers (same as today: no errors) |
| `blockers` | alias of `errors` **or** keep `errors` + document synonym | Prefer keep `errors` for compatibility; FE can label as «Blockers» |
| `topic_context_summary` | object \| null | key editorial presence snapshot |
| `channel_checks` | list/object | per-channel length / present |
| `media_checks` | object | count / issues summary |

Keep existing: `status`, `errors`, `warnings`, `checks`, `channel_eligibility`, pack/preflight/approval statuses.

### Rule implementation notes

1. Load topic + `extract_editorial_fields(topic.metadata_json)` when topic present.  
2. Apply M7-C blockers/warnings from product plan.  
3. Upgrade `topic_not_linked` → **error** `topic_missing` (document migration of code name; update tests that expected warning).  
4. Thresholds as constants near rules: `MIN_TEXT_BLOCKER=20`, `MIN_TEXT_WARN=40` for social channels.  
5. Insights: still optional (empty → warning only).  
6. Persist `version: "2"` inside `preflight_report_json`.  
7. Status transition logic **unchanged** (errors fail; else pass + ready_for_approval).

### Backward compatibility

- Old packs with minimal metadata: still produce valid report (more warnings/possible new blockers if no topic).  
- Packs **without topic** will now **fail** preflight (intentional product upgrade — mention in deploy notes).  
- Existing FE still works with `errors`/`warnings`/`checks` if C2 not deployed yet.

---

## Frontend plan (M7-C2)

### Files likely to change

```text
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx
platform-console/src/pages/workspace/marketing/marketingPreflightDisplay.ts   # NEW helpers
platform-console/src/pages/workspace/marketing/marketingPreflightDisplay.test.ts
platform-console/src/types/marketing.ts
platform-console/src/index.css   # only .marketing-preflight-* additions
```

Optional light touch:

```text
platform-console/src/pages/workspace/marketing/packDetail/PackDetailApprovalTab.tsx  # note if warnings present from last report (only if pack exposes report; otherwise skip)
platform-console/src/pages/workspace/marketing/marketingLabels.ts  # RU labels for codes
```

### UI behavior

- Verdict banner: «Нужно исправить» / «Можно утверждать» (+ warnings subline).  
- Separate Blockers vs Warnings with RU messages.  
- Checklist with human labels.  
- Quick links: Texts / Media / Topics list.  
- Do **not** change publish tab.  
- Do **not** require report.version for basic UX (fallback to v1 lists).

---

## Tests

### Backend

| Case | Expect |
|------|--------|
| Complete topic editorial + decent telegram text | `passed` or `warning`; `preflight_status=passed`; approve OK |
| No text | `failed`; `no_publishable_text` |
| No topic | `failed`; `topic_missing` |
| Topic approved but audience+pain+CTA empty | `failed`; `context_triple_missing` |
| Insight / source_ref missing, context otherwise ok | `warning`; still `passed` |
| Funnel=`diagnosis` + CTA empty | `warning` `cta_missing_for_funnel` |
| All texts &lt; 20 chars | `failed` `all_texts_too_short` |
| Warning-only pack | approve still 200 |
| Cross-tenant | 404 unchanged |
| No alembic / models untouched | compile + tests only |

### Frontend

| Case | Expect |
|------|--------|
| Helper: maps errors→blockers labels | ok |
| Helper: verdict from status/errors | ok |
| `npm run build` | pass |

---

## Smoke plan (M7-C3 / after deploy)

Tenant: `flexity-sales`.

| Entity | Id |
|--------|-----|
| Rich pack | `7ab244ef-0cd2-4da0-8f08-c8140aa39fbc` |
| Topic | `a25333a3-ad1b-4539-956f-40298cfa5499` |
| Thin pack (optional empty-state) | `996a4183-681e-44dd-841d-25e15beaa876` |

Steps:

1. Ensure pack has ≥1 non-empty channel text (edit existing if empty — prefer no new packs).  
2. `POST …/preflight` → expect `passed`/`warning`, report `version=2`, topic summary present.  
3. Approve still allowed after passed.  
4. Publish disabled.  
5. Health / CRM / inbound regression.  
6. **No** new rows unless required to fill text.

---

## Deploy notes (later)

- Backend allow-list: `approval.py`, `schemas.py`, (+ optional `preflight_rules.py`).  
- Console dist rebuild.  
- **No Alembic.**  
- Call out breaking intent: packs without topic now fail preflight.

---

## Rollback

- Restore backend files + restart.  
- Restore console dist.  
- No schema rollback.  
- Leave smoke packs/topics.

---

## Risks

1. Upgrading «no topic» to blocker may break old M6 packs without topics — intentional; document.  
2. Over-tuning length thresholds — start with 20/40; adjust in hotfix if Асем blocked unfairly.  
3. FE without C1 still works; C1 without C2 shows raw codes — acceptable briefly.  
4. Do not reuse M7-B soft completeness as hard gate.  
5. Server file-copy drift continues on deploy.

---

## Implementation steps (when HQ approves code)

1. Freeze product rules (this + product plan).  
2. **M7-C1** backend + tests.  
3. Package review → commit → PR → merge → deploy plan.  
4. **M7-C2** FE polish (same process).  
5. **M7-C3** smoke/closeout.  
6. Only then consider further content quality CR (not Margosya).

---

## Approval gate

Do **not** write production code until Асем / HQ explicitly approves **M7-C implementation** (preferably M7-C1 first).

---

## Checklist progress

| Item | Status |
|------|--------|
| Product + implementation plans | DONE |
| **M7-C1 backend** rules + schemas + tests | DONE (local, 2026-07-14) — not committed/deployed |
| M7-C2 FE Preflight UX | pending HQ |
| M7-C3 deploy/smoke | pending |
