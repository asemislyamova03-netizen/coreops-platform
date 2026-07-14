# Package Review — Marketing M7-C2 Frontend (pre-commit)

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Mode:** Review + staging plan **only** (no commit / push / deploy / stage)  
**Branch:** `feature/marketing-m6-package` (tracks `origin/feature/marketing-m6-package`)  
**HEAD (local tip noted):** still on prior marketing commits; M7-C1 is on `main` (`fcfa4a7`), local feature tip may lag merge — C2 package is FE-only on this branch.

---

## Status

**READY TO COMMIT** — after explicit HQ approval to stage + commit allow-list only.

Staged area: **empty** (`git diff --cached --name-only` → none). Safe to proceed with path-scoped `git add` when approved.

---

## 1. Dirty tree summary

Working tree has a **large unrelated WIP** (CRM, inbound, booking, landing, consulting import, scripts, secrets paths, etc.).

### M7-C2-relevant dirty / new

| Path | State |
|------|--------|
| `platform-console/src/types/marketing.ts` | modified |
| `platform-console/src/pages/workspace/marketing/marketingPreflight.ts` | **untracked** |
| `platform-console/src/pages/workspace/marketing/marketingPreflight.test.ts` | **untracked** |
| `…/packDetail/PackDetailPreflightTab.tsx` | modified |
| `…/packDetail/PackDetailApprovalTab.tsx` | modified |
| `…/MarketingPackDetailPage.tsx` | modified |
| `platform-console/src/index.css` | modified (**marketing-only** hunks verified) |
| `docs/ai/reports/2026-07-14-marketing-m7-c2-frontend-preflight-report.md` | untracked |
| `docs/ai/plans/2026-07-14-marketing-m7-c2-implementation-plan.md` | untracked |
| `docs/ai/plans/2026-07-14-marketing-m7-c2-preflight-ui-plan.md` | untracked |
| `docs/ai/reports/2026-07-14-marketing-m7-c2-planning-report.md` | untracked |
| `docs/ai/reports/2026-07-14-marketing-m7-c2-package-review-report.md` | this file (new) |

### Expected but **not** dirty

| Path | Note |
|------|------|
| `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md` | tracked, **unchanged** in WT — **exclude** from stage (no C2 checklist edit landed there) |

### Explicitly **excluded** (examples)

- All `backend/**` WIP  
- CRM/party/workflow console changes  
- `landing/**`  
- `scripts/content/publish_*`  
- `.ai_local/`, credentials, booking modules, alembic, env  
- `docs/ai/plans/2026-07-14-marketing-m7-product-plan.md` (unrelated product draft; not C2 package)  
- Other untracked reviews/handoffs  

---

## 2. M7-C2 files confirmed

Allow-list for future commit:

```text
platform-console/src/types/marketing.ts
platform-console/src/pages/workspace/marketing/marketingPreflight.ts
platform-console/src/pages/workspace/marketing/marketingPreflight.test.ts
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/PackDetailApprovalTab.tsx
platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx
platform-console/src/index.css
docs/ai/reports/2026-07-14-marketing-m7-c2-frontend-preflight-report.md
docs/ai/plans/2026-07-14-marketing-m7-c2-implementation-plan.md
docs/ai/plans/2026-07-14-marketing-m7-c2-preflight-ui-plan.md
docs/ai/reports/2026-07-14-marketing-m7-c2-planning-report.md
docs/ai/reports/2026-07-14-marketing-m7-c2-package-review-report.md
```

**Diff stats (marketing UX code, approx):**

- Preflight tab: ~+209 / −57  
- types: +45  
- Approval: +9 / −something small  
- Pack detail note: 1 line  
- Helper+tests: new files  
- CSS: +94 / −0, all marketing preflight selectors  

---

## 3. Scope violations

**None** in the proposed allow-list.

Verified absent from allow-list:

| Gate | Result |
|------|--------|
| backend | PASS |
| Alembic / migration | PASS |
| env / secrets | PASS |
| production/server scripts | PASS |
| dist / node_modules | PASS |
| public inbound / landing | PASS |
| CRM / Booking / Clinic / Trailers / currency | PASS |
| publish/export / Margosya | PASS |
| M7-D | PASS |

