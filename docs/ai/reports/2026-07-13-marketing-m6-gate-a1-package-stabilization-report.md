# Gate A1 — Marketing M6 package stabilization report

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Branch:** `main` @ `6c3b617`  
**Category:** documentation_only / git package audit  
**HQ:** stabilize package — **no commit, no deploy, no migrations, no env, no production**

**Parents:**
- `docs/ai/reports/2026-07-13-marketing-m6-server-deploy-readiness-report.md`
- `docs/ai/reports/2026-07-13-production-schema-catchup-0012-to-0015-audit-report.md`
- `docs/ai/reports/2026-07-13-marketing-m6-local-0015-upgrade-and-fe3-smoke-report.md`

---

## Status

**PACKAGE AUDIT COMPLETE — NOT SAFE TO COMMIT WHOLE TREE.**

Marketing M6 **can** be packaged for commit **only via allow-list staging**.

Tree is **heavily dirty** (~243 status lines; ~57 tracked files modified, +3499/−188 in tracked diff). Marketing itself is almost entirely **untracked** (`git ls-files` count for marketing paths = **0**).

**Do not** SCP / commit from dirty tree as-is.

---

## 1. Git status summary

| Metric | Value |
|--------|--------|
| Branch | `main` |
| HEAD | `6c3b617` Merge PR #96 content/threads-splitter-polish |
| Tracked modified | ~57 files |
| Untracked / other | large (`.ai_local`, booking, consulting imports, CRM reports, marketing, …) |
| Tracked marketing paths | **0** |

### Marketing-relevant tracked modifications (partial diffs)

| File | Marketing? | Notes |
|------|------------|--------|
| `backend/app/api/v1/router.py` | **Yes** | +marketing router import/include only (clean 2-line delta) |
| `backend/app/modules/models.py` | **Mixed** | +marketing models **and** +`Branch` import |
| `backend/app/modules/module_registry/seed.py` | **Mixed** | +`marketing` definition **and** +`booking` definition |
| `platform-console/src/routes.tsx` | **Yes** | marketing routes FE1–FE3 |
| `platform-console/src/components/layout/WorkspaceSidebar.tsx` | **Yes** | nav `marketing` |
| `platform-console/src/i18n/ruUi.ts` | **Mixed** | marketing labels (+ other unrelated if any beyond these 4 keys — diff shows only marketing keys) |
| `platform-console/src/workspace/moduleErrors.ts` | **Yes** | marketing disabled message |
| `platform-console/src/index.css` | **Mixed** | large CRM board CSS + marketing CSS at end |

### Explicitly NOT Marketing (hold — Package C)

Examples of unrelated tracked/untracked work in same tree:

- CRM / parties / workflows / public_leads / lead disposition / match UI  
- Booking module + booking tests + booking seed entitlements  
- Consulting imports_dry_run / C2 scripts / staging runners  
- Finance `PaymentDirection` + tenants `default_branch` (belong to **Package A**, not Marketing product)  
- Landing / content publish scripts / `.ai_local` / credentials / stackdumps  

---

## 2. Marketing backend package inventory

### Untracked — core module (include in Package B)

| Path | Status |
|------|--------|
| `backend/app/modules/marketing/__init__.py` | untracked |
| `backend/app/modules/marketing/enums.py` | untracked |
| `backend/app/modules/marketing/exceptions.py` | untracked |
| `backend/app/modules/marketing/models.py` | untracked |
| `backend/app/modules/marketing/schemas.py` | untracked |
| `backend/app/modules/marketing/repository.py` | untracked |
| `backend/app/modules/marketing/routes.py` | untracked |
| `backend/app/modules/marketing/service/__init__.py` | untracked |
| `backend/app/modules/marketing/service/topics.py` | untracked |
| `backend/app/modules/marketing/service/packs.py` | untracked |
| `backend/app/modules/marketing/service/pack_factory.py` | untracked |
| `backend/app/modules/marketing/service/texts.py` | untracked |
| `backend/app/modules/marketing/service/media.py` | untracked |
| `backend/app/modules/marketing/service/approval.py` | untracked |
| `backend/app/modules/marketing/service/approval_reset.py` | untracked |
| `backend/app/modules/marketing/service/slugify.py` | untracked |

