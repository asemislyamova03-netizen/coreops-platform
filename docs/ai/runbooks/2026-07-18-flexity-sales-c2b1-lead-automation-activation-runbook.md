# Flexity Sales — C2b1 Lead Automation Activation Runbook

**Date:** 2026-07-18
**Type:** ops runbook
**Status:** draft — local/staging only until production one-shot exists
**Branch:** `feature/consulting-lead-c2b1-auto-task`
**Scope:** enable `industry_config_json.consulting.lead_automation` + Process Overlay for sales intake
**Related plan:** `docs/ai/plans/2026-07-18-consulting-lead-to-client-c2b-automation-implementation-plan.md`

---

## Purpose

Operational checklist to activate C2b1 **ProcessRun → first-contact Task** automation for the Flexity sales tenant after code merge and migration `0024_task_run_automation_key`.

This runbook covers:

- local / staging activation (including optional bootstrap helper)
- production **BLOCKED** gate until a separate approved one-shot ops procedure exists
- config merge semantics for `lead_automation`
- ordered rollout and rollback

---

## Prerequisites

- Merged code includes C2b1 hook (`lead_automation.py`) wired after ProcessRun start.
- Migration `0024_task_run_automation_key` applied on target DB.
- Sales tenant exists (e.g. slug `flexity-sales`) with active `parties` + `crm` modules.
- Process Overlay catalog template `flexity_sales_intake` available (C2a).
- Operator has tenant admin / platform ops access.
- **Assignee UUID** resolved: active `UserTenantMembership` for the sales tenant (e.g. Asem) — record in ops notes; **never hardcode in code**.

---

## Schema note — composite FK (tasks ↔ process_runs)

Migration 0024 (post-review hardening) links automation tasks to runs with **tenant-safe** FK:

| Object | Name | Definition |
|--------|------|------------|
| FK | `fk_tasks_tenant_process_run` | `tasks(tenant_id, process_run_id)` → `process_runs(tenant_id, id)` ON DELETE RESTRICT |
| Unique (target) | `uq_process_runs_tenant_id_id` | `process_runs(tenant_id, id)` — required FK target (E1b) |
| CHECK | `ck_tasks_process_run_automation_key_pair` | both NULL or both NOT NULL |
| CHECK | non-empty `automation_key` when set | `length(trim(automation_key)) > 0` |
| Partial unique | `uq_tasks_tenant_process_run_automation_key` | `(tenant_id, process_run_id, automation_key)` WHERE both NOT NULL |

**Ops implication:** cross-tenant `process_run_id` references are rejected at DB level. Do not bypass with direct SQL.

---

## Config path and merge semantics

**Path:** `tenant_settings.industry_config_json.consulting.lead_automation`

### Required fields (when `enabled=true`)

| Field | Type | Default / cap |
|-------|------|----------------|
| `enabled` | bool | — |
| `default_assignee_user_id` | UUID string | required; must be active tenant member |
| `first_contact_sla_minutes` | int | default **240**; allowed **1..10080** (7 days) |
| `task_template_code` | str | default `consulting_first_contact`; used as `automation_key` |
| `create_activity` | bool | default `true` |

### Merge rules (do NOT wipe sibling keys)

1. **Always backup** full `industry_config_json` before write (see step 4 in activation order).
2. Read current JSON; shallow-merge at `consulting` level only:
   - preserve existing `consulting.*` siblings (e.g. other consulting flags)
   - set/update `consulting.lead_automation` object only
3. **Never** replace entire `industry_config_json` with only `lead_automation`.
4. **Never** replace entire `consulting` object if it contains other keys.
5. Prefer controlled service/API merge if available; if manual JSON edit — validate structure before commit.
6. Set `enabled=false` for rollback; do not delete the key unless restoring from backup.

Example merge target (illustrative):

```json
{
  "consulting": {
    "lead_automation": {
      "enabled": true,
      "default_assignee_user_id": "<ASSIGNEE_UUID>",
      "first_contact_sla_minutes": 240,
      "task_template_code": "consulting_first_contact",
      "create_activity": true
    }
  }
}
```

