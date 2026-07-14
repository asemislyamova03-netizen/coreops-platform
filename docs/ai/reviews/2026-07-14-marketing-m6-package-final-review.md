# Marketing M6 Package — Final Review (A → B1 → B2 → B3)

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Mode:** READ-ONLY REVIEW  
**Branch:** `feature/marketing-m6-package`  
**HEAD:** `590ecab` — `marketing: add cabinet m6 documentation`

**Constraints honored:** no stage, no commit, no push, no migrations run, no env/prod/server changes, dirty tree not cleaned.

---

## Verdict

**PASS WITH NOTES**

The committed package `21d16e8^..590ecab` is a coherent, allow-list-isolated Marketing M6 + schema catch-up chain. No Booking/Branch **application** code, no CRM CSS additions, and no consulting code appear in the committed range. Shared wiring hunks are Marketing-only.

Notes below are non-blocking for package integrity; they constrain **deploy/ops** and **local dirty-tree** handling.

---

## 1. Repository state (review boundary)

| Item | Value |
|------|--------|
| Branch | `feature/marketing-m6-package` |
| HEAD | `590ecab85d501093f49e18556c81eaf81673ee16` |
| Staged index | empty |
| Dirty tree | large (~287 porcelain lines) — **out of package scope** |
| Review basis | **commit range only**: `21d16e8^..590ecab` (= `6c3b617..590ecab`) |

### Committed package vs dirty tree

| Layer | In commits A–B3? | Local dirty tree? |
|-------|------------------|-------------------|
| Migrations 0012 history / 0013 / 0014 / 0015 | Yes | N/A (committed) |
| `backend/app/modules/marketing/**` | Yes | Clean vs HEAD for marketing |
| Marketing console FE | Yes | Clean vs HEAD for marketing pages |
| Marketing docs A1b+B gates | Yes | Extra Gate A2 reports still `??` |
| Branch ORM import / Booking seed / CRM CSS / CRM FE | **No** | **Yes** (uncommitted) |

Review contents below **exclude** uncommitted local changes from package composition claims.

---

## 2. Commit chain

| Hash | Subject | Files | Stat | Purpose | Unexpected / mixed? |
|------|---------|-------|------|---------|---------------------|
| `21d16e8` | schema: add production catch-up migrations 0013-0014 | 10 | +2879 | Package A: schema catch-up migrations + packaging/catch-up docs | Includes optional **0012 Booking schema history** file (expected Package A history helper, not Booking app) |
| `b4ac0a3` | marketing: add cabinet backend mvp | 25 | +4174 | Package B1: Marketing BE + 0015 + tests + marketing wiring | Shared: router / models / seed — marketing-only hunks |
| `9ed763c` | marketing: add cabinet console fe1-fe3 | 23 | +2567 | Package B2: Marketing FE1–FE3 + marketing CSS | `index.css` +123 marketing only |
| `590ecab` | marketing: add cabinet m6 documentation | 20 | +9204 | Package B3: Marketing docs/reports | Docs-only |

Linear parents verified: `590ecab` → `9ed763c` → `b4ac0a3` → `21d16e8` → `6c3b617`.

---

## 3. Aggregate committed diff (`21d16e8^..590ecab`)

```text
78 files changed, 18824 insertions(+)
```

### Path groups

#### 1) Migrations / schema (4)

- `backend/alembic/versions/20250702_0012_phase12_booking_e1.py` (history)
- `backend/alembic/versions/20260708_0013_c1c_payment_direction.py`
- `backend/alembic/versions/20260709_0014_core_branches_baseline.py`
- `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py`

#### 2) Marketing backend (21)

- `backend/app/modules/marketing/**` (16)
- `backend/tests/test_marketing_*.py` (5)

#### 3) Marketing frontend (18 new + shared below)

- `platform-console/src/api/marketing.ts`
- `platform-console/src/types/marketing.ts`
- `platform-console/src/pages/workspace/marketing/**` (16)

#### 4) Marketing / package documentation (27)

- Product TZ, M1–M5 drafts/plans, M6 BE/FE reports, FE3, smokes, readiness, A1/A1b, B-prep/B1/B2, margosya audit, handoff, catch-up audits, 0014 plan

#### 5) Shared integration files (8 modified)

- `backend/app/api/v1/router.py` (+marketing router)
- `backend/app/modules/models.py` (+marketing ORM imports only)
- `backend/app/modules/module_registry/seed.py` (+marketing module def only)
- `platform-console/src/routes.tsx`
- `platform-console/src/components/layout/WorkspaceSidebar.tsx`
- `platform-console/src/i18n/ruUi.ts`
- `platform-console/src/workspace/moduleErrors.ts`
- `platform-console/src/index.css` (+123 `.marketing-*` only)

---

## 4. Crossover review

### Path scan (committed names)

Hits that look like “other domains” but are **expected Package A / docs**:

| Path | Assessment |
|------|------------|
| `...0012_phase12_booking_e1.py` | Schema history for stamp continuity — **not** Booking module/routes/services |
| `...0014_core_branches_baseline.py` | Schema catch-up (`branches` table / `tenants.default_branch_id`) — **not** Branch app package |
| `...0014-branches-baseline-plan.md` | Docs for 0014 |
| `...crm-ready-marketing-cabinet-next-handoff.md` | Marketing transition handoff (A1b allow-list) |

**Absent from committed tree:** `backend/app/modules/booking/**`, `backend/app/modules/branches/**`, consulting adapters, CRM page components, landing.

### Shared-file content (HEAD)

