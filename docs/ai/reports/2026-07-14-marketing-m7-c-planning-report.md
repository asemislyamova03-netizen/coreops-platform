# Planning Report — Marketing M7-C Preflight v2

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Status:** PLANNING COMPLETE — code not started  
**Category:** documentation_only

---

## Goal

Plan Preflight v2 so Marketing Cabinet checks strategic context + text quality before approval, without enabling publish/Margosya and without DB migration.

---

## Inputs / related docs

| Doc | Path |
|-----|------|
| Product plan | `docs/ai/plans/2026-07-14-marketing-m7-c-preflight-v2-plan.md` |
| Implementation plan | `docs/ai/plans/2026-07-14-marketing-m7-c-implementation-plan.md` |
| Parent M7 | `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md` |
| Live baseline | M6 + M7-A + M7-B; alembic **0015**; publish disabled |

Smoke references:
- pack `7ab244ef-0cd2-4da0-8f08-c8140aa39fbc`
- topic `a25333a3-ad1b-4539-956f-40298cfa5499`

---

## Current state summary (read-only)

Preflight lives in `MarketingApprovalService.run_preflight` (`approval.py`):

- Already returns `errors` / `warnings` / `checks` / `channel_eligibility`.
- Stores full report in **`preflight_report_json`** (+ `preflight_status`, `preflight_at`).
- On blockers → `preflight_failed`; else → `ready_for_approval` and `preflight_status=passed` even if warnings.
- Approve requires `preflight_status == passed` (warnings do not block).
- FE Preflight tab shows raw codes; Approval tab only checks `preflight_status`.
- M7-B soft completeness is **display-only** and must stay out of enforcement.

---

## Answers to required planning questions

### 1. Is migration needed?

**No.**  
`preflight_report_json` already exists. v2 is additive JSON + rule logic.

### 2. Recommended blocker / warning rules?

**Blockers (errors):**
- keep M6: no text, missing text rows, pack metadata incomplete, topic not approved (if linked), invalid media mime;
- **upgrade:** no linked topic → `topic_missing`;
- **new:** audience + pain + CTA **all** empty → `context_triple_missing`;
- **new:** all non-empty social texts &lt; 20 chars → `all_texts_too_short`.

**Warnings:**
- insight missing;
- source_ref missing;
- CTA missing for funnel ∈ diagnosis / consultation / product_education / objection_handling;
- no media metadata;
- channel text short (&lt; 40) on some socials;
- notes empty;
- topic planned_date missing;
- keep M6: telegram too long, empty insights, media not 1080×1080;
- optional: obvious placeholder text warning.

### 3. How strict should v2 be?

**Warning-heavy, blocker-light.**  
Approve must remain possible with warnings. Avoid single-field blockers except the carefully chosen set above.

### 4. Backend files likely to change?

```text
backend/app/modules/marketing/service/approval.py
backend/app/modules/marketing/schemas.py
backend/tests/test_marketing_preflight_approval.py
# optional:
backend/app/modules/marketing/service/preflight_rules.py
backend/tests/test_marketing_preflight_v2.py
```

### 5. Frontend files likely to change?

```text
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx
platform-console/src/pages/workspace/marketing/marketingPreflightDisplay.ts (+ .test.ts)
platform-console/src/types/marketing.ts
platform-console/src/index.css   # .marketing-preflight-* only
```

### 6. Tests required?

Yes — BE cases for pass/warn/block/approve-with-warnings/no-topic/triple-missing/short-text; FE helper + build. Existing preflight tests must be updated for `topic_missing` upgrade.

### 7. Recommended gate split?

**M7-C1** backend rules + tests → **M7-C2** FE display → **M7-C3** deploy/smoke.  
Default: keep split for safer review.

### 8. Smoke pack?

Primary: `7ab244ef-0cd2-4da0-8f08-c8140aa39fbc` (+ topic `a25333a3-…`).  
Optional thin: `996a4183-681e-44dd-841d-25e15beaa876`.  
Prefer edit texts on existing pack; avoid new rows.

### 9. Risks / blockers (planning)?

| Risk | Mitigation |
|------|------------|
| Packs without topic now fail | Document as intentional; Асем links topic first |
| Length thresholds too harsh | Start 20/40; tune after smoke |
| Coupling to soft completeness | Explicitly out of enforcement |
| C1 without C2 | Raw codes still usable |
| File-copy drift on deploy | Same allow-list pattern |

**Planning blockers:** none — ready for HQ code approval of C1.

### 10. Next recommended step?

HQ approve **M7-C1 implementation** (product + this plan) → code backend preflight v2 only → package review → commit/PR → (later) C2 / deploy.

---

## Approval behavior (locked for plans)

```text
blockers → fail preflight → cannot approve
warnings only → preflight_status=passed → can approve
publish remains disabled
```

---

## What was not touched (this planning task)

- production code / commit / push / deploy  
- migrations / env / DB writes  
- publish / Margosya / smoke cleanup  
- M7-C implementation  

---

## Next safe step

Wait for explicit HQ approval: **implement M7-C1 (backend Preflight v2)**.