---

## Local / staging — Process Overlay bootstrap (non-production only)

`ProcessOverlayBootstrapService` is **disabled by default** and **forbidden in production** (`app_env=production` → hard deny).

### Temporary flag

```env
PROCESS_OVERLAY_BOOTSTRAP_ENABLED=true
```

Set only for the bootstrap window on **local or staging**. Revert to `false` immediately after successful bootstrap/validation.

### Bootstrap guardrails

- Allowed: `app_env` = `local`, `development`, `staging` (non-production).
- Forbidden: production — service raises `PermissionDeniedError`.
- Bootstrap does **not** write `lead_automation` config — overlay only.
- After bootstrap: validate graph, pipeline binding, published version fingerprint, optional activation.
- **Always** set `PROCESS_OVERLAY_BOOTSTRAP_ENABLED=false` after ops complete.

### Staging bootstrap checklist

1. Set `PROCESS_OVERLAY_BOOTSTRAP_ENABLED=true`; restart backend if env is loaded at startup.
2. Run bootstrap with explicit `tenant_id`, `pipeline_code` (`flexity_sales`), `actor_user_id`.
3. Validate: catalog entry exists; configuration created once; published immutable version; policy fingerprint stable on re-run.
4. Optionally `activate=True` for staging smoke only.
5. Set `PROCESS_OVERLAY_BOOTSTRAP_ENABLED=false`; restart if needed.
6. Proceed to activation order from step 3 onward.

---

## Production activation — **BLOCKED**

> **PRODUCTION ACTIVATION BLOCKED** until an approved **one-shot ops procedure** exists that uses normal `ProcessOverlayConfigurationService` / `ProcessOverlayPublicationService` / activation services — **not** `ProcessOverlayBootstrapService`.

| Rule | Status |
|------|--------|
| Use bootstrap service in production | **FORBIDDEN** |
| Direct SQL `UPDATE tenant_settings` / `industry_config_json` | **FORBIDDEN** |
| Direct SQL overlay/version mutation | **FORBIDDEN** |
| One-shot ops command/script via approved services | **NOT IMPLEMENTED** → **BLOCKED** |

### Production gate requirements (before unblock)

Separate HQ approval required for:

1. Named **rollback owner** and **backup owner**
2. Pre-deploy DB backup verified
3. Documented one-shot procedure (create/publish/activate via services)
4. Post-deploy internal CRM smoke signed off
5. Public inbound (`PUBLIC_LEADS_ENABLED`) enabled **last**, with separate approval

**Do not proceed with production C2b1 activation until this section is explicitly unblocked by HQ.**

---

## Activation order

Execute in order. Do not enable public inbound until internal path is verified.

| Step | Action | Notes |
|------|--------|-------|
| **1** | Deploy merged code + run migration `0024` | Alembic head includes C2b1; no down-migrate in prod without separate plan |
| **2** | **DB backup** | Full backup; record backup ID and timestamp |
| **3** | Determine UUIDs | `tenant_id`, sales `pipeline_id` (`flexity_sales`), **assignee `default_assignee_user_id`** |
| **4** | Backup `industry_config_json` | Export current row for tenant; store with backup ID |
| **5** | Create/publish immutable overlay version | Staging: bootstrap helper OK with flag. **Prod: one-shot via publication services only (BLOCKED until exists)** |
| **6** | Activate configuration/version | Overlay `activation_state=ACTIVE`; active definition version pinned |
| **7** | Write `lead_automation` config | Merge at `consulting.lead_automation`; do not wipe sibling keys; `enabled=true` only after steps 5–6 pass |
| **8** | Internal CRM smoke | Create WorkItem → start ProcessRun → verify Task «Связаться с лидом» + Activity; idempotent re-run |
| **9** | Public inbound enable **LAST** | `PUBLIC_LEADS_ENABLED=true` + env UUIDs per public leads runbook — only after step 8 |
| **10** | E2E public smoke | `POST /api/v1/public/leads` → Party + WorkItem + ProcessRun + Task |
| **11** | Monitoring | Logs, task creation rate, overlay errors, SLA due dates, duplicate-key violations |

