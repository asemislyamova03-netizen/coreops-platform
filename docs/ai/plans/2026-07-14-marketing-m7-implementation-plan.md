# Implementation Plan: Marketing M7 — usable content cabinet

**Date:** 2026-07-14
**Project:** Flexity / `coreops-platform`
**Category:** documentation_only until approved; future code = `universal_module` (marketing)
**Status:** waiting for approval
**Product plan:** `docs/ai/plans/2026-07-14-marketing-m7-product-plan.md`

---

## Goal

Сделать Marketing Cabinet полезным для реального контент-процесса Асем: rich topic metadata, pack context, preflight v2 — **без** publish/Margosya/миграции (если JSON хватает).

---

## Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | universal_module (marketing) — planning now |
| Risk | medium (after approval: FE+BE product changes) |
| Intended scope | marketing module + console marketing pages |
| Forbidden | publish, Margosya, CRM/inbound, booking, migrations unless separate gate |

---

## Scope

### Recommended start gate

**M7-A** only after explicit HQ approval for code.

### Files likely to modify (future gates)

| Area | Paths |
|------|--------|
| Backend schemas | `backend/app/modules/marketing/schemas.py` |
| Backend services | `topics.py`, `approval.py` (preflight), maybe `packs.py` |
| Backend tests | `backend/tests/test_marketing_*.py` |
| FE types/API | `platform-console/src/types/marketing.ts`, `api/marketing.ts` |
| FE topics | `MarketingTopicsPage.tsx` (+ helpers) |
| FE pack detail | `MarketingPackDetailPage.tsx`, tabs (preflight/approval), `marketingNextAction.ts` |
| Labels | `marketingLabels.ts` |

### Files not to touch

- publish/export routes (none live — keep disabled)
- public inbound / landing
- CRM workflows beyond reading
- alembic versions (unless M7-Migration gate approved)
- Margosya / bots
- billing / tenants enablement for other orgs

---

## M7 gates (order)

### M7-A — Content taxonomy / topic metadata

**Status: DONE (local, 2026-07-14)** — see `docs/ai/reports/2026-07-14-marketing-m7-a-taxonomy-metadata-report.md`.
Not committed / not deployed until separate HQ approval.

**Migration:** prefer **none**. Store editorial fields in `metadata_json`:

```json
{
  "audience": "...",
  "pain": "...",
  "insight": "...",
  "source_ref": "...",
  "cta": "...",
  "funnel_stage": "trust",
  "notes": "..."
}
```

First-class already: `title`, `rubric`, `angle`, `priority`, `status`, `recommended_channels`.

**Backend:**
- Document metadata contract (constants / TypedDict / Pydantic nested optional).
- `TopicCreate` / `TopicUpdate` accept nested `metadata_json` or typed optional fields that merge into JSON.
- Soft rubric allow-list helper (warn, don’t hard-fail unknown).
- List filters: rubric / status / priority (query params if missing).

**Frontend:**
- Topic create/edit form: rubric select, angle, audience, pain, insight, source_ref, CTA, funnel, priority, notes.
- Topics table filters.
- Rubric label map (RU).

**Tests:**
- API: metadata round-trip on create/patch.
- Helper: rubric labels / funnel codes.
- Do not require migration tests if no migration.

**Risks:** metadata key typos — centralize keys. Collision with M6 `source` vs `source_ref` — document clearly.

**Rollback:** revert FE/BE files; JSON fields remain harmless.

---

### M7-B — Pack detail context blocks

**Status: DONE (local, 2026-07-14)** — see `docs/ai/reports/2026-07-14-marketing-m7-b-pack-context-report.md`.  
Not committed / not deployed until separate HQ approval.

**No migration.**

**Frontend:**
- Topic context panel on pack detail (from `pack.topic` + fetch topic if metadata needed).
- Channel completeness indicator.
- Show CTA / insight / source_ref from topic.
- Extend `resolveMarketingNextAction` with “complete topic context” if thin.

**Backend (minimal):**
- Ensure pack detail response includes enough topic fields / metadata (may already via nested topic — expand if needed).

**Tests:**
- next-action unit tests for new ids.
- Pack detail render helpers if extracted.

---

### M7-C — Preflight v2

**Status: M7-C1 DONE (local backend, 2026-07-14)** — see `docs/ai/reports/2026-07-14-marketing-m7-c1-backend-preflight-report.md`.  
M7-C2 FE + deploy still pending HQ approval.

**No migration** (`preflight_report_json` already exists).

**Backend (`approval.py`):**
- New checks for topic metadata (insight, source_ref, cta, audience/pain).
- Media missing → warning.
- Generic/short text → soft warning.
- Keep M6 blockers (empty all texts, unapproved topic).
- Policy: warnings do not set FAILED; errors do.

**Frontend:**
- Preflight tab: group errors vs warnings.
- Approval tab: show “warnings accepted / blockers present”.
- Keep publish disabled.

**Tests:**
- pytest cases for warning vs blocker matrix.
- FE display helpers.

---

### M7-D — Real content seed / operating setup

**Not auto seed in production.** Docs + optional API script later.

- List of first **10 real topics** (titles + rubrics) for Асем to enter via UI after M7-A.
- Optional: rename/archive smoke topic — **separate approval**.
- SOP short: create → fill → approve topic → take → texts → preflight → approve pack.

**No prod DB writes in planning.** Execution of seed = later HQ gate.

---

### M7-E — Closeout & smoke

- Local pytest + FE unit tests green.
- Local/console smoke checklist.
- Production deploy smoke plan (separate execution approval): create 1 real-style topic end-to-end, leave publish disabled.
- Update closeout / SESSION if required.

---

## Steps (high level after approval)

1. Approve product plan + this implementation plan.
2. Implement **M7-A** only.
3. QA / review / small PR.
4. Then M7-B → M7-C.
5. M7-D content ops with Асем.
6. M7-E closeout.

---

## Tests / checks

| Gate | Checks |
|------|--------|
| A | `pytest` marketing topic metadata; FE form/helpers |
| B | next-action tests; pack context helpers |
| C | preflight warning/blocker cases |
| E | build; marketing smoke checklist |

Regression: CRM routes, public inbound — **read-only verify** after any console deploy (future).

---

## Risks

| Risk | Mitigation |
|------|------------|
| Metadata sprawl | Central key list |
| Over-strict preflight blocks Асем | Start warning-heavy |
| Accidental publish work | Explicit forbidden |
| Desire for migration | Separate gate only if JSON proven insufficient |
| Server git drift | Keep allow-list deploy discipline like M6 |

---

## Rollback

Per-gate: revert PR files.
JSON metadata left in DB is safe.
No schema downgrade needed if no migration.

---

## Approval

**Status:**

1. Product + implementation plans — approved.
2. **M7-A code** — implemented locally (report GREEN); commit/deploy still need separate approval.
3. Do not start publish/Margosya.

---

## Next step after M7-A

After commit/deploy decision for M7-A: start **M7-B** pack detail context blocks (no migration).
