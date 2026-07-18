# Implementation Plan: Consulting Lead-to-Client Automation — C2b1

**Date:** 2026-07-18
**Type:** implementation plan
**Status:** **C2b1 APPROVED** — implement in local worktree only
**Project:** Flexity
**Category:** universal_module (workflows Task/Activity + ProcessRun automation hook)
**Truth baseline:** `origin/main` @ `e2d816d` (post PR #117 C2a)
**Branch / worktree:** `feature/consulting-lead-c2b1-auto-task` / `.worktrees/consulting-lead-c2b1-auto-task`
**Tenant:** automation via **tenant config only** (no hardcoded slug/email/UUID)
**Related:** C2a plan `docs/ai/plans/2026-07-18-consulting-lead-to-client-c2a-implementation-plan.md`

---

## HQ decisions (locked)

1. **C2b1 approved** for local implementation after C2a merge.
2. **C2b2** reminders / scheduler / escalation — **deferred** (out of scope).
3. Real assignee UUID (e.g. Asem) is needed **only** when configuring a tenant’s `industry_config_json` — **not** in code.
4. **Production config / activation** — **out of scope** (no push, no deploy, no prod enable).
5. Schema: nullable `process_run_id` + `automation_key` + CHECK pair + partial unique `(tenant_id, process_run_id, automation_key)`.
6. Composite FK `tasks(tenant_id, process_run_id) → process_runs(tenant_id, id)` **`fk_tasks_tenant_process_run`** ON DELETE RESTRICT.
7. `automation_key` VARCHAR(64), generic naming (not consulting-specific constraint).
8. Completed Task on **same** ProcessRun — **do not** recreate; **new** ProcessRun may reuse same `automation_key`.
9. Hook is a **universal ProcessRun automation hook**, enabled only via tenant config.

---

## Goal

After Active `ProcessRun` starts (C2a path or CRM `WorkflowService` create):

1. Read `TenantSettings.industry_config_json.consulting.lead_automation`.
2. Missing config / `enabled=false` → **no-op**.
3. `enabled=true` → validate; create one Task «Связаться с лидом» + one system Activity in the **same outer transaction**.
4. Idempotent under concurrency via partial unique + nested transaction.

---

## Config schema

**Path:** `industry_config_json.consulting.lead_automation`

| Field | Type | Default |
|-------|------|---------|
| `enabled` | bool | — |
| `default_assignee_user_id` | UUID | required when enabled |
| `first_contact_sla_minutes` | int | `240` (allowed **1..10080**) |
| `task_template_code` | str | `consulting_first_contact` (used as `automation_key`) |
| `create_activity` | bool | `true` |

**Semantics:** enabled + invalid/cross-tenant/inactive assignee → typed fail-closed; no inner commits.

---

## Migration 0024 (REQUIRED)

- `down_revision`: `0023_mkt_storage_profiles`
- `revision`: `0024_task_run_automation_key`
- Columns on `tasks`: `process_run_id` UUID NULL, `automation_key` VARCHAR(64) NULL
- CHECK pair: both NULL or both NOT NULL (`ck_tasks_process_run_automation_key_pair`)
- Partial unique `(tenant_id, process_run_id, automation_key)` with `postgresql_where` + `sqlite_where`
- Index `ix_tasks_process_run_id`
- up/down/up test

**Amendment note:** post-review hardening is applied **in-place to 0024** (unpublished branch revision). No separate `0025` migration — safe because 0024 has not shipped to production.

### Post-review hardening (0024 + runtime validation)

| Item | Detail |
|------|--------|
| Composite FK | `fk_tasks_tenant_process_run`: `tasks(tenant_id, process_run_id)` → `process_runs(tenant_id, id)` ON DELETE RESTRICT |
| FK target unique | `uq_process_runs_tenant_id_id` on `process_runs(tenant_id, id)` (E1b; required for composite FK) |
| Non-empty key CHECK | when `automation_key` IS NOT NULL → `length(trim(automation_key)) > 0` |
| SLA cap | `first_contact_sla_minutes` validated **1..10080** in `load_lead_automation_config` (default 240) |
| Production activation | **BLOCKED** — no bootstrap in prod; requires separate approved one-shot ops via configuration/publication/activation services (see activation runbook) |

Replaces earlier single-column FK `tasks.process_run_id → process_runs.id` in unpublished 0024 draft.

---

## Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | universal_module |
| Risk | medium |
| Forbidden | C2b2; notifications; API/UI; C2c/C2d; consulting_basic runtime; push/deploy; prod config; hardcoded Asem UUID |

---

## Files (implementation)

- `backend/alembic/versions/20260718_0024_task_run_automation_key.py`
- `backend/app/modules/workflows/models.py` (Task columns + constraints)
- New: `backend/app/modules/workflows/service/lead_automation.py` (or process_overlay hook module)
- Wire after ProcessRun start (`ProcessOverlayRunService.start_run` and/or `_maybe_auto_start_process_run` path — prefer single post-start hook)
- `backend/tests/test_migration_0024_task_run_automation_key.py`
- `backend/tests/test_lead_automation_c2b1.py`

---

## Exclusions

C2b2 scheduler/reminders; email/Telegram/WhatsApp; API/UI; documents/finance; social connectors; consulting_basic seed; production tenant config; deploy.

---

## Activation runbook

Ops steps (local/staging bootstrap, production **BLOCKED** gate, rollback order):
`docs/ai/runbooks/2026-07-18-flexity-sales-c2b1-lead-automation-activation-runbook.md`

---

## Approval

**C2b1:** APPROVED for local code in this worktree.
**Push / merge / production activation:** NOT approved.
**Production C2b1 enablement:** **BLOCKED** until approved one-shot ops procedure exists (no bootstrap in production).
