# Marketing M7-B — Package Review (pre-commit)

**Date:** 2026-07-14  
**Mode:** Review + staging plan only  
**Branch:** `feature/marketing-m6-package`  
**HEAD:** `33e4a8b` (`marketing: add topic taxonomy metadata`)  
**HQ:** no commit / push / deploy / migrations / staging yet

---

## Verdict

**READY TO STAGE (allow-list only)** after HQ approval to stage+commit.

Local M7-B code is GREEN. Scope matches pack-detail topic context + soft completeness. Dirty tree is large (~340 paths) — **must not** use `git add .`.

---

## 1. Dirty tree summary

| Item | Value |
|------|--------|
| Branch tracking | `feature/marketing-m6-package...origin/feature/marketing-m6-package` |
| Staged | empty |
| Dirty paths (approx) | ~340 (CRM, inbound, booking, consulting import, landing, publish scripts, `.ai_local`, etc.) |
| Alembic dirty | none |
| `.env` / secrets in M7-B allow-list | none |

Unrelated WIP must stay unstaged.

---

## 2. M7-B files confirmed

### Backend (modified)

| Path | Role |
|------|------|
| `backend/app/modules/marketing/schemas.py` | Expand `TopicSummaryInPack` (+ editorial fields) |
| `backend/app/modules/marketing/service/packs.py` | `_topic_summary()` via `extract_editorial_fields` |
| `backend/tests/test_marketing_packs.py` | Rich / thin / no-topic cases (+79 lines) |

### Frontend (modified + new)

| Path | Role |
|------|------|
| `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx` | Context / brief / completeness panels |
| `platform-console/src/pages/workspace/marketing/marketingPackContext.ts` | **NEW** helpers |
| `platform-console/src/pages/workspace/marketing/marketingPackContext.test.ts` | **NEW** FE unit |
| `platform-console/src/types/marketing.ts` | Types for nested topic fields |
| `platform-console/src/index.css` | +55 lines, `.marketing-pack-*` only |

### Docs

| Path | Status |
|------|--------|
| `docs/ai/reports/2026-07-14-marketing-m7-b-pack-context-report.md` | untracked — include |
| `docs/ai/plans/2026-07-14-marketing-m7-b-pack-context-plan.md` | untracked — include |
| `docs/ai/plans/2026-07-14-marketing-m7-b-implementation-plan.md` | untracked — include |
| `docs/ai/reports/2026-07-14-marketing-m7-b-planning-report.md` | untracked — include |
| `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md` | modified (+3 status lines) — include |
| `docs/ai/reports/2026-07-14-marketing-m7-b-package-review-report.md` | this file — include when staging |

### Extra M7-B files?

None beyond the expected allow-list + this package-review report.  
`docs/ai/plans/2026-07-14-marketing-m7-product-plan.md` exists untracked but was **not** part of the code step allow-list in HQ brief — **exclude** unless HQ explicitly wants product plan in the same commit.

---

## 3. Scope review

| Check | Result |
|-------|--------|
| Alembic / migration | **PASS** — no alembic dirty |
| production/server scripts | **PASS** — not in allow-list |
| env/secrets | **PASS** |
| dist / node_modules | **PASS** (build artifacts local only; not staged) |
| public inbound / landing | **PASS** — dirty but excluded |
| CRM logic | **PASS** — dirty CRM FE/BE excluded |
| Booking / Clinic / Trailers / currency | **PASS** — excluded |
| publish / export | **PASS** — `scripts/content/publish_*` dirty but excluded; Pack Detail publish UI unchanged in behavior |
| Margosya | **PASS** — no mentions in M7-B diffs |
| M7-C preflight enforcement | **PASS** — UI note only: completeness does not block preflight/approval |
| `index.css` accidental CRM hunks | **PASS** — append-only `.marketing-pack-*` (+55) |

### Special checks

**MarketingPackDetailPage.tsx**
- Adds topic context / writing brief / soft completeness before tabs.
- Diff does not alter approve/preflight/publish handlers.
- Completeness labeled display-only (M7-C deferral noted in UI).

**Backend**
- Additive nested `TopicSummaryInPack` fields only.
- Uses existing `extract_editorial_fields` (M7-A).
- Thin/missing metadata still maps; packs without topic remain valid (`test_marketing_packs` covers cases).