### Untracked — tests (include in Package B)

| Path | Status |
|------|--------|
| `backend/tests/test_marketing_migration.py` | untracked |
| `backend/tests/test_marketing_topics.py` | untracked |
| `backend/tests/test_marketing_packs.py` | untracked |
| `backend/tests/test_marketing_texts_media.py` | untracked |
| `backend/tests/test_marketing_preflight_approval.py` | untracked |

### Tracked wiring — must include carefully

| Path | Status | How to include |
|------|--------|----------------|
| `backend/app/api/v1/router.py` | tracked modified | Marketing-only hunk (safe) |
| `backend/app/modules/models.py` | tracked modified | Include **marketing imports only** if committing Marketing alone; `Branch` import → Package A / 0014 companion |
| `backend/app/modules/module_registry/seed.py` | tracked modified | Include **`marketing` definition only**; exclude `booking` block |

### Missing / gaps

| Item | Status |
|------|--------|
| Dedicated marketing permission rows in `subscriptions/seed.py` | **Not present** in marketing-specific form (seed adds booking entitlements only — hold) |
| Publish/export BE (BE6) | **Out of scope** / intentionally absent |
| Already tracked clean marketing files | **None** |

---

## 3. Marketing frontend package inventory

### Untracked (Package B)

| Path | Role |
|------|------|
| `platform-console/src/api/marketing.ts` | API client |
| `platform-console/src/types/marketing.ts` | Types |
| `.../marketing/MarketingDashboardPage.tsx` | Dashboard |
| `.../marketing/MarketingTopicsPage.tsx` | Topics FE3 |
| `.../marketing/MarketingPacksPage.tsx` | Packs list FE3 |
| `.../marketing/MarketingPackDetailPage.tsx` | Pack detail shell |
| `.../marketing/MarketingPageHeader.tsx` | Header |
| `.../marketing/marketingLabels.ts` | RU labels |
| `.../marketing/marketingLabels.test.ts` | Helper tests |
| `.../marketing/marketingNextAction.ts` | Next-action |
| `.../marketing/marketingNextAction.test.ts` | Helper tests |
| `.../packDetail/PackDetailTextsTab.tsx` | Texts |
| `.../packDetail/PackDetailMediaTab.tsx` | Media |
| `.../packDetail/PackDetailPreflightTab.tsx` | Preflight |
| `.../packDetail/PackDetailApprovalTab.tsx` | Approval |
| `.../packDetail/PackDetailPublishTab.tsx` | Publish disabled |
| `.../packDetail/PackDetailLogsTab.tsx` | Logs |
| `.../packDetail/marketingErrors.ts` | API error mapping |

### Tracked wiring (Package B — careful)

| Path | Status | Notes |
|------|--------|--------|
| `platform-console/src/routes.tsx` | modified | Marketing routes only in diff — OK |
| `.../WorkspaceSidebar.tsx` | modified | one nav line — OK |
| `platform-console/src/i18n/ruUi.ts` | modified | 4 marketing labels — OK |
| `.../moduleErrors.ts` | modified | marketing message — OK |
| `platform-console/src/index.css` | **mixed** | Extract/commit **only** `.marketing-*` block; **exclude** CRM board CSS |

### Missing

| Item | Status |
|------|--------|
| FE publish/export live | intentionally missing |
| Binary upload UI | intentionally missing |

---

## 4. Migration inventory

