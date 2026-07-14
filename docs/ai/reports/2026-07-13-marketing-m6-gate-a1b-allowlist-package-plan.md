# Gate A1b — Allow-list package plan (Marketing M6)

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Category:** documentation_only / local git planning  
**Parent:** `docs/ai/reports/2026-07-13-marketing-m6-gate-a1-package-stabilization-report.md`

**HQ constraints honored:** no code change, no `git add`, no commit, no branch create, no stash, no deploy, no migrations, no env, no production.

---

## Status

**ALLOW-LIST PLAN READY.**  
Operational next step after HQ approval: create branch + stage by allow-list (commands below are draft only).

---

## 1. Branch status

| Item | Value |
|------|--------|
| Current branch | `main` |
| HEAD | `6c3b617` — Merge PR #96 content/threads-splitter-polish |
| Upstream | `origin/main` (tracking exists) |
| Uncommitted changes | **Yes** (~243 porcelain lines) |
| Dirty tree safe for whole commit? | **No** |

### New branch recommendation

**Name:** `feature/marketing-m6-package`

**How (plan only — do not run yet):**

```bash
# After HQ approval to create branch:
git switch -c feature/marketing-m6-package
```

Creating a branch only moves HEAD metadata; still recommended **only after HQ yes**, because dirty working tree will follow onto the new branch.

**Do not** create branch in this gate.

---

## 2. Package A allow-list (schema catch-up 0013/0014)

### A1 — Migrations only (preferred minimal)

```text
backend/alembic/versions/20260708_0013_c1c_payment_direction.py
backend/alembic/versions/20260709_0014_core_branches_baseline.py
```

Optional history helper (server disk may lack 0012 file):

```text
backend/alembic/versions/20250702_0012_phase12_booking_e1.py
```

### A2 — Docs for catch-up

```text
docs/ai/plans/2026-07-13-production-schema-catchup-0012-to-0015-audit.md
docs/ai/reports/2026-07-13-production-schema-catchup-0012-to-0015-audit-report.md
docs/ai/plans/2026-07-09-flexity-core-0014-branches-baseline-plan.md
```

### Package A optional code risk — needs HQ decision

**Not included in minimal A.** If HQ wants app-ready 0013/0014 (local finance/tenants already expect schema):

| Path | Why |
|------|-----|
| `backend/app/core/enums.py` | `PaymentDirection` |
| `backend/app/modules/finance/models.py` | direction column |
| `backend/app/modules/finance/schemas.py` | direction payloads |
| `backend/app/modules/finance/service.py` | direction mapping |
| `backend/app/modules/branches/**` | Branch ORM |
| `backend/app/modules/tenants/models.py` | `default_branch_id` |
| `backend/app/modules/tenants/schemas.py` | schema field |
| `backend/app/modules/tenants/service.py` | `ensure_default_branch` |
| `backend/app/modules/models.py` | Branch import only (surgical) |
| `backend/tests/test_migration_0014_branches.py` | migration test |
| `backend/tests/test_finance.py` | finance direction tests (may mix other deltas — review) |

**Recommendation:** Gate A2 production catch-up can start with **migrations-only A1** while server code stays old (compat OK per audit). Ship optional code in a **separate** commit/PR if needed.

### Package A staging draft (DO NOT RUN)

```bash
git add -- \
  backend/alembic/versions/20260708_0013_c1c_payment_direction.py \
  backend/alembic/versions/20260709_0014_core_branches_baseline.py \
  backend/alembic/versions/20250702_0012_phase12_booking_e1.py \
  docs/ai/plans/2026-07-13-production-schema-catchup-0012-to-0015-audit.md \
  docs/ai/reports/2026-07-13-production-schema-catchup-0012-to-0015-audit-report.md \
  docs/ai/plans/2026-07-09-flexity-core-0014-branches-baseline-plan.md

git diff --cached --stat
git diff --cached --name-only
git diff --cached --name-only | sort
```

**Exclude from A:** `0015`, Marketing module/FE, booking, CRM.

---

## 3. Package B allow-list (Marketing M6)

### B — Backend module (untracked)

```text
backend/app/modules/marketing/__init__.py
backend/app/modules/marketing/enums.py
backend/app/modules/marketing/exceptions.py
backend/app/modules/marketing/models.py
backend/app/modules/marketing/schemas.py
backend/app/modules/marketing/repository.py
backend/app/modules/marketing/routes.py
backend/app/modules/marketing/service/__init__.py
backend/app/modules/marketing/service/topics.py
backend/app/modules/marketing/service/packs.py
backend/app/modules/marketing/service/pack_factory.py
backend/app/modules/marketing/service/texts.py
backend/app/modules/marketing/service/media.py
backend/app/modules/marketing/service/approval.py
backend/app/modules/marketing/service/approval_reset.py
backend/app/modules/marketing/service/slugify.py
```