---

## 4. Frontend behavior review

| Check | Result |
|-------|--------|
| Blockers vs warnings visually separate | **PASS** — left borders red vs amber; separate titles |
| Warnings non-blocking copy | **PASS** — «Не блокируют утверждение» + banner |
| M6 report render | **PASS** — normalize uses `errors`/`checks` |
| M7-C1 v2 render | **PASS** — blockers/checklist/topic/channel/media |
| Unknown code fallback | **PASS** — `Неизвестная проверка: <code>` |
| aliases errors↔blockers, checks↔checklist | **PASS** (tests cover) |
| Missing report safe | **PASS** — tone `empty` |
| Approval gate unchanged | **PASS** — still `preflight_status === "passed"`; microcopy only |
| Publish disabled | **PASS** — `PackDetailPublishTab` untouched enablement |
| Preflight button preserved | **PASS** |
| API calls unchanged | **PASS** — still `runMarketingPreflight` |

**Non-blocking notes:**

1. Checklist fail vs warn heuristic uses exact code match to blocker list (soft fails often show as `!` warn — acceptable).  
2. Full v2 panels need joint C1+C2 deploy; until then UI degrades cleanly on M6.  
3. Parent M7 impl plan not updated in this package (optional follow-up doc-only).

---

## 5. CSS review

`platform-console/src/index.css` working-tree diff is **entirely** M7-C2 marketing preflight styles (`marketing-preflight-*`, blockers/warnings borders, check marks).  

**No CRM / booking / landing CSS** in this file’s current diff. Safe to `git add` the whole file for this commit.

---

## 6. Tests / build (re-run this review)

```text
npx tsx …/marketingPreflight.test.ts      → passed
npx tsx …/marketingPackContext.test.ts    → ok
npx tsx …/marketingTaxonomy.test.ts       → ok
npx tsx …/marketingLabels.test.ts         → ok
npm run build                             → GREEN
```

Local build artifacts (do **not** commit `dist/`):

- `index-CgVHM5HT.js` (or rebuild hash may match prior C2 report)
- `index-Cn_Q_hGN.css`

Backend pytest: **not required** (no backend files in package).

---

## 7. Staging plan (DO NOT RUN until HQ asks)

**Proposed commit message:**

```text
marketing: render preflight v2 results
```

**Proposed commands (path-scoped only):**

```bash
git add \
  platform-console/src/types/marketing.ts \
  platform-console/src/pages/workspace/marketing/marketingPreflight.ts \
  platform-console/src/pages/workspace/marketing/marketingPreflight.test.ts \
  platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx \
  platform-console/src/pages/workspace/marketing/packDetail/PackDetailApprovalTab.tsx \
  platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx \
  platform-console/src/index.css \
  docs/ai/reports/2026-07-14-marketing-m7-c2-frontend-preflight-report.md \
  docs/ai/plans/2026-07-14-marketing-m7-c2-implementation-plan.md \
  docs/ai/plans/2026-07-14-marketing-m7-c2-preflight-ui-plan.md \
  docs/ai/reports/2026-07-14-marketing-m7-c2-planning-report.md \
  docs/ai/reports/2026-07-14-marketing-m7-c2-package-review-report.md

git diff --cached --stat
git diff --cached --name-only
# verify only the 12 paths above
# then commit with message above
```

**Hard rules:** never `git add -A` / `git add .` on this dirty tree.

---

## 8. Backend / migration / publish

| Item | Value |
|------|--------|
| Backend in package | **no** |
| Migration | **no** |
| Publish/Margosya | **remain disabled** |
| Deploy | **not now**; later **joint C1+C2** |

---

## Recommendation

**APPROVE COMMIT** (allow-list only), when HQ says so.

Then: push + PR (separate approval) → merge → **joint C1+C2 deploy** planning (not auto).

---

## What was not touched in this review

- commit / push / staging  
- deploy / migrations / env / DB / production  
- code fixes  
- unrelated dirty WIP  
- M7-D  

---

## Next step

HQ: `APPROVED: commit M7-C2` → execute path-scoped stage + commit with message `marketing: render preflight v2 results`.