| File | Rev | Down | Git | Package |
|------|-----|------|-----|---------|
| `20250702_0012_phase12_booking_e1.py` | `0012_booking_e1` | `0011…` | **untracked** | History consistency / Package A support (server may lack file) |
| `20260708_0013_c1c_payment_direction.py` | `0013_c1c_payment_direction` | `0012_booking_e1` | **untracked** | **Package A** schema catch-up — **not** Marketing product |
| `20260709_0014_core_branches_baseline.py` | `0014_core_branches_baseline` | `0013…` | **untracked** | **Package A** |
| `20260709_0015_marketing_cabinet_mvp.py` | `0015_marketing_cabinet_mvp` | `0014…` | **untracked** | **Package B** Marketing |

**Companion code for Package A (not Marketing product, but needed if A includes app readiness):**

- `backend/app/modules/branches/**` (untracked)  
- `backend/app/modules/tenants/{models,schemas,service}.py` (modified)  
- `backend/app/modules/finance/{models,schemas,service}.py` (modified)  
- `backend/app/core/enums.py` (`PaymentDirection`)  
- `backend/tests/test_migration_0014_branches.py` + finance test delta  

**Rule:** 0013/0014 **must not** ride silently inside “Marketing M6” commit/deploy.

---

## 5. Docs / reports inventory

### Required for Marketing package context (optional commit as docs commit)

| Doc | Class |
|-----|--------|
| `docs/ai/plans/2026-07-03-marketing-content-cabinet-product-tz.md` | TZ |
| `docs/ai/research/2026-07-09-margosya-to-cabinet-audit.md` | M1 research |
| `docs/ai/plans/2026-07-09-marketing-cabinet-data-model-draft.md` | M2 |
| `docs/ai/plans/2026-07-09-marketing-cabinet-ui-wireframe-plan.md` | M3 |
| `docs/ai/plans/2026-07-09-marketing-cabinet-api-contract-draft.md` | M4 |
| `docs/ai/plans/2026-07-09-marketing-cabinet-mvp-implementation-plan.md` | M5/M6 guide |
| BE/FE slice reports `2026-07-10-marketing-cabinet-m6-be*` / `m6-fe*` | slice reports |
| FE3 plan/report `2026-07-13-marketing-m6-fe3-*` | FE3 |
| Local smoke / 0015 upgrade / readiness / catch-up audit reports | ops |
| This Gate A1 report | stabilization |
| Handoff `2026-07-13-crm-ready-marketing-cabinet-next-handoff.md` | handoff |

### Optional / working notes

- `.ai_local/*` smoke scripts, backups — **do not commit** (secrets risk: `.local-dev-credentials`)  
- Site marketing content plan `2026-06-19-site-marketing-content-plan.md` — separate topic  

---

## 6. Package separation recommendation

### Package A — Schema catch-up `0012→0014`

**Include:**
- migrations `0013`, `0014` (+ `0012` file if needed for history)  
- preferably companion: `branches/**`, tenants/finance/enums deltas, `test_migration_0014_branches.py`, finance tests as needed  
- catch-up audit docs  

**Exclude:** Marketing module, Marketing FE, booking, CRM.

### Package B — Marketing M6

**Include:**
- `backend/app/modules/marketing/**`  
- migration **`0015` only**  
- marketing tests  
- FE marketing pages/api/types/helpers/tests  
- allow-listed wiring: router, models (marketing imports), seed (`marketing` only), routes/sidebar/ruUi/moduleErrors, marketing CSS  

**Exclude:** 0013/0014, booking, CRM, consulting, credentials.

### Package C — Unrelated / HOLD

- Booking, CRM E* live leftovers, public inbound rate limit (if not already deployed separately), consulting import runners, landing content, `.ai_local`, stackdump, workspace files  

---

## 7. Commit strategy recommendation

**Preferred: Option 1 — separate commits (after HQ asks to commit)**

1. **Docs** (optional first): Marketing plans/reports only  
2. **Schema catch-up Package A:** 0013/0014 (+ companions) — separate PR  
3. **Marketing backend Package B1:** module + 0015 + tests + minimal router/models/seed  
4. **Marketing frontend Package B2:** FE1–FE3 + CSS marketing block + routes/nav/i18n  

**Not preferred now:** one giant Marketing+schema+CRM commit.

