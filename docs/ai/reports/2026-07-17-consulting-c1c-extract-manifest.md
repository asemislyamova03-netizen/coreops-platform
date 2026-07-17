# Consulting/C1c CRM Inbound Extract Manifest

**Date:** 2026-07-17
**Source (READ ONLY):** `C:/Users/АДМИН/OneDrive/Documents/Flexity`
**Source tip:** `feature/marketing-m8-publish-bridge` @ `9658a82` + large uncommitted WIP
**Target worktree:** `.worktrees/consulting-c1c-crm-inbound`
**Target branch:** `feature/consulting-c1c-crm-inbound` FROM `origin/main` @ `76773ec`
**Mode:** local extract only — no push / merge / deploy / dirty-root mutation

## Task Classification

1. **Project:** Flexity
2. **Category:** universal_module (CRM inbound match + Consulting import readiness)
3. **Risk level:** medium
4. **Intended scope:** parties match, public_leads rate-limit + match, imports_dry_run, finance PaymentDirection ORM, documents import, CRM console UI, related tests/docs/scripts
5. **Forbidden scope:** wholesale `models.py`, `test_tenants.py`, `conftest.py`, `branches/**`, E1a/E1b/M8 migrations/process overlay, credentials, `.env`, `.ai_local`, `.worktrees`, dumps
6. **Required plan:** extract/reconstruct (approved by parent task)

## PaymentDirection migration decision

- Dirty root ORM needs `payments.direction`.
- `origin/main` already contains `backend/alembic/versions/20260708_0013_c1c_payment_direction.py`.
- Alembic head on target remains `0023_mkt_storage_profiles` (unchanged).
- **Action:** apply enum/model/schema/service hunks only. **Do NOT create 0024.** No migration renumber needed.

## Copied paths (source → dest)

### New modules / files (wholesale copy)

| Source | Dest |
|---|---|
| `backend/app/modules/parties/matching.py` | same |
| `backend/app/modules/public_leads/rate_limit.py` | same |
| `backend/app/modules/imports_dry_run/*.py` (no `__pycache__`) | same |
| `backend/app/modules/industry_templates/lead_sources.py` | same |
| `backend/scripts/c2a_synthetic_dry_run.py` | same |
| `backend/scripts/c2b_readonly_dry_run.py` | same |
| `backend/scripts/c2b_real_source_dry_run.py` | same |
| `backend/scripts/consulting_staging_write_import.py` | same |
| `backend/tests/fixtures/consulting_legacy_min.sqlite` | same |
| `backend/tests/test_party_match.py` | same |
| `backend/tests/test_public_leads_rate_limit.py` | same |
| `backend/tests/test_imports_dry_run.py` | same |
| `backend/tests/test_imports_sqlite_readonly.py` | same |
| `backend/tests/test_import_summary_contract.py` | same |
| `backend/tests/test_lead_sources.py` | same |
| `backend/tests/test_staging_write_import_runner.py` | same |
| `backend/tests/test_status_mapping_contracts.py` | same |
| `platform-console/src/api/leadSources.ts` | same |
| `platform-console/src/types/leadSources.ts` | same |
| `platform-console/src/components/workspace/CrmBoardViewSwitcher.tsx` | same |
| `platform-console/src/components/workspace/CrmCardDensitySwitcher.tsx` | same |
| `platform-console/src/components/workspace/CrmDisplayModeSwitcher.tsx` | same |
| `platform-console/src/components/workspace/CrmStageFilter.tsx` | same |
| `platform-console/src/components/workspace/CrmWorkItemsListView.tsx` | same |
| `platform-console/src/components/workspace/LeadDetailModal.tsx` | same |
| `platform-console/src/workspace/*` (helpers + tests listed in copy log) | same |

### Modified tracked files (dirty working tree overlay onto main; uncommitted-only vs HEAD)

