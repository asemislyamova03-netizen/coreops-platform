# Implementation Plan: Flexity Backend PR CI

**Date:** 2026-07-17
**Type:** implementation plan (approved Task 1 — LOCAL ONLY)
**Project:** Flexity
**Category:** platform_core (CI / developer workflow)
**Status:** approved for local implementation on `chore/backend-pr-ci`
**Base:** `origin/main` @ merge of process-overlay E1b (#106)
**Worktree:** `.worktrees/backend-pr-ci`
**Forbidden:** push, merge, deploy, production secrets, edits to publish workflows, dirty root branch `feature/marketing-m8-publish-bridge`

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | platform_core |
| Risk level | low (CI-only; no runtime product code) |
| Intended scope | `.github/workflows/backend-pr-ci.yml`, this plan doc |
| Forbidden scope | `instagram-publish.yml`, `telegram-publish.yml`, production `.env`/secrets, deploy jobs, dirty root worktree |
| Required plan | this document |

---

## Goal

Add a **minimal GitHub Actions pull_request CI** for backend PRs targeting `main`:

1. Install backend deps from `backend/pyproject.toml` (`pip install -e ".[dev]"`).
2. Run against an ephemeral **PostgreSQL service container** and dedicated DB `coreops_pr_ci` (localhost credentials in workflow only).
3. Fail on **multiple Alembic heads**.
4. Apply `alembic upgrade head` on the CI DB.
5. Run a **small green regression** pytest set (process overlay E1a/E1b + workflows + migration 0019/0020 + tenants).
6. Use pip dependency caching and concurrency cancel-in-progress.
7. **No** publish/deploy jobs and **no** production secrets.

---

## Current backend test setup (main)

- Dependencies: `backend/pyproject.toml` (Hatchling; optional `dev` extras: pytest, httpx, pytest-asyncio). No `requirements.txt` / Pipfile.
- Unit/API tests: `backend/tests/conftest.py` uses **in-memory SQLite** (`TEST_DATABASE_URL = "sqlite://"`) + `Base.metadata.create_all`.
- Alembic: `backend/alembic.ini` placeholder URL; real URL from `app.core.config.get_settings().database_url` (`DATABASE_URL` env, default `postgresql+psycopg://coreops:coreops@localhost:5432/coreops`).
- Migration / some overlay run tests: require reachable Postgres via `DATABASE_URL` (`postgres_required` skipif).
- Existing workflows (do **not** modify): `.github/workflows/instagram-publish.yml`, `telegram-publish.yml` (publish-only).

---

## Exact files

| Path | Action |
|------|--------|
| `.github/workflows/backend-pr-ci.yml` | **create** — PR CI only |
| `docs/ai/plans/2026-07-17-flexity-backend-pr-ci-implementation-plan.md` | **create** — this plan |

Tiny test/code fixes only if required to keep the chosen pytest set green on CI.

---

## Workflow design

- `on.pull_request.branches: [main]`
- `concurrency.group` + `cancel-in-progress: true`
- `permissions.contents: read`
- Service: `postgres:16-alpine` with user/password/db `coreops` / `coreops` / `coreops_pr_ci`
- Env: `DATABASE_URL=postgresql+psycopg://coreops:coreops@localhost:5432/coreops_pr_ci`
- Steps: checkout → setup-python 3.12 + pip cache on `backend/pyproject.toml` → `pip install -e ".[dev]"` → alembic single-head → `alembic upgrade head` → minimal pytest list above
- Explicitly **omitted**: publish, deploy, SSH, production secret refs

### Minimal pytest set

```
tests/test_process_overlay_e1a_models.py
tests/test_process_overlay_e1a_publication.py
tests/test_process_overlay_e1b_models.py
tests/test_process_overlay_e1b_runs.py
tests/test_workflows.py
tests/test_migration_0019_process_overlay_e1a.py
tests/test_migration_0020_process_overlay_e1b.py
tests/test_tenants.py
```

Rationale: covers recent main head (E1a/E1b), CRM workflows, tenants seed path, and Alembic chain integrity — small enough to stay green.

---

## Local validation (this worktree)

1. Ephemeral Postgres on high port (e.g. 55442) with DB `coreops_pr_ci` — never touch production `coreops` DB on :5432.
2. YAML parse (PyYAML / `yaml.safe_load`) and `actionlint` if available.
3. Dry-run same commands as CI with `DATABASE_URL` pointing at ephemeral DB.
4. Scoped commit on `chore/backend-pr-ci` only; **no push**.

---

## Rollback

Delete the workflow file and this plan on the branch, or abandon the branch. No DB/schema/product rollback needed.

---

## Success criteria

- [x] Worktree from `origin/main`, branch `chore/backend-pr-ci`
- [x] Workflow file present and valid YAML
- [x] Plan doc present
- [x] Local dry-run of alembic head check + upgrade + pytest set passes against ephemeral Postgres
- [x] Local commit with message `chore(ci): add backend pull_request CI workflow`
- [x] Dirty root repo untouched (staged = 0); no push
