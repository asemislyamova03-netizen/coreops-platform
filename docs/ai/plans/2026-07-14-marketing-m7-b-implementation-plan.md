# Implementation Plan — Marketing M7-B Pack context

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Category:** `universal_module` (marketing) — wait for HQ approval before code  
**Risk:** low–medium (API shape expand + FE only; no migration)  
**Source of truth commit baseline:** production already on `0c1dbe6` (M7-A)

**Related:**
- Product UX: `docs/ai/plans/2026-07-14-marketing-m7-b-pack-context-plan.md`
- Parent M7: `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md`
- Planning report: `docs/ai/reports/2026-07-14-marketing-m7-b-planning-report.md`

---

## Goal

Surface source-topic editorial context on Marketing pack detail so content writing has strategic brief without publish/Margosya.

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | universal_module (marketing) |
| Risk | low–medium |
| Migration | **none** |
| Forbidden | publish/export/Margosya, alembic, env, CRM/inbound/landing, smoke cleanup |

---

## Current state (verified read-only)

### Backend

- `GET /marketing/packs/{id}` → `PackDetailResponse`
- Nested `topic: TopicSummaryInPack | null` with **only**:
  `id`, `legacy_topic_id`, `title`, `rubric`, `status`
- Topic ORM already `selectinload`’ed; serialization truncates editorial fields
- Full editorial flatten exists on `TopicResponse` via `topic_metadata.extract_editorial_fields` (M7-A)
- `GET /marketing/topics/{id}` already returns full flattened topic

### Frontend

- `MarketingPackDetailPage.tsx` shows only `pack.topic?.title`
- Types mirror thin `MarketingTopicSummaryInPack`
- Helpers in `marketingTaxonomy.ts` (`extractTopicEditorial`, rubric/funnel/priority labels) reusable
- `resolveMarketingNextAction` does not consider topic metadata completeness
- No dedicated `getMarketingTopic` helper named as such (PATCH/archive/take exist; GET topic API exists and can be wrapped)

---

## Design decision

### Preferred: Option A — expand nested topic on pack responses (minimal BE)

Expand `TopicSummaryInPack` (or rename clarity later) to include:

- columns: `angle`, `priority` (+ keep existing summary fields)
- editorial flatten: `audience`, `pain`, `insight`, `source_ref`, `cta`, `funnel_stage`, `notes`, `planned_date`

Build via same helper as topics (`extract_editorial_fields`) in `packs._to_summary` (or dedicated mapper).

**Why preferred:**
- one round-trip on pack detail;
- topic already loaded;
- list endpoints get slightly richer topic too (acceptable; fields optional);
- no migration;
- FE simpler.

### Fallback: Option B — FE-only second fetch

Add `getMarketingTopic(topicId)` and `useQuery` when `pack.topic_id` set.

Valid if HQ wants FE-only first slice. Slightly more UI waterfalls; still no migration.

**Recommendation:** implement **Option A** in the same M7-B code gate unless HQ mandates FE-only.

Do **not** invent a separate `topic_context` bag unless expanding nested topic proves messy — prefer flat optional fields on nested topic.

---

## Gate split

### Recommended: **one** code gate **M7-B**

Scope fit in one PR if kept tight:

1. Backend expand nested topic serialization  
2. FE types + API (if needed)  
3. Pack detail: Topic context + Writing brief + soft completeness  
4. Optional next-action id for thin topic context  
5. Tests + build  

### Optional split (if PR too large)

| Gate | Scope |
|------|--------|
| **M7-B1** | Backend expand nested topic + FE Topic context panel (read-only) + link to topic |
| **M7-B2** | Writing brief + completeness chips + next-action soft hint |

Default HQ ask: **approve combined M7-B**.

---

## Exact files likely to change

### Backend

- `backend/app/modules/marketing/schemas.py` — expand `TopicSummaryInPack`
- `backend/app/modules/marketing/service/packs.py` — map editorial into nested topic
- `backend/tests/test_marketing_packs.py` — pack detail includes editorial; thin topic OK

Reuse (do not duplicate logic):

- `backend/app/modules/marketing/topic_metadata.py`

### Frontend

- `platform-console/src/types/marketing.ts`
- `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx`
- new small helper(s), e.g. `packTopicContext.ts` (+ `.test.ts`):
  - completeness scoring
  - writing brief derivation
  - empty labels
- optional: `marketingNextAction.ts` / `.test.ts`
- optional: `api/marketing.ts` only if FE-only fallback
- minimal CSS in `index.css` for context/brief panel (marketing-prefixed only)

### Docs (after code, separate)

- M7-B implementation / deploy reports when executed

---

## Forbidden files / zones

- alembic / migrations  
- publish tab / Margosya / export publishers  
- preflight enforcement logic in `approval.py` (M7-C)  
- Topics create form (M7-A already done)  
- CRM / inbound / landing / booking  

---

## Implementation steps (after approval)

1. Expand `TopicSummaryInPack` + pack service mapping from loaded topic + `extract_editorial_fields`.  
2. Update FE types.  
3. Add `packTopicContext` helpers (completeness + brief).  
4. Render Topic context + Writing brief + soft completeness on pack detail; link to topics.  
5. Optional soft next-action when context weak.  
6. Tests + `npm run build`.  
7. Stop for review → commit → PR → (later) deploy without migration.

---

## Tests

### Backend

- `GET /packs/{id}` nested topic includes editorial when present in `metadata_json`  
- Pack with topic but empty metadata → nested fields null / absent, **200**  
- Pack without topic → `topic=null`, **200**  
- Existing pack tests still pass (backward compatible)  
- Tenant isolation pattern if already present for packs  

### Frontend

- Helper tests: brief derivation, completeness levels, empty handling  
- Labels use existing taxonomy helpers where applicable  
- `npm run build` must pass  
- next-action tests if extended  

---

## Smoke plan (later execution; not now)

Prefer **minimal new rows**:

1. Prefer: **take** existing rich topic  
   `M7-A Metadata Smoke Topic`  
   id `a25333a3-ad1b-4539-956f-40298cfa5499`  
   into **one** pack (if not already taken).  
2. Open pack detail → verify context/brief filled from M7-A metadata.  
3. Optionally open thin M6 pack `996a4183-681e-44dd-841d-25e15beaa876` → empty/partial context UX OK.  
4. No publish. No multi-pack spam. No smoke cleanup unless separately approved.

---

## Deploy note (future)

- Backend file allow-list + console build/deploy  
- **No Alembic**  
- Alembic stays on `0015`  
- Backend + console should ship together so nested fields and UI match  

---

## Rollback

- Revert BE/FE PR files  
- Nested richer JSON is additive; old FE ignores unknown fields  
- No schema rollback  

---

## Risks

| Risk | Mitigation |
|------|------------|
| Pack list payloads slightly larger | optional fields; small JSON |
| Breaking clients expecting only 5 topic fields | additive optional fields only |
| Confusing pack.planned_date vs topic.planned_date | clear RU labels («дата пака» vs «план. дата темы») |
| Thin legacy topics | empty states + link to Topics |
| Scope creep into preflight | hard stop at display-only for M7-B |

---

## Approval

**Status:**

1. Product + implementation plans — approved.  
2. **M7-B code** — implemented locally (see `docs/ai/reports/2026-07-14-marketing-m7-b-pack-context-report.md`); commit/deploy need separate approval.  
3. Do not start M7-C / publish / Margosya without approval.

---

## Next step after M7-B

After commit/deploy of M7-B: start **M7-C** preflight v2 (display already soft-complete; enforce next).
