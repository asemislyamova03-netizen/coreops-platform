# Gate B-prep — Package B staging report (Marketing M6)

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Gate:** B-prep — stage Package B allow-list  
**Commit:** **not performed**

**Parents:**
- `docs/ai/reports/2026-07-13-marketing-m6-gate-a1b-allowlist-package-plan.md`
- `docs/ai/reports/2026-07-13-marketing-m6-gate-a2-commit-a-report.md` (Commit A `21d16e8`)

---

## Status

**PASS — Package B staged for HQ review (66 files, no commit).**

- Branch: `feature/marketing-m6-package`
- HEAD: `21d16e8` (unchanged — staging only)
- Package A crossover: **none**
- Forbidden path scan: **clean**
- Backend marketing tests: **54 passed**
- Frontend helper tests + build: **PASS**

---

## 1. Pre-check

| Item | Value |
|------|--------|
| Branch | `feature/marketing-m6-package` |
| HEAD | `21d16e8` — Commit A |
| Working tree | still dirty outside index |

---

## 2. Package B files staged (66)

### Backend (22 paths)

| Area | Paths |
|------|-------|
| Migration 0015 | `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` |
| Marketing module | `backend/app/modules/marketing/**` (16 files) |
| Router wiring | `backend/app/api/v1/router.py` |
| ORM registry | `backend/app/modules/models.py` (marketing imports only) |
| Module seed | `backend/app/modules/module_registry/seed.py` (marketing entry only) |
| Tests | `backend/tests/test_marketing_*.py` (5 files) |

### Frontend (25 paths)

| Area | Paths |
|------|-------|
| API/types | `platform-console/src/api/marketing.ts`, `types/marketing.ts` |
| Pages/helpers | `platform-console/src/pages/workspace/marketing/**` (18 files) |
| Routes/nav/i18n | `routes.tsx`, `WorkspaceSidebar.tsx`, `ruUi.ts`, `moduleErrors.ts` |
| CSS | `platform-console/src/index.css` (marketing block only) |

### Docs (19 paths)

Product TZ + M1–M5 plans, M6 BE/FE reports, FE3 plan/report, local smoke reports, gate A2 prep/commit reports, marketing handoff.

**Not re-staged from Package A:** readiness / catch-up / A1 / A1b docs already in Commit A.

---

## 3. Mixed files — staging method

| File | Staged | Excluded (left unstaged) | Method |
|------|--------|--------------------------|--------|
| `backend/app/modules/models.py` | marketing ORM imports | `Branch` import (0014) | surgical temp edit → `git add` → restore WT |
| `backend/app/modules/module_registry/seed.py` | `marketing` module def | `booking` module def | surgical temp edit → `git add` → restore WT |
| `platform-console/src/index.css` | `.marketing-*` block (+123 lines) | CRM/kanban/list CSS (+431 lines approx) | HEAD + marketing append → `git add` → restore full WT |

**Not present / skipped:** `App.tsx`, `backend/app/api/router.py` (not in tree).

**Not staged (non-marketing):** `backend/app/modules/module_registry/service.py` (`booking` in enabled list only).

---

## 4. Mixed hunks excluded (summary)

```text
backend/app/modules/models.py          → Branch import (0014 companion)
backend/app/modules/module_registry/seed.py → booking module definition
platform-console/src/index.css       → CRM pipeline/list/match CSS (~62 hunk lines remain unstaged)
backend/app/modules/module_registry/service.py → booking enable line (whole file unstaged)
```

No blocker — hunks were separable without `git add -p` interactive session.

---

## 5. Any non-Package-B files staged?

**No application code outside Marketing scope.**

Notes:
- `docs/ai/handoffs/2026-07-13-crm-ready-marketing-cabinet-next-handoff.md` is **Marketing transition handoff** (included in A1b B3 list).
- Gate A2 prep/commit reports staged as packaging chain docs (not Package A migrations).

**Not staged:** CRM pages/components, Booking, consulting, landing, `.ai_local`, secrets, branches module code.

---

## 6. Package A crossover check

```bash
git diff --cached --name-only | grep -E '20260708_0013|20260709_0014|20250702_0012'
```

