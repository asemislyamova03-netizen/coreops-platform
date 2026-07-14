# Marketing M7-A — Package review before commit

**Date:** 2026-07-14
**Branch:** `feature/marketing-m6-package` @ `8aa20b8`
**Task:** review + staging plan only
**Commit / push / deploy:** not performed

---

## Verdict

**READY for M7-A staging** (CSS blocker cleared 2026-07-14).

Backend + Marketing FE + docs for M7-A look in-scope and tests/build are GREEN.
`platform-console/src/index.css` now differs from HEAD by **+15 lines** of Marketing M7-A CSS only (CRM WIP removed from this file’s diff).

---

## Dirty tree summary

Working tree is **heavily dirty** with unrelated WIP (CRM, booking, imports, consulting, landing, credentials, etc.).

Tracked modifications alone span core, finance, parties, workflows, public_leads, CRM console, Instagram publish scripts, plus Marketing M7-A files.

Untracked noise includes `.ai_local/`, `.local-dev-credentials`, booking modules, CRM helpers, many docs reports.

**Do not** `git add .` or stage broadly.

---

## Path correction vs HQ brief

HQ brief listed frontend under `platform-console/src/features/marketing/`.

**Actual M7-A frontend paths** (no `features/marketing/` directory exists):

| Brief (incorrect) | Actual |
|-------------------|--------|
| `.../features/marketing/marketingTaxonomy.ts` | `platform-console/src/pages/workspace/marketing/marketingTaxonomy.ts` |
| `.../features/marketing/marketingTaxonomy.test.ts` | `platform-console/src/pages/workspace/marketing/marketingTaxonomy.test.ts` |
| `.../features/marketing/MarketingTopicsPage.tsx` | `platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx` |

---

## M7-A files confirmed

### Backend (clean scope)

| File | Status | Notes |
|------|--------|--------|
| `backend/app/modules/marketing/topic_metadata.py` | **untracked (new)** | editorial merge/extract helpers |
| `backend/app/modules/marketing/schemas.py` | modified | +26 editorial fields on create/update/response |
| `backend/app/modules/marketing/service/topics.py` | modified | map metadata; flatten on response |
| `backend/tests/test_marketing_topics.py` | modified | +144 rich metadata + isolation + legacy create |

### Frontend (mostly clean; CSS blocker)

| File | Status | Notes |
|------|--------|--------|
| `platform-console/src/pages/workspace/marketing/marketingTaxonomy.ts` | **untracked (new)** | rubrics/funnel/priority + payload builders |
| `platform-console/src/pages/workspace/marketing/marketingTaxonomy.test.ts` | **untracked (new)** | helper/payload tests |
| `platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx` | modified | create/edit form, filters, list context |
| `platform-console/src/types/marketing.ts` | modified | +26 optional editorial fields |
| `platform-console/src/index.css` | modified | **CLEAN for M7-A** — +15 marketing selectors only (CRM WIP stripped 2026-07-14) |

### Docs

| File | Status | Notes |
|------|--------|--------|
| `docs/ai/reports/2026-07-14-marketing-m7-a-taxonomy-metadata-report.md` | untracked | M7-A implementation report |
| `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md` | untracked | full M7 plan + M7-A DONE checklist |
| `docs/ai/reports/2026-07-14-marketing-m7-a-package-review-report.md` | this file | package review |

### Extra M7-related docs (exclude from this code commit unless HQ asks)

- `docs/ai/plans/2026-07-14-marketing-m7-product-plan.md`
- `docs/ai/reports/2026-07-14-marketing-m7-planning-report.md`

These belong to **M7 planning**, not M7-A code slice. Keep out of M7-A commit or ship as a separate docs commit.

---

## Scope check — forbidden zones

| Zone | Result |
|------|--------|
| Alembic / migrations | **Clean** — no dirty `backend/alembic/`; M7-A uses `metadata_json` only |
| Env / secrets | **Excluded** — `backend/.local-dev-credentials` present untracked; never stage |
| Publish / export / Margosya | **Clean** in M7-A diffs; unrelated dirty: `scripts/content/publish_instagram_live.py` — exclude |
| Public inbound / landing | **Unrelated dirty** — exclude |
| CRM logic | **Unrelated dirty** (many files) — exclude; **leaks into index.css** |
| Booking / Clinic / Trailers / currency | Unrelated dirty — exclude |
| Generated `dist/` / `node_modules` | Not staged; build artifacts local only |
| Production / server scripts | Not in M7-A allow-list |

### `index.css` — resolved (was contaminated)