### B — Tests + migration 0015

```text
backend/tests/test_marketing_migration.py
backend/tests/test_marketing_topics.py
backend/tests/test_marketing_packs.py
backend/tests/test_marketing_texts_media.py
backend/tests/test_marketing_preflight_approval.py
backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py
```

### B — Backend wiring (tracked modified — surgical)

```text
backend/app/api/v1/router.py
```

Safe: diff currently only marketing include.

```text
backend/app/modules/models.py
backend/app/modules/module_registry/seed.py
```

**Risk:** mixed with Branch import / booking seed. Prefer:

- `git add -p` for these two files, **or**
- HQ-approved temporary cleanup commit that splits hunks before packaging.

### B — Frontend pure Marketing (untracked)

```text
platform-console/src/api/marketing.ts
platform-console/src/types/marketing.ts
platform-console/src/pages/workspace/marketing/MarketingDashboardPage.tsx
platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx
platform-console/src/pages/workspace/marketing/MarketingPacksPage.tsx
platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx
platform-console/src/pages/workspace/marketing/MarketingPageHeader.tsx
platform-console/src/pages/workspace/marketing/marketingLabels.ts
platform-console/src/pages/workspace/marketing/marketingLabels.test.ts
platform-console/src/pages/workspace/marketing/marketingNextAction.ts
platform-console/src/pages/workspace/marketing/marketingNextAction.test.ts
platform-console/src/pages/workspace/marketing/packDetail/PackDetailTextsTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/PackDetailMediaTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/PackDetailApprovalTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPublishTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/PackDetailLogsTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/marketingErrors.ts
```

### B — Frontend wiring (tracked — mostly marketing-only diffs)

```text
platform-console/src/routes.tsx
platform-console/src/components/layout/WorkspaceSidebar.tsx
platform-console/src/i18n/ruUi.ts
platform-console/src/workspace/moduleErrors.ts
```

### B — CSS (mixed-file risk)

```text
platform-console/src/index.css
```

| Fact | Detail |
|------|--------|
| Marketing CSS | approx lines **1377–1498** (`.marketing-*`) |
| Also in same file diff | large **CRM board** styles |
| Risk if `git add` whole file | CRM CSS ships with Marketing |

**Recommendation:**

1. **Preferred:** extract marketing CSS to e.g. `platform-console/src/pages/workspace/marketing/marketing.css` + import (needs HQ code approval — not this gate).  
2. **Interim:** `git add -p platform-console/src/index.css` and stage **only** marketing hunks.  
3. **Avoid:** `git add platform-console/src/index.css` bare.

### B — Docs (Package B3)

```text
docs/ai/plans/2026-07-03-marketing-content-cabinet-product-tz.md
docs/ai/research/2026-07-09-margosya-to-cabinet-audit.md
docs/ai/plans/2026-07-09-marketing-cabinet-data-model-draft.md
docs/ai/plans/2026-07-09-marketing-cabinet-ui-wireframe-plan.md
docs/ai/plans/2026-07-09-marketing-cabinet-api-contract-draft.md
docs/ai/plans/2026-07-09-marketing-cabinet-mvp-implementation-plan.md
docs/ai/plans/2026-07-13-marketing-m6-fe3-workflow-polish-plan.md
docs/ai/plans/2026-07-13-marketing-m6-server-deploy-readiness-plan.md
docs/ai/reports/2026-07-10-marketing-cabinet-m6-be1-be2-report.md
docs/ai/reports/2026-07-10-marketing-cabinet-m6-be3-packs-api-report.md
docs/ai/reports/2026-07-10-marketing-cabinet-m6-be4-texts-media-api-report.md
docs/ai/reports/2026-07-10-marketing-cabinet-m6-be5-preflight-approval-report.md
docs/ai/reports/2026-07-10-marketing-cabinet-m6-fe1-route-nav-shell-report.md
docs/ai/reports/2026-07-10-marketing-cabinet-m6-fe2-pack-detail-editor-report.md
docs/ai/reports/2026-07-13-marketing-m6-fe3-workflow-polish-report.md
docs/ai/reports/2026-07-13-marketing-m6-fe3-local-smoke-report.md
docs/ai/reports/2026-07-13-marketing-m6-local-0015-upgrade-and-fe3-smoke-report.md
docs/ai/reports/2026-07-13-marketing-m6-server-deploy-readiness-report.md
docs/ai/reports/2026-07-13-marketing-m6-gate-a1-package-stabilization-report.md
docs/ai/reports/2026-07-13-marketing-m6-gate-a1b-allowlist-package-plan.md
docs/ai/handoffs/2026-07-13-crm-ready-marketing-cabinet-next-handoff.md
```

Large docs set is OK if kept in docs commit; optional trim if HQ wants thinner PR.

