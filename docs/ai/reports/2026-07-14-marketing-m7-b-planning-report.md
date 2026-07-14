# Planning Report — Marketing M7-B Pack context

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Status:** PLANNING COMPLETE — code not started  
**Category:** documentation_only

---

## Documents created

| Doc | Path |
|-----|------|
| Product / UX | `docs/ai/plans/2026-07-14-marketing-m7-b-pack-context-plan.md` |
| Implementation | `docs/ai/plans/2026-07-14-marketing-m7-b-implementation-plan.md` |
| This report | `docs/ai/reports/2026-07-14-marketing-m7-b-planning-report.md` |

---

## Answers (required)

### 1. Is backend change needed?

**Preferred: yes, minimal** — expand nested `TopicSummaryInPack` on pack responses with angle/priority + M7-A editorial flatten (reuse `extract_editorial_fields`).

**Not strictly required** — FE could call existing `GET /topics/{id}`. Fallback if HQ wants FE-only B1.

Topic ORM is already eager-loaded on pack detail; today’s gap is **serialization**, not missing joins.

### 2. Is migration needed?

**No.** All fields already in topic columns / `metadata_json` (M7-A). Alembic remains `0015`.

### 3. What data is already available in pack detail?

| Available now | Missing for M7-B UX |
|---------------|---------------------|
| Pack statuses, texts, media, logs | Nested topic angle / priority |
| Nested topic: id, legacy_topic_id, title, rubric, status | audience, pain, insight, source_ref, cta, funnel_stage, notes, planned_date |
| Pack `planned_date` | Topic planned_date (editorial) |

Full data exists via topic GET after M7-A; pack detail does not expose it.

### 4. What UI blocks should be built?

1. **Topic context** panel (all editorial fields, RU labels, empty states, link to topic)  
2. **Writing brief** (display-only derived lines)  
3. **Soft completeness** indicators (display only; not M7-C enforcement)  
4. Preserve tabs + disabled publish  

### 5. Can M7-B be one small code gate?

**Yes — recommended combined M7-B.**

Optional split:

- **M7-B1** nested topic + context panel  
- **M7-B2** brief + completeness + next-action hint  

### 6. What tests are required?

- Backend: pack detail nested editorial; empty metadata OK; no-topic OK; existing packs tests green  
- Frontend: brief/completeness helpers; next-action if touched; `npm run build`  

### 7. Which smoke data should be used?

| Preference | Asset |
|------------|--------|
| Primary | Take / open pack for **M7-A Metadata Smoke Topic** `a25333a3-ad1b-4539-956f-40298cfa5499` (rich metadata) |
| Secondary | Existing M6 pack `996a4183-681e-44dd-841d-25e15beaa876` for thin/empty UX |
| Avoid | many new topics/packs; publish; smoke cleanup without approval |

### 8. Risks / blockers?

| Item | Level | Notes |
|------|-------|--------|
| Blockers | **None** for planning | M7-A live |
| Additive API fields | low | old clients ignore |
| Pack list payload size | low | optional fields |
| Date label confusion | low | pack vs topic planned_date |
| Preflight scope creep | process | keep M7-B display-only |

### 9. Recommended next gate

**HQ approve M7-B plans → implement combined M7-B code (Option A + UI) → tests → review → commit/PR → deploy without migration.**

Then M7-C preflight v2.

---

## What was not touched

- Production / server / DB / migrations / env  
- Code / commit / push / deploy  
- Publish / Margosya  
- Smoke cleanup  
- M7-C/D/E implementation  

---

## Next recommended step

Асем / HQ explicit approval of M7-B product + implementation plans, then code gate **M7-B** (no migration).