**CSS**
- Selectors all prefix `marketing-pack-`.
- No shared CRM class edits.

---

## 4. Validation re-run (this review)

### Backend

```bash
python -m pytest backend/tests/test_marketing_packs.py backend/tests/test_marketing_topics.py -q
```

**Result:** `33 passed` (~67s). Warnings: known SQLite FK cycle DROP (conftest) — not M7-B regressions.

### Frontend helpers

```bash
cd platform-console
npx tsx src/pages/workspace/marketing/marketingPackContext.test.ts
npx tsx src/pages/workspace/marketing/marketingTaxonomy.test.ts
npx tsx src/pages/workspace/marketing/marketingLabels.test.ts
```

**Result:** all `ok`.

### Build

```bash
cd platform-console
VITE_API_BASE_URL=https://flexity.asia/api/v1 npm run build
```

**Result:** exit 0  
Artifacts: `index-ELLYr9Ww.js` (379.00 kB), `index-CayYvMi5.css` (13.60 kB).

---

## 5. Proposed staging allow-list (do not stage until HQ asks)

```text
backend/app/modules/marketing/schemas.py
backend/app/modules/marketing/service/packs.py
backend/tests/test_marketing_packs.py
platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx
platform-console/src/pages/workspace/marketing/marketingPackContext.ts
platform-console/src/pages/workspace/marketing/marketingPackContext.test.ts
platform-console/src/types/marketing.ts
platform-console/src/index.css
docs/ai/reports/2026-07-14-marketing-m7-b-pack-context-report.md
docs/ai/plans/2026-07-14-marketing-m7-b-pack-context-plan.md
docs/ai/plans/2026-07-14-marketing-m7-b-implementation-plan.md
docs/ai/reports/2026-07-14-marketing-m7-b-planning-report.md
docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md
docs/ai/reports/2026-07-14-marketing-m7-b-package-review-report.md
```

**Staging commands (future only):**

```bash
git add -- \
  backend/app/modules/marketing/schemas.py \
  backend/app/modules/marketing/service/packs.py \
  backend/tests/test_marketing_packs.py \
  platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx \
  platform-console/src/pages/workspace/marketing/marketingPackContext.ts \
  platform-console/src/pages/workspace/marketing/marketingPackContext.test.ts \
  platform-console/src/types/marketing.ts \
  platform-console/src/index.css \
  docs/ai/reports/2026-07-14-marketing-m7-b-pack-context-report.md \
  docs/ai/plans/2026-07-14-marketing-m7-b-pack-context-plan.md \
  docs/ai/plans/2026-07-14-marketing-m7-b-implementation-plan.md \
  docs/ai/reports/2026-07-14-marketing-m7-b-planning-report.md \
  docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md \
  docs/ai/reports/2026-07-14-marketing-m7-b-package-review-report.md

git status --short
# verify only the 14 paths above are staged
```

**Proposed commit message:**

```text
marketing: show topic context in pack detail
```

---

## 6. Explicitly excluded (examples)

- All CRM / parties / workflows / public_leads dirty
- Booking / branches / imports_dry_run
- Landing / Instagram publish scripts
- `.ai_local/`, credentials, worktrees, alembic (none dirty anyway)
- `docs/ai/plans/2026-07-14-marketing-m7-product-plan.md` (untracked, out of M7-B code allow-list unless HQ adds it)
- `platform-console/dist/**` (never commit)

---

## 7. Risks

1. **Dirty tree contamination** if broad `git add` — high operational risk, mitigated by allow-list.
2. **Shared `index.css`** — M7-B hunk is clean now; re-check `git diff --cached -- index.css` before commit if other CSS land later.
3. **API additive fields** — old thin topics/packs still work; clients ignoring new fields unchanged.

---

## 8. Recommendation

**Approve allow-list stage + commit** when HQ requests.  
Do **not** push/deploy in the same step without separate approval.

**Next safe step:** HQ says «stage + commit M7-B allow-list» → commit with message above → then separate push/PR package.

---

## Finish checklist

| Item | Value |
|------|--------|
| Files changed in this review | this report only |
| Code changes | none (review-only) |
| Tests | 33 pytest; 3 FE helpers; build OK |
| Migration | none |
| Publish/Margosya | none in scope |
| Handoff needed | optional after commit |