**Option 2** (single Marketing feature commit) only after Package A already merged and tree is cleaned.

**Can Marketing be committed safely today?**  
**Yes, only with pathspec / interactive allow-list.**  
**No**, if staging `git add .` or whole dirty tree.

**Commit not requested in this Gate — do not commit yet.**

---

## 8. Validation commands (before any future commit)

### Backend

```bash
cd backend
python -m alembic heads
python -m alembic current   # local DB
python -m compileall app/modules/marketing
python -m pytest tests/test_marketing_topics.py tests/test_marketing_packs.py \
  tests/test_marketing_texts_media.py tests/test_marketing_preflight_approval.py \
  tests/test_marketing_migration.py -q
# If packaging Package A too:
python -m pytest tests/test_migration_0014_branches.py tests/test_finance.py -q
```

### Frontend

```bash
cd platform-console
npx tsx src/pages/workspace/marketing/marketingLabels.test.ts
npx tsx src/pages/workspace/marketing/marketingNextAction.test.ts
npm run build
# For production artifact later:
# VITE_API_BASE_URL=https://flexity.asia/api/v1 npm run build
```

---

## 9. Production gate sequence (after A1)

| Gate | Purpose |
|------|---------|
| **A1** | Stabilize / allow-list package (this report) |
| **A2** | Schema catch-up **plan/approval** for `0012→0014` |
| **A3** | Run `0012→0014` on server with full DB backup + smoke |
| **A4** | Marketing M6 deploy package approval (BE+0015+FE) |
| **A5** | Marketing deploy: backend + `0015` + console + module enable + smoke |

Publish/export / Margosya remain out until separate HQ.

---

## 10. What was not touched

No functional code changes, no commit, no stash/clean/delete, no migrations, no deploy, no env, no production/server, no DB writes, no module enable.

---

## 11. Risks

1. **0 tracked marketing files** — easy to lose/forget in deploy  
2. **`seed.py` mixes booking + marketing** — accidental booking ship  
3. **`models.py` mixes Branch + marketing**  
4. **`index.css` mixes CRM + marketing**  
5. **Credentials in `.ai_local` / `.local-dev-credentials`** — never commit  
6. Committing whole tree would ship CRM/Booking/Consulting noise  

---

## 12. Next recommended step

HQ approve: **create a clean feature branch and stage Package B allow-list** (docs optional), **without** 0013/0014 booking/CRM — then ask for **explicit commit approval**.

Parallel/next track: Package A (0013/0014) for Gate A2.

---

## HQ summary

1. **Status:** A1 audit complete; whole-tree commit **unsafe**  
2. **Git status:** dirty (~243 lines); Marketing **untracked** (0 ls-files)  
3. **Marketing backend:** full `marketing/` module + 5 tests untracked; router/models/seed need surgical include  
4. **Marketing frontend:** full FE1–FE3 untracked + tracked routes/sidebar/i18n/moduleErrors; CSS mixed  
5. **Migrations:** all `0012–0015` **untracked**; **0015→Package B**; **0013/0014→Package A**  
6. **Docs:** TZ/M1–M5/BE-FE reports/smoke/readiness/catch-up present (mostly untracked)  
7. **Untracked Marketing:** module + FE + api/types + tests + 0015  
8. **Unrelated:** CRM, Booking, consulting imports, finance/tenants (→A), landing, `.ai_local`  
9. **Separation:** A=schema 0013/0014; B=Marketing+0015+FE; C=hold rest  
10. **Commit strategy:** Option 1 separate commits; allow-list only; **no commit yet**  
11. **Validation:** marketing pytest + helper tsx + `npm run build` (+ 0014/finance if A)  
12. **Gates:** A1→A2→A3→A4→A5  
13. **Not touched:** code/commit/deploy/migrations/env/prod  
14. **Risks:** dirty tree, mixed seed/models/css, secrets in local dirs  
15. **Next:** HQ → allow-list branch for Package B (and separately Package A); then explicit commit request  