| File | Committed delta | Crossover? |
|------|-----------------|------------|
| `router.py` | import + `include_router(marketing_router)` | No booking/CRM |
| `models.py` | marketing model imports only | No `Branch` |
| `module_registry/seed.py` | `marketing` MODULE_DEFINITIONS entry only | No `booking` |
| `routes.tsx` | marketing page imports + 4 routes | Marketing-only |
| `WorkspaceSidebar.tsx` | one nav item | Marketing-only |
| `ruUi.ts` | marketing labels | Marketing-only |
| `moduleErrors.ts` | marketing disabled message | Marketing-only |
| `index.css` | +123 lines `.marketing-*`; **`.crm-` count unchanged** vs parent (`11` → `11`) | No CRM CSS added |

### Migration graph (read-only, no upgrade)

At HEAD: **single head** `0015_marketing_cabinet_mvp`.

Packaging segment:

```text
0015_marketing_cabinet_mvp ← 0014_core_branches_baseline
0014_core_branches_baseline ← 0013_c1c_payment_direction
0013_c1c_payment_direction ← 0012_booking_e1
0012_booking_e1 ← 0011_phase11
```

**LINEAR: PASS.** All four revisions have `downgrade`. 0014 includes backfill for default branches; 0015 creates Marketing tables only.

---

## 5. Functional consistency

| Check | Result |
|-------|--------|
| Marketing imports of booking/branches | None |
| APIRouter prefix `/marketing` vs FE `/marketing/...` paths | Aligned |
| Console routes `marketing`, `topics`, `packs`, `:packId` | Aligned with pages |
| Status/channel enums BE ↔ FE types | Aligned (topic/pack/preflight/approval/publish/channel) |
| Module registry seed `marketing` | Present at HEAD |
| Models registration for Marketing ORM | Present at HEAD |
| Broken imports / missing exports in committed marketing module | None found in static scan |
| Dependency on uncommitted CRM CSS for Marketing UI | **No** — marketing CSS is committed; leftover CRM CSS is dirty-only |
| Dependency on uncommitted Branch/Booking for Marketing runtime | **No** for Marketing app code; schema 0013/0014 are Alembic SQL |

### Dirty-tree independence assessment

**Committed Marketing package can build and operate without local dirty-tree hunks**, with caveats:

1. **Marketing FE/BE:** self-contained at HEAD; `npm run build` and marketing tests green under current environment.  
2. **CRM CSS leftover (`M index.css`, +431 CRM-ish lines unstaged):** not required for Marketing styles; local WT ≠ clean checkout cosmetics for CRM only.  
3. **Branch import / Booking seed (unstaged):** not in HEAD; Marketing does not import them. SAWarnings about `branches`↔`tenants` in pytest teardown come from **dirty** Branch registration, not from committed package.  
4. **0013/0014 app companions (finance direction models, Branch ORM, tenants service):** intentionally **not** in this package. Schema is shippable for catch-up; old app code remains compatible for Marketing focus (per prior Gate A posture).  
5. **0012 history file:** applying from stamp `0011` would create Booking **tables** via Alembic; that is schema chain reality, not inclusion of Booking product module.

---

## 6. Validation results (no DB upgrade)

| Check | Result |
|-------|--------|
| `python -m pytest backend/tests/test_marketing_*.py -q` | **54 passed** (~47s); SAWarning branches↔tenants from dirty Branch model |
| `npx tsx .../marketingLabels.test.ts` | ok |
| `npx tsx .../marketingNextAction.test.ts` | ok |
| `npm run build` (platform-console) | **PASS** (`tsc && vite build`) |
| `git diff --check 21d16e8^..590ecab` | Docs trailing whitespace only (non-blocking) |
| Alembic graph walk | Linear; head = 0015; no missing revision in packaging segment |
| Real `alembic upgrade` | **Not run** (forbidden) |

---

## 7. Findings

### Blocking

**None.**

### Non-blocking notes

1. Package A includes **0012 Booking schema history** + **0014 branches schema** by design — do not confuse with Booking/Branch **implementation** packages.  
2. Markdown trailing whitespace in several docs triggers `diff --check` noise.  
3. Working tree remains large and dangerous for broad `git add` — keep Marketing branch ops allow-list-only.  
4. Gate A2 packaging reports remain local (`??`) — out of B3 on purpose.  
5. Production still needs separate HQ gates for catch-up migrate + Marketing enable/deploy; this review does **not** approve push/deploy.  
6. Pytest SAWarning is dirty-tree artifact; clean checkout of HEAD should not register Branch unless separately added.

---

## 8. Recommendation

1. Treat `feature/marketing-m6-package` @ `590ecab` as **ready for HQ chain review / PR consideration**.  
2. **Do not push / deploy / migrate** without a new explicit HQ approval.  
3. Next safe step: HQ decision on push → PR → then separate production catch-up plan (`0012→0014`) before Marketing `0015`/module enable.  
4. Keep dirty CRM CSS / Booking / Branch / consulting work on separate packaging lines.

---

## HQ summary block

| Field | Value |
|-------|--------|
| Status | **PASS WITH NOTES** |
| Reviewed range | `21d16e8^..590ecab` |
| Commit chain | A `21d16e8` → B1 `b4ac0a3` → B2 `9ed763c` → B3 `590ecab` |
| Aggregate | 78 files, +18824 |
| Backend tests | 54 passed |
| Frontend build | PASS |
| Migration graph | Linear; `0012→0013→0014→0015`; head 0015 |
| Crossover | Clean for app code; expected schema/docs only for booking/branches/crm-named handoff |
| Dirty-tree independence | Marketing committed package independent of leftover CRM CSS / Branch / Booking hunks |
| Blocking | None |
| Non-blocking | 0012/0014 schema in Package A; doc whitespace; dirty tree risk; no deploy approval |
| This report | created **unstaged** |

**Explicit:** no push · no deploy · no migrations · no env · no prod.