**Result:** empty — **NO_PKG_A_CROSSOVER**

---

## 7. Staged diff stat

```text
66 files changed, 15078 insertions(+)
```

Breakdown (approx):
- Backend code/tests/migration: ~4.5k lines
- Frontend code/CSS: ~2.9k lines
- Docs: ~8.6k lines

---

## 8. `git diff --cached --check`

- Exit: warnings (docs trailing whitespace)
- Migrations/code: no blocking issues observed
- Same class of doc whitespace as Package A gates

---

## 9. Forbidden path scan

```bash
git diff --cached --name-only | grep -E '(^\.ai_local|\.env|dist/|node_modules|landing/|booking|clinic|trailers|FLEXITY_BOOKING|FLEXITY_CLINIC|TRAILERS|credential|secret|\.pem|\.key)'
```

**Result:** `NO_FORBIDDEN`

(CRM CSS content excluded from staged `index.css`; booking seed block excluded.)

---

## 10. Validation (no migrations)

### Backend

```bash
python -m pytest backend/tests/test_marketing*.py -q
```

**Result:** `54 passed` in ~78s (SAWarning on test teardown FK cycle branches↔tenants — known test harness noise).

### Frontend

```bash
npx tsx src/pages/workspace/marketing/marketingLabels.test.ts      # ok
npx tsx src/pages/workspace/marketing/marketingNextAction.test.ts  # ok
npm run build                                                       # tsc + vite build ✅
```

No `npm run test` script in `platform-console/package.json` — used FE3 report commands.

**No alembic upgrade run.**

---

## 11. Report file

Created (this file):

`docs/ai/reports/2026-07-13-marketing-m6-gate-b-prep-package-b-staging-report.md`

**Not staged** (per HQ: create after staging, do not auto-add).

---

## 12. What was not touched

- no commit / no push
- no deploy / no env / no prod / no DB writes
- no Package A changes
- no migration execution
- no staging of CRM FE (`CrmPage`, kanban helpers, `LeadDetailModal`, etc.)
- no staging of Booking module / branches ORM / consulting / landing
- no `.ai_local` / credentials

---

## 13. Risks

1. **Split CSS state:** Marketing styles staged; CRM styles still local-only — console CRM UI may look incomplete until CRM package or combined CSS commit.
2. **Split seed/models:** Marketing module registered; Booking seed + Branch ORM import still unstaged — local dev may need full WT for booking/0014 app code.
3. **Large docs bundle:** 19 doc files in same staged set — HQ may prefer **B1 backend / B2 frontend / B3 docs** split at commit time.
4. **Doc whitespace** `--check` noise (cosmetic).

---

## 14. Next recommended step

HQ review `git diff --cached --name-only | sort` and decide commit strategy:

| Option | Scope |
|--------|--------|
| **One Commit B** | all 66 staged files |
| **Split B1** | backend + 0015 + tests + router/models/seed |
| **Split B2** | frontend + marketing CSS |
| **Split B3** | docs only |

**Still not deploy.** Production catch-up 0012→0014 remains separate gate before Marketing 0015 on server.

---

## HQ summary

1. **Status:** PASS — Package B staged, no commit  
2. **Branch/HEAD:** `feature/marketing-m6-package` @ `21d16e8`  
3. **Package B files staged:** 66  
4. **Mixed files staged:** `models.py`, `module_registry/seed.py`, `index.css` (marketing-only hunks)  
5. **Mixed hunks excluded:** Branch import; booking seed; CRM CSS; module_registry/service booking line  
6. **Non-Package-B app code staged:** none  
7. **Package A crossover:** none  
8. **Staged diff stat:** 66 files, +15078  
9. **diff --check:** docs trailing whitespace only  
10. **Forbidden path scan:** clean  
11. **Backend tests:** 54 passed  
12. **Frontend tests/build:** tsx helpers ok; `npm run build` ok  
13. **Report file:** created, unstaged  
14. **Not touched:** commit, deploy, migrations, env, prod, CRM/Booking code staging  
15. **Risks:** split CSS/seed; docs size; commit split decision  
16. **Next:** HQ review staged list → approve commit strategy (B monolith vs B1/B2/B3)  
