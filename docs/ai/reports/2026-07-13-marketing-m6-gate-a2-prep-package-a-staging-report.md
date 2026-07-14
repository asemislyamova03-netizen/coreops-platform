# Gate A2-prep — Package A staging report

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Gate:** A2-prep (branch + stage Package A only)  
**Commit:** **not performed**

**Parents:**
- `docs/ai/reports/2026-07-13-marketing-m6-gate-a1b-allowlist-package-plan.md`
- `docs/ai/reports/2026-07-13-marketing-m6-gate-a1-package-stabilization-report.md`

---

## Status

**PASS — Package A staged for HQ review.**

- Branch created: `feature/marketing-m6-package`
- HEAD unchanged: `6c3b617`
- Staged: **10 files** (3 alembic + 7 docs)
- **No commit**
- Package B / marketing code / CSS / router **not staged**

---

## 1. Pre-check / branch actions

| Item | Value |
|------|--------|
| Branch before | `main` |
| HEAD before | `6c3b617` — Merge PR #96 content/threads-splitter-polish |
| Expected HEAD | ✅ matches prior A1b (`6c3b617`) |
| Action | `git switch -c feature/marketing-m6-package` |
| Branch after | `feature/marketing-m6-package` (new) |
| HEAD after | `6c3b617` (unchanged) |
| Existing branch overwrite | N/A — branch did not exist |

Working tree remains dirty (unrelated unstaged files) — only allow-list was staged.

---

## 2. Package A files staged

```text
backend/alembic/versions/20250702_0012_phase12_booking_e1.py
backend/alembic/versions/20260708_0013_c1c_payment_direction.py
backend/alembic/versions/20260709_0014_core_branches_baseline.py
docs/ai/plans/2026-07-09-flexity-core-0014-branches-baseline-plan.md
docs/ai/plans/2026-07-13-marketing-m6-server-deploy-readiness-plan.md
docs/ai/plans/2026-07-13-production-schema-catchup-0012-to-0015-audit.md
docs/ai/reports/2026-07-13-marketing-m6-gate-a1-package-stabilization-report.md
docs/ai/reports/2026-07-13-marketing-m6-gate-a1b-allowlist-package-plan.md
docs/ai/reports/2026-07-13-marketing-m6-server-deploy-readiness-report.md
docs/ai/reports/2026-07-13-production-schema-catchup-0012-to-0015-audit-report.md
```

| Include | Rationale |
|---------|-----------|
| 0013 + 0014 | Core Package A migrations |
| optional 0012 file | A1b history helper (server disk lacked 0012 file) |
| catch-up + readiness + A1/A1b docs | HQ-listed Package A docs |
| 0014 branches baseline plan | A1b Package A docs allow-list |

---

## 3. Any non-Package-A files staged?

**No Package B code paths staged** (verified):

- no `backend/app/modules/marketing/**`
- no `0015_marketing_cabinet_mvp.py`
- no `index.css` / router / sidebar / i18n / seed / models

Note: some **staged doc filenames** contain the word `marketing` (readiness / gate A1 / A1b). Those are Package A planning docs, **not** Marketing application code.

---

## 4. Staged diff stat

```text
10 files changed, 2879 insertions(+)
```

| Area | Approx |
|------|--------|
| `0012` migration file | +350 |
| `0013` | +42 |
| `0014` | +134 |
| docs | remainder |

---

## 5. `git diff --cached --check`

**Result:** trailing whitespace warnings on **markdown docs only** (multiple lines).

- No whitespace errors reported on the three Alembic `.py` files in the check output sample.
- Docs trailing whitespace is non-blocking for HQ review of Package A; optional cleanup later if HQ wants a clean `--check`.

---

## 6. Secrets / path scan

Command:

```bash
git diff --cached --name-only | grep -E '(^\.ai_local|secret|credential|\.env|dist/|node_modules|backup|dump|\.pem|\.key)' || true
```