---

## Internal CRM smoke (step 8 detail)

1. Create Party + WorkItem in sales pipeline (`flexity_sales`).
2. Ensure ProcessRun starts (overlay ACTIVE).
3. Confirm exactly one Task:
   - title «Связаться с лидом»
   - `automation_key` = `task_template_code` (default `consulting_first_contact`)
   - `assigned_to_user_id` = configured assignee UUID
   - `due_at` ≈ now + `first_contact_sla_minutes`
4. Confirm system Activity when `create_activity=true`.
5. Repeat start/idempotency: same ProcessRun must not create duplicate task (partial unique).
6. Complete task; new ProcessRun on same work item may create new task with same `automation_key`.

---

## Public inbound (step 9–10 — last)

Follow `docs/ai/plans/2026-06-24-public-inbound-leads-runbook.md`:

- `PUBLIC_LEADS_ENABLED=false` until internal smoke passes.
- Verify `PUBLIC_LEADS_TARGET_TENANT_ID`, pipeline/stage/user UUIDs.
- Enable only after C2b1 internal path confirmed.

---

## Rollback

Rollback order is **reverse of activation**. Do **not** auto-rollback migration `0024`.

| Order | Action |
|-------|--------|
| 1 | **Public inbound off first** — `PUBLIC_LEADS_ENABLED=false` |
| 2 | Disable automation — `lead_automation.enabled=false` **or** restore `industry_config_json` from step-4 backup |
| 3 | Deactivate overlay config for **new** runs (existing ACTIVE runs unaffected by deactivation policy) |
| 4 | **ACTIVE ProcessRuns** — handle separately: allow to complete or cancel; do not bulk-delete tasks |
| 5 | Migration | **Do NOT** run `alembic downgrade` unless separate approved schema rollback plan |

### Rollback owners

- Record **backup owner** and **rollback owner** in change ticket before production (when unblocked).

---

## Monitoring (step 11)

Watch after enablement:

- Application logs: `LeadAutomationConfigError`, `LeadAutomationConflictError`, overlay start failures
- DB: violations on `uq_tasks_tenant_process_run_automation_key`, `fk_tasks_tenant_process_run`
- CRM: task backlog for assignee; SLA breaches (`due_at` vs completion)
- Public leads: 4xx/5xx on `/api/v1/public/leads`; rate limits

---

## Approvals summary

| Environment | Bootstrap helper | `lead_automation` config | Public inbound |
|-------------|------------------|--------------------------|----------------|
| Local | Allowed with `PROCESS_OVERLAY_BOOTSTRAP_ENABLED=true` | Operator discretion | Optional |
| Staging | Allowed with flag; revert after | HQ/ops sign-off recommended | After internal smoke |
| Production | **FORBIDDEN** | **BLOCKED** until one-shot ops | **Last**, separate approval |

---

## Forbidden in this runbook

- Production bootstrap service usage
- Direct SQL updates to `tenant_settings`, overlay tables, or tasks
- Enabling public inbound before internal C2b1 smoke
- Leaving `PROCESS_OVERLAY_BOOTSTRAP_ENABLED=true` after staging bootstrap
- Auto-downgrading migration `0024` as part of config rollback

---

## References

- C2b1 plan: `docs/ai/plans/2026-07-18-consulting-lead-to-client-c2b-automation-implementation-plan.md`
- C2a plan: `docs/ai/plans/2026-07-18-consulting-lead-to-client-c2a-implementation-plan.md`
- Public leads: `docs/ai/plans/2026-06-24-public-inbound-leads-runbook.md`
- Bootstrap service: `backend/app/modules/process_overlay/service/bootstrap.py`
- Lead automation: `backend/app/modules/workflows/service/lead_automation.py`