Earlier full dirty diff: **+446 / −9** (CRM board density, list view, etc.).

**After cleanup (2026-07-14):** restored from HEAD + only:

```css
.marketing-form-span-2 { grid-column: span 2; }
@media (max-width: 720px) { .marketing-form-span-2 { grid-column: span 1; } }
.marketing-textarea { resize: vertical; min-height: 64px; }
```

Current M7-A `index.css` diff: **+15 / −0**. Safe to include in allow-list.

---

## Validation re-run (this review)

### Backend

```bash
python -m pytest backend/tests/test_marketing_topics.py backend/tests/test_marketing_packs.py -q
→ 30 passed, 30 warnings in 58.44s
```

### Frontend tests

```bash
npm test -- marketingTaxonomy marketingLabels --run
→ FAIL: Missing script "test" (no npm test in platform-console)

Fallback (project pattern):
npx tsx src/pages/workspace/marketing/marketingTaxonomy.test.ts → ok
npx tsx src/pages/workspace/marketing/marketingLabels.test.ts → ok
```

### Build

```bash
VITE_API_BASE_URL=https://flexity.asia/api/v1 npm run build
→ exit 0
  dist/assets/index-Bt3X7FOi.js
  dist/assets/index-DoMqef_m.css
```

**Migration:** none
**Publish/Margosya:** not touched in M7-A package

---

## Proposed staging allow-list (exact)

Stage **only** these paths after CSS cleanup:

```text
backend/app/modules/marketing/topic_metadata.py
backend/app/modules/marketing/schemas.py
backend/app/modules/marketing/service/topics.py
backend/tests/test_marketing_topics.py

platform-console/src/pages/workspace/marketing/marketingTaxonomy.ts
platform-console/src/pages/workspace/marketing/marketingTaxonomy.test.ts
platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx
platform-console/src/types/marketing.ts
platform-console/src/index.css   # M7-A marketing rules only (+15)

docs/ai/reports/2026-07-14-marketing-m7-a-taxonomy-metadata-report.md
docs/ai/reports/2026-07-14-marketing-m7-a-package-review-report.md
docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md
```

### Explicitly excluded (examples)

- All CRM / parties / workflows / public_leads / finance / booking / imports files
- `landing/**`
- `scripts/content/publish_*.py`
- `backend/.local-dev-credentials`
- `.ai_local/`, `.worktrees/`, `bash.exe.stackdump`
- M7 product plan + M7 planning report (unless separate docs commit)
- Current contaminated `index.css` as-is
- Any remaining CRM CSS WIP (must stay out of M7-A; re-apply later in a CRM commit if needed)

**This review did not stage any files.**

---

## Proposed commit message

```text
marketing: add topic taxonomy metadata
```

---

## Recommendation

1. ~~**Revise** `platform-console/src/index.css` to M7-A-only marketing rules.~~ **DONE 2026-07-14.**
2. HQ approve staging of the allow-list above.
3. Then (separate approval) commit locally — still no push/deploy unless asked.
4. After M7-A lands: proceed to **M7-B** pack context.

Optional: separate docs-only commit for M7 product plan + planning report.

---

## CSS cleanup follow-up (2026-07-14)

**Status after cleanup: READY for M7-A staging (CSS blocker cleared).**

### Action taken

1. Restored `platform-console/src/index.css` from `HEAD`.
2. Re-added only Marketing M7-A selectors after `.marketing-form-grid`:
   - `.marketing-form-span-2`
   - `@media` override for span-2
   - `.marketing-textarea`
3. Did not re-introduce CRM CSS into this file’s M7-A diff.

### Diff/stat after cleanup

```text
platform-console/src/index.css | 15 +++++++++++++++
1 file changed, 15 insertions(+)
```

CRM / Booking / landing selectors in `index.css` diff: **none**.

### Build after cleanup

```text
VITE_API_BASE_URL=https://flexity.asia/api/v1 npm run build → exit 0
  dist/assets/index-kjKDKGSb.js
  dist/assets/index-c0Afn_MP.css
```

### Note on CRM WIP CSS

Unrelated CRM CSS hunks were removed from the **working copy** of `index.css` (file returned toward HEAD + M7-A only). CRM component WIP elsewhere is unchanged; if local CRM UI needed those styles, they belong to a separate CRM commit later — not M7-A.

### Remaining blockers for commit

- None for CSS.
- Still need separate HQ approval to **stage + commit** the M7-A allow-list (not done in this step).

---

## What was not touched in this review task

- No commit, push, deploy
- No staging
- No migrations / env / DB / production
- No code fixes (CSS cleanup left for next approved step)