### Package B staging draft (DO NOT RUN)

```bash
# --- B1 backend ---
git add -- \
  backend/app/modules/marketing \
  backend/tests/test_marketing_migration.py \
  backend/tests/test_marketing_topics.py \
  backend/tests/test_marketing_packs.py \
  backend/tests/test_marketing_texts_media.py \
  backend/tests/test_marketing_preflight_approval.py \
  backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py \
  backend/app/api/v1/router.py

# models.py / seed.py: use patch mode (HQ-required care)
git add -p -- backend/app/modules/models.py
git add -p -- backend/app/modules/module_registry/seed.py

# --- B2 frontend ---
git add -- \
  platform-console/src/api/marketing.ts \
  platform-console/src/types/marketing.ts \
  platform-console/src/pages/workspace/marketing \
  platform-console/src/routes.tsx \
  platform-console/src/components/layout/WorkspaceSidebar.tsx \
  platform-console/src/i18n/ruUi.ts \
  platform-console/src/workspace/moduleErrors.ts

git add -p -- platform-console/src/index.css   # marketing hunks only

# --- B3 docs (optional separate) ---
git add -- \
  docs/ai/plans/2026-07-03-marketing-content-cabinet-product-tz.md \
  docs/ai/research/2026-07-09-margosya-to-cabinet-audit.md \
  docs/ai/plans/2026-07-09-marketing-cabinet-data-model-draft.md \
  docs/ai/plans/2026-07-09-marketing-cabinet-ui-wireframe-plan.md \
  docs/ai/plans/2026-07-09-marketing-cabinet-api-contract-draft.md \
  docs/ai/plans/2026-07-09-marketing-cabinet-mvp-implementation-plan.md \
  docs/ai/plans/2026-07-13-marketing-m6-fe3-workflow-polish-plan.md \
  docs/ai/plans/2026-07-13-marketing-m6-server-deploy-readiness-plan.md \
  docs/ai/reports/2026-07-10-marketing-cabinet-m6-be1-be2-report.md \
  docs/ai/reports/2026-07-10-marketing-cabinet-m6-be3-packs-api-report.md \
  docs/ai/reports/2026-07-10-marketing-cabinet-m6-be4-texts-media-api-report.md \
  docs/ai/reports/2026-07-10-marketing-cabinet-m6-be5-preflight-approval-report.md \
  docs/ai/reports/2026-07-10-marketing-cabinet-m6-fe1-route-nav-shell-report.md \
  docs/ai/reports/2026-07-10-marketing-cabinet-m6-fe2-pack-detail-editor-report.md \
  docs/ai/reports/2026-07-13-marketing-m6-fe3-workflow-polish-report.md \
  docs/ai/reports/2026-07-13-marketing-m6-fe3-local-smoke-report.md \
  docs/ai/reports/2026-07-13-marketing-m6-local-0015-upgrade-and-fe3-smoke-report.md \
  docs/ai/reports/2026-07-13-marketing-m6-server-deploy-readiness-report.md \
  docs/ai/reports/2026-07-13-marketing-m6-gate-a1-package-stabilization-report.md \
  docs/ai/reports/2026-07-13-marketing-m6-gate-a1b-allowlist-package-plan.md \
  docs/ai/handoffs/2026-07-13-crm-ready-marketing-cabinet-next-handoff.md

# --- safety ---
git diff --cached --stat
git diff --cached --name-only
git diff --cached --name-only | sort
```

**After each `git add -p`, verify name-only list contains no CRM/booking/consulting paths.**

---

## 4. Exclusion / deny-list

Never stage:

```text
.ai_local/
backend/.ai_local/
backend/.local-dev-credentials
*.stackdump
.worktrees/
.codex-remote-attachments/
Flexity.code-workspace
platform-console/dist/
platform-console/node_modules/
backend/**/__pycache__/
*.db
*.sql backups under .ai_local/backups/
landing/**
scripts/content/**
backend/app/modules/booking/**
backend/app/modules/imports_dry_run/**
backend/scripts/c2*
backend/scripts/consulting*
backend/scripts/seed_booking_demo.py
# CRM / parties / workflows / public_leads working tree (unless separate HQ)
backend/app/modules/parties/**
backend/app/modules/workflows/**
backend/app/modules/public_leads/**
platform-console/src/pages/workspace/CrmPage.tsx
platform-console/src/components/workspace/CrmPipelineBoard.tsx
platform-console/src/components/workspace/CreateWorkItemModal.tsx
# Package A optional code unless HQ includes it
backend/app/modules/finance/**
backend/app/modules/tenants/**
backend/app/modules/branches/**
backend/app/core/enums.py
backend/alembic/versions/20260708_0013_c1c_payment_direction.py   # stay in Package A
backend/alembic/versions/20260709_0014_core_branches_baseline.py  # stay in Package A
```