**Result:** empty (no matches).

---

## 7. Migration metadata (read staged files; no upgrade)

### 0013 — `20260708_0013_c1c_payment_direction.py`

| Field | Value |
|-------|--------|
| revision | `0013_c1c_payment_direction` |
| down_revision | `0012_booking_e1` |
| upgrade | ADD `payments.direction` NOT NULL + `server_default='incoming'` + index |
| touches existing tables | **Yes** — `payments` |
| data/backfill | server_default only (no row loop) |
| downgrade | **Yes** — drop index + drop column |

### 0014 — `20260709_0014_core_branches_baseline.py`

| Field | Value |
|-------|--------|
| revision | `0014_core_branches_baseline` |
| down_revision | `0013_c1c_payment_direction` |
| upgrade | CREATE `branches`; ADD nullable `tenants.default_branch_id` + FK; **`_backfill_default_branches()`** |
| touches existing tables | **Yes** — `tenants` (+ new `branches`) |
| data/backfill | **Yes** — default `main` branch per tenant |
| downgrade | **Yes** — null FK, drop FK/index/column, drop `branches` |

### Optional staged 0012 file

| Field | Value |
|-------|--------|
| revision | `0012_booking_e1` |
| down_revision | `0011_phase11` |
| note | Staging this file does **not** re-run 0012 on server (stamp already `0012`); it restores missing history file for Alembic graph |

### Downgrade reality

| Rev | Downgrade code | Prod-safe? |
|-----|----------------|------------|
| 0013 | Yes | Conditional (if direction unused) |
| 0014 | Yes | **Not easy** after backfill/use — prefer backup restore |

Finance/tenants/branches **application code** was intentionally **not** staged (optional HQ risk left open).

---

## 8. Report file

Created (this file):

`docs/ai/reports/2026-07-13-marketing-m6-gate-a2-prep-package-a-staging-report.md`

**Not staged** (created after staging; not auto-added).

---

## 9. What was not touched

- no commit  
- no Package B staging  
- no `git add .` / `-A`  
- no migration run / deploy / env / production / DB writes  
- no stash / delete / reset  
- working-tree dirty files remain unstaged  

---

## 10. Risks

1. Docs `--check` trailing whitespace noise (docs only).  
2. Optional `0012` file included — correct for history, but reviewers must not confuse with re-applying booking schema.  
3. Finances/tenants companion code still **unstaged** — intentional for migrations-only Package A.  
4. Dirty tree still present outside index — careful not to accidentally broad-add later.  

---

## 11. Next recommended step

HQ review staged Package A (`git diff --cached`), then **explicit commit approval** for Commit A:

`schema: add production catch-up migrations 0013-0014`

After that: Gate A2 production catch-up plan / Package B staging (separate HQ).

---

## HQ summary

1. **Status:** PASS — Package A staged, no commit  
2. **Branch before:** `main`  
3. **Branch after:** `feature/marketing-m6-package` (created)  
4. **HEAD:** `6c3b617` (unchanged)  
5. **Package A staged:** 3 alembic (`0012` opt + `0013` + `0014`) + 7 docs  
6. **Non-Package-A files staged:** none (no Marketing/CSS/router code)  
7. **Staged diff stat:** 10 files, +2879  
8. **`--check`:** docs trailing whitespace only  
9. **Secrets/path scan:** clean  
10. **0013:** `0013_c1c_payment_direction` ← `0012_booking_e1`  
11. **0014:** `0014_core_branches_baseline` ← `0013_c1c_payment_direction`  
12. **Downgrade:** both have scripts; 0014 not easy in prod after use  
13. **Report file created:** yes (unstaged)  
14. **Not touched:** commit, Package B, deploy, migrations run, env, prod  
15. **Risks:** doc whitespace; 0012 history file nuance; companion code not included  
16. **Next:** HQ review cached diff → approve **Commit A** only  