| Source | Dest | Notes |
|---|---|---|
| `backend/.gitignore` | same | hunk: `tests/_c2b_tmp/` |
| `backend/app/core/config.py` | same | public_leads rate-limit settings |
| `backend/app/core/enums.py` | same | `PaymentDirection` |
| `backend/app/core/exceptions.py` | same | `RateLimitExceededError` |
| `backend/app/core/exception_handlers.py` | same | 429 for rate limit |
| `backend/app/modules/parties/{repository,routes,schemas,service}.py` | same | match API |
| `backend/app/modules/public_leads/{schemas,service}.py` | same | match + rate limit |
| `backend/app/modules/workflows/{repository,routes,schemas,service}.py` | same | CRM history/disposition helpers |
| `backend/app/modules/finance/{models,schemas,service}.py` | same | direction ORM/API (migration already on main) |
| `backend/app/modules/documents/{routes,schemas,service}.py` | same | `POST /documents/import` |
| `backend/app/modules/audit/{schemas,service}.py` | same | import batch summary audit hook |
| `backend/app/modules/industry_templates/{routes,schemas,seed,service}.py` | same | lead sources dictionary |
| `backend/tests/test_documents.py` | same | import tests |
| `backend/tests/test_finance.py` | same | direction tests |
| `backend/tests/test_public_leads.py` | same | match/rate-limit tests |
| `backend/tests/test_industry_templates.py` | same | lead sources tests |
| `platform-console/src/api/{parties,workflows}.ts` | same | match/history API |
| `platform-console/src/types/{party,workflows}.ts` | same | match types |
| `platform-console/src/components/workspace/{CreateWorkItemModal,CrmPipelineBoard}.tsx` | same | match UI |
| `platform-console/src/pages/workspace/CrmPage.tsx` | same | CRM page |

### Docs (selected Consulting/C1c/C2 + CRM match plans/reports/specs)

Copied selectively under `docs/ai/{plans,reports,specs}/` and key root docs — see copy log section below after execution.

## Skipped paths (with reason)

| Path | Reason |
|---|---|
| `backend/app/modules/models.py` | Forbidden wholesale; dirty delta only drops `ProcessRun` (process overlay) — not needed for C1c |
| `backend/tests/test_tenants.py` | Forbidden; dirty delta is default_branch assertions (C3/branches), not C1c inbound |
| `backend/tests/conftest.py` | Forbidden; no C1c-required change identified |
| `backend/app/modules/branches/**` | Forbidden wholesale; already present on `origin/main` |
| E1a/E1b/M8 migrations / `process_overlay/**` | Forbidden / out of scope |
| New migration `0024_*` | Not needed — `0013_c1c_payment_direction` already on main |
| Marketing committed tip files (`object_storage/**`, `secrets/**`, etc.) | Not Consulting/C1c |
| `.env`, credentials, `.ai_local/**`, dumps, bash stackdumps, `__pycache__`, `_c2b_tmp` contents | Secrets/hygiene |
| Dirty root itself | READ/COPY ONLY — no stash/reset/commit/modify |

## Manual hunks on shared files

All shared-file transfers below are **exact dirty working-tree overlays** onto `origin/main` copies (verified: scoped C1c files have **zero** committed tip delta vs `origin/main`; deltas are uncommitted WIP only):

1. `backend/app/core/enums.py` — add `PaymentDirection`
2. `backend/app/core/exceptions.py` — add `RateLimitExceededError`
3. `backend/app/core/exception_handlers.py` — map rate limit → 429
4. `backend/app/core/config.py` — public leads rate-limit settings
5. `backend/.gitignore` — ignore `tests/_c2b_tmp/`
6. `backend/app/modules/industry_templates/seed.py` — flexity_sales lead_sources + disposition custom fields (kindergarten block untouched)

## Post-copy test hygiene fixes (worktree only)

1. `backend/tests/test_import_summary_contract.py` — create real `ProviderCompany` + `Tenant` before audit write (SQLite FK to `tenants.id`).
2. `backend/tests/test_staging_write_import_runner.py` — flush `Branch` before setting `tenant.default_branch_id` (SQLite circular FK with branches/tenants).

## Counts (post-copy)

| Category | Count |
|---|---|
| Copied / modified paths in worktree status | ~101 |
| Skipped forbidden / out-of-scope (listed above) | 10+ explicit skip rules |
| New alembic revisions | **0** (reuse `0013_c1c_payment_direction`) |
| Alembic head unchanged | `0023_mkt_storage_profiles` |

## Execution status

- [x] Files copied
- [x] Tests run — focused **120 passed**; broader **77 passed**
- [x] `git diff --check` clean; secret scan — only false positive `hashed_password="not-used"` in tests
- [ ] Local commit(s) if green