Secrets grep after any future stage:

```bash
git diff --cached | rg -i "password|secret|token|api_key|DATABASE_URL|BEGIN OPENSSH" || true
```

---

## 5. Commit strategy (draft — do not commit)

**Preferred sequence on `feature/marketing-m6-package`:**

| Commit | Message (draft) | Contents |
|--------|-----------------|----------|
| **A** | `schema: add production catch-up migrations 0013-0014` | Package A migrations (+ optional 0012 file) + catch-up docs |
| **B1** | `marketing: add cabinet backend mvp` | `marketing/**`, 0015, tests, router, surgical models/seed |
| **B2** | `marketing: add cabinet console workflow` | FE pages/api/types + routes/sidebar/i18n/moduleErrors + marketing CSS hunks |
| **B3** | `docs: add marketing m6 plans and reports` | docs allow-list |

**Alternative:** merge B1+B2 into one Marketing code commit if HQ wants fewer PRs — still keep **A separate** from Marketing.

**No production deploy until these commits are stable and reviewed.**

---

## 6. Validation commands (before commit)

```bash
# Local alembic
cd backend
python -m alembic heads
python -m alembic history -r 0012_booking_e1:head
python -m alembic current

# Package A (if staged/committed)
python -m pytest tests/test_migration_0014_branches.py tests/test_finance.py -q

# Package B backend
python -m compileall app/modules/marketing
python -m pytest \
  tests/test_marketing_topics.py \
  tests/test_marketing_packs.py \
  tests/test_marketing_texts_media.py \
  tests/test_marketing_preflight_approval.py \
  tests/test_marketing_migration.py -q

# Package B frontend
cd ../platform-console
npx tsx src/pages/workspace/marketing/marketingLabels.test.ts
npx tsx src/pages/workspace/marketing/marketingNextAction.test.ts
npm run build

# Staged safety (after future git add — not now)
git diff --cached --name-only | sort
git diff --cached | rg -i "password|secret|token|api_key|BEGIN OPENSSH" || true
# Ensure booking not slipped into seed staging:
git diff --cached -- backend/app/modules/module_registry/seed.py | rg "booking|marketing" || true
# Ensure CSS not full CRM dump:
git diff --cached -- platform-console/src/index.css | rg "crm-pipeline|marketing-" || true
```

---

## 7. Risk notes

1. **CSS:** staging whole `index.css` ships unrelated CRM board styles.  
2. **routes/sidebar:** current diffs look marketing-only — still re-check cached.  
3. **seed:** currently also adds **booking** — must use `-p` or risk shipping booking definition.  
4. **models.py:** includes **Branch** import — Package A concern; exclude unless HQ couples packages.  
5. **0013/0014 migrations alone** do not deploy finance/tenants code — OK for old server; optional code is separate HQ risk.  
6. Untracked Marketing docs are many but safe; exclude `.ai_local` always.  
7. No production deploy until commits stable.

---

## 8. What was not touched

No code edits, no `git add`, no commit, no branch create, no stash, no migrations, no deploy, no env, no production/server, no DB writes.

---

## 9. Next recommended step

1. HQ approve branch name `feature/marketing-m6-package`.  
2. HQ approve staging Package **A** (migrations-only) vs A+optional code.  
3. HQ approve Package **B** allow-list + CSS strategy (`-p` vs extract).  
4. Then explicit command: «create branch and stage Package A/B» → then separate **commit approval**.

---

## HQ summary

1. **Status:** A1b allow-list plan complete (no staging executed)  
2. **Current branch/HEAD:** `main` / `6c3b617` tracking `origin/main`; dirty (~243)  
3. **New branch recommendation:** `feature/marketing-m6-package` (create only after HQ)  
4. **Package A allow-list:** `0013` + `0014` (+ optional `0012` file) + catch-up docs; optional finance/branches/tenants code = HQ risk decision  
5. **Package B allow-list:** full `marketing/` + 0015 + tests + FE marketing + surgical router/routes/sidebar/i18n; models/seed/CSS via `-p`  
6. **CSS/mixed-file risk:** `index.css` contains CRM + marketing — do not add whole file blindly  
7. **Exclusion list:** `.ai_local`, credentials, CRM/Booking/consulting, landing, dist, Package A migs in B, etc.  
8. **Staging commands:** drafted above; **not run**  
9. **Commit strategy:** A → B1 → B2 → B3  
10. **Validation:** alembic heads/history; marketing pytest; helper tsx; build; cached name-only + secrets grep  
11. **Risks:** mixed seed/models/css; 0013/0014 code gap; dirty tree  
12. **Not touched:** add/commit/branch/deploy/migrations/env/prod  
13. **Next:** HQ approve create-branch + first allow-list stage (A or B)  
