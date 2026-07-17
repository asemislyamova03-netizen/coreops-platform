# Implementation Plan: Process Overlay E1c — Transition Enforcement

**Date:** 2026-07-17 (corrected 2026-07-18)  
**Type:** implementation plan  
**Project:** Flexity  
**Category:** platform_core (thin Process Overlay)  
**Studied baseline:** `origin/main` @ `abbde60` (post E1b2 + Booking + C1c; merge PR #113)  
**Worktree:** `.worktrees/process-overlay-e1c-transition-enforcement`  
**Branch:** `feature/process-overlay-e1c-transition-enforcement`  
**Parent architecture:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1-architecture-plan.md`  
**Parent E1a / E1b / E1b2 plans:** same `docs/ai/plans/` tree  
**Status:** **APPROVED** (HQ locked decisions below) — local implementation allowed; **no push/merge/deploy**  
**Depends on:** E1a (`0019`) + E1b (`0020`) + E1b2 auto-start already on `origin/main`  
**Proposed migration:** **none**  
**Git:** two local commits (plan, then code); **no push**

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | platform_core |
| Risk level | medium (CRM stage-change paths gain fail-closed overlay gate when ACTIVE ProcessRun exists) |
| Intended scope | single shared transition guard; wire into `move_stage`, `update_work_item` (stage change), `close_work_item`, `reopen_work_item`; pinned policy edges only; applied audit once; tests |
| Forbidden scope | dirty root WIP; migrations; API/UI/OpenAPI; required fields/tasks/documents/approvals; auto-actions / ProcessRun auto-completion; ModuleGuard disable-block; new dependencies; push/merge/deploy |
| Required plan | this document (corrected to locked decisions) |

---

## Goal

Deliver **E1c transition enforcement**: when a WorkItem has an **ACTIVE** `ProcessRun`, any CRM stage **transition** must pass a **single** server-side guard that evaluates **allowed edges only** against the run’s **pinned** `ProcessDefinitionVersion.policy_snapshot_json`.

- **ACTIVE ProcessRun** → enforce transitions from pinned policy (fail-closed on invalid/missing policy or stages).  
- **No ACTIVE / COMPLETED / CANCELLED only** → prior CRM behavior **unchanged** (no block).  
- **Four writers, one guard, no bypass:** `move_stage`, `update_work_item` (when stage changes), `close_work_item`, `reopen_work_item`.  
- E1c does **not** evaluate required fields / roles / tasks / documents / approvals.  
- ProcessRun auto-completion is **out** (E1c2 later).

---

## LOCKED decisions (HQ — exact)

These supersede any earlier “optional / recommend” wording in draft plans.

| ID | Decision |
|----|----------|
| L1 | Enforce **only** for **ACTIVE** ProcessRun |
| L2 | Policy from **pinned** ProcessRun version (`policy_snapshot_json` / pinned `process_definition_version_id`) — **never** current active config pointer |
| L3 | Guard on: `move_stage`, `update_work_item` (stage change), `close_work_item`, `reopen_work_item` — **single shared guard, no bypass** |
| L4 | No ACTIVE run / COMPLETED / CANCELLED → **legacy CRM** (no overlay block) |
| L5 | Deactivated configuration + still-ACTIVE run → enforcement **CONTINUES** (pin freeze) |
| L6 | CRM tenant/pipeline validation **MUST run BEFORE** overlay policy |
| L7 | Same-stage update is **NOT** a transition (no applied audit; no deny) |
| L8 | Invalid/missing policy or current/target stage → **fail-closed** |
| L9 | WorkItem **and** ACTIVE ProcessRun locked with **`SELECT … FOR UPDATE`** |
| L10 | Existing CRM Activity **exactly once** (keep existing side-effects; **no** duplicate Activity for overlay) |
| L11 | `process_transition.applied` audit **exactly once** on successful **applied** transition |
| L12 | Denied transition → **typed error**; **NO** separate persisted deny audit |
| L13 | `current_stage_code` synced **ONLY** after successful applied transition |
| L14 | **NO** auto-completion of ProcessRun |

---

## Non-goals (explicit)

| Item | Deferred to |
|------|-------------|
| Evaluate `conditions.required_*` / `requires_approval` | later evidence / approvals slices |
| Automatic stage transitions / AI actions | out |
| Auto-complete / auto-cancel ProcessRun on terminal CRM stages | **E1c2** |
| HTTP routes / OpenAPI / UI for overlay | later |
| BPMN / visual editor / scripts | out |
| ModuleGuard “cannot disable while policy requires module” | later |
| New Alembic revision / schema change | out |
| Changing E1b2 auto-start rules | out |
| Dirty root WIP / marketing branch | forbidden |
| Persisted deny audit rows | out (typed error only) |

---

## Current state findings (from `origin/main` @ `abbde60`)

### What already exists

| Area | Finding |
|------|---------|
| Immutable version + policy snapshot | `ProcessDefinitionVersion.policy_snapshot_json` |
| Policy schema v1 | `parse_policy_snapshot`; transitions with conditions (unused at runtime) |
| Seed edges | `new_lead→contacted→diagnosis→accepted\|rejected` |
| ProcessRun pin | pinned at `start_run`; never updated |
| Active run lookup | `get_active_run_for_work_item` |
| Auto-start | E1b2 `_maybe_auto_start_process_run` on create |
| CRM writers | `move_stage` / `update_work_item` / `close_work_item` / `reopen_work_item` — no overlay check |
| Anti-enforcement tests | E1b T14 + E1b2 A10 must be rewritten for E1c |

### Gaps for E1c

1. No transition evaluation service / guard.  
2. Four stage writers ignore ACTIVE ProcessRun.  
3. No `process_transition.applied` audit.  
4. No `SELECT FOR UPDATE` helpers for WorkItem + ACTIVE run on these paths.  
5. No `update_run_current_stage_code` helper.  
6. T14 / A10 encode “no enforcement”.

---

## Design (aligned to locked decisions)

### D1 — Enforce only when ACTIVE ProcessRun exists (L1, L4, L5)

| WorkItem state | Stage-change behavior |
|----------------|----------------------|
| No ProcessRun | Legacy CRM |
| Only COMPLETED / CANCELLED | Legacy CRM |
| One ACTIVE ProcessRun | Guard evaluates pinned policy edges |

Config `activation_state` is **not** re-checked: deactivated config + still-ACTIVE run → enforcement **continues**.

### D2 — Policy source = pinned version only (L2)

Always load `run.process_definition_version_id` → immutable `policy_snapshot_json`.  
Never live `config.active_definition_version_id`, template blueprint, or request payload.

### D3 — Single shared guard, four callers (L3)

```text
ProcessOverlayTransitionGuard.apply_or_bypass(
  tenant_id, work_item, *, from_stage_code, to_stage_code, actor_user_id, via
) -> TransitionGuardResult
```

**Callers (all required):**

1. `WorkflowService.move_stage`  
2. `WorkflowService.update_work_item` — only when `payload.stage_id` differs from current  
3. `WorkflowService.close_work_item` — target `rejected`  
4. `WorkflowService.reopen_work_item` — target `new_lead`  

### D4 — Edge-only evaluation

Parse pinned snapshot; allow iff `(from, to)` ∈ transitions; **ignore** all `conditions.*`.

### D5 — Same-stage is not a transition (L7)

`from_stage_code == to_stage_code` → skip overlay transition (no applied audit, no deny, no `current_stage_code` write). CRM may still run its existing path for non-stage fields; for same-stage `move_stage`, prefer no-op return without duplicate Activity noise when stage unchanged.

### D6 — Fail-closed (L8)

Deny (typed error, no stage mutation) when: missing pinned version, tenant/config mismatch, parse failure, unresolved from/to stage codes, edge missing, integrity mismatch (run config pipeline vs work item — defense in depth).

### D7 — CRM validation before overlay (L6)

Order inside each writer:

1. Load/lock WorkItem (`FOR UPDATE`).  
2. Existing CRM tenant/pipeline/stage checks (`ConflictError` / `NotFoundError`).  
3. Resolve from/to stage codes from DB.  
4. Overlay guard (lock ACTIVE run if any; evaluate).  
5. Apply CRM mutation + side-effects.  
6. If applied under enforcement: sync `current_stage_code` + `process_transition.applied` once.

### D8 — close / reopen through same guard (L3)

Required. Seed has `diagnosis→rejected` but **no** reopen edge → ACTIVE reopen fails closed (operators cancel/complete run first, or use WorkItems without ACTIVE run).

### D9 — No auto-complete (L14)

Allowed transition into terminal stages leaves ProcessRun **ACTIVE**.

### D10 — Sync `current_stage_code` only after success (L13)

Narrow repository helper; never mutate version pin.

### D11 — Audit: applied only (L11, L12)

| Event | When | Persisted? |
|-------|------|------------|
| `process_transition.applied` | After successful applied transition under ACTIVE run | **Yes, exactly once** |
| Deny | Typed `ProcessTransitionDeniedError` | **No** deny audit row |

Keys for applied: `work_item_id`, `process_run_id`, `definition_version_id`, `from_stage_code`, `to_stage_code`, `via`.

### D12 — No migration / no API / no UI

### D13 — Concurrency locks (L9)

Required:

1. Lock **WorkItem** with `SELECT … FOR UPDATE` before stage mutation.  
2. If ACTIVE run exists, lock that **ProcessRun** with `SELECT … FOR UPDATE` before evaluate/apply.  

SQLite may no-op `FOR UPDATE`; PostgreSQL enforces. Prefer ephemeral PostgreSQL for concurrency/race tests.

### D14 — Activity exactly once (L10)

Keep existing CRM `add_activity` side-effects on `move_stage` / `close` / `reopen`. Overlay must **not** insert a second Activity.

---

## Package layout

```text
process_overlay/
├── exceptions.py              # + ProcessTransitionDeniedError
├── constants.py               # EVENT_PROCESS_TRANSITION_APPLIED
├── repository.py              # + lock helpers + update_run_current_stage_code
└── service/
    └── transitions.py         # NEW: ProcessOverlayTransitionGuard
workflows/
├── repository.py              # + get_work_item_for_update
└── service.py                 # wire four paths (CRM checks → guard → mutate)
```

### Guard algorithm (pseudocode)

```text
def evaluate_and_prepare(...):
    # Caller already locked WorkItem and ran CRM pipeline checks.
    if from_stage_code == to_stage_code:
        return TransitionGuardResult(enforced=False, noop=True)  # not a transition

    run = repo.get_active_run_for_work_item_for_update(tenant_id, work_item.id)
    if run is None:
        return TransitionGuardResult(enforced=False)  # legacy CRM

    version = repo.get_definition_version(tenant_id, run.process_definition_version_id)
    if version is None or mismatches: raise ProcessTransitionDeniedError  # fail-closed, no audit

    policy = parse_policy_snapshot(...)  # on failure → ProcessTransitionDeniedError

    if (from, to) not in edges:
        raise ProcessTransitionDeniedError(...)  # no deny audit

    return TransitionGuardResult(enforced=True, run=run, version=version)

# After CRM mutation succeeds:
#   update_run_current_stage_code(run, to)
#   audit process_transition.applied exactly once
```

---

## Error semantics

| Case | Guard? | Stage changes? | Audit |
|------|--------|----------------|-------|
| No ACTIVE run | Skip | Yes (legacy) | none overlay |
| ACTIVE + allowed edge | Enforce | Yes | `process_transition.applied` once |
| ACTIVE + same stage | Not a transition | No preferred | none |
| ACTIVE + missing edge / bad policy / missing stage | Deny typed | No | **none** (no deny audit) |
| Stage not on pipeline | CRM Conflict first | No | none |
| Non-stage `update_work_item` fields | N/A | N/A | unchanged |

`ProcessTransitionDeniedError` subclasses `ConflictError` (HTTP 409 via existing handler).

---

## Test plan

New: `backend/tests/test_process_overlay_e1c_transition_enforcement.py`  
Rewrite: E1b T14, E1b2 A10.

| ID | Scenario | Assertion |
|----|----------|-----------|
| C1 | No run: `move_stage` | Legacy success |
| C2 | No run: `update_work_item(stage)` | Legacy success |
| C3 | ACTIVE: `new_lead→contacted` via `move_stage` | Allowed; stage changed; `current_stage_code` synced; applied audit once; Activity once |
| C4 | ACTIVE: `new_lead→accepted` | Denied typed; stage unchanged; **no** deny audit; run ACTIVE |
| C5 | ACTIVE: `new_lead→proposal_prepared` (or non-edge) | Denied |
| C6 | ACTIVE: same allow/deny via `update_work_item` | Shared guard |
| C7 | ACTIVE: same-stage | Not a transition; no applied audit |
| C8 | Corrupt pinned policy | Fail-closed deny; no deny audit |
| C9 | Tenant isolation | Tenant B cannot move A’s item |
| C10 | Pipeline stage mismatch | CRM Conflict before overlay |
| C11 | Pin freeze after active version pointer moves | Old edges still apply |
| C12 | COMPLETED/CANCELLED only | Legacy CRM |
| C13 | Conditions ignored | Edge with `required_roles` still allows |
| C14 | close/reopen with ACTIVE | Shared guard; reopen denied without edge |
| C15 | Source contract | Four writers reference guard |
| C16 | No auto-complete | `diagnosis→accepted` leaves run ACTIVE |
| C17 | E1a/E1b/E1b2 regression | Suites green after T14/A10 rewrite |
| + | Deactivated config + ACTIVE run | Enforcement continues |
| + | Race / FOR UPDATE helpers present | Contract + PG race if available |
| + | Audit regression | Exactly one applied; no duplicate Activity |

### Commands

```bash
cd backend
python -m pytest tests/test_process_overlay_e1c_transition_enforcement.py -q
python -m pytest tests/test_process_overlay_e1b_runs.py tests/test_process_overlay_e1b2_auto_start.py -q
python -m pytest tests/test_process_overlay_e1a_models.py tests/test_process_overlay_e1a_publication.py -q
python -m pytest tests/ -q   # prefer ephemeral PostgreSQL if shared DB dirty
python -m compileall app/modules/workflows app/modules/process_overlay
# alembic heads must remain 0023_mkt_storage_profiles only
```

---

## Proposed file touch list

### Create

| Path | Purpose |
|------|---------|
| `backend/app/modules/process_overlay/service/transitions.py` | Shared guard |
| `backend/tests/test_process_overlay_e1c_transition_enforcement.py` | C1–C17 + extras |

### Modify

| Path | Change |
|------|--------|
| `backend/app/modules/workflows/service.py` | Four writers: lock → CRM checks → guard → mutate |
| `backend/app/modules/workflows/repository.py` | `get_work_item_for_update` |
| `backend/app/modules/process_overlay/exceptions.py` | `ProcessTransitionDeniedError` |
| `backend/app/modules/process_overlay/repository.py` | Active-run FOR UPDATE + `update_run_current_stage_code` |
| `backend/app/modules/process_overlay/constants.py` | Applied event constant |
| `backend/app/modules/process_overlay/service/__init__.py` | Export guard |
| `backend/tests/test_process_overlay_e1b_runs.py` | Rewrite T14 |
| `backend/tests/test_process_overlay_e1b2_auto_start.py` | Rewrite A10 |

### Intentionally NOT touched

Dirty root; Alembic; routes/OpenAPI/UI; `runs.py` lifecycle; `policy_schema.py` / `seed.py`; marketing; auth/tenant/billing.

---

## Implementation steps

1. Plan commit (this file).  
2. Exceptions + constants.  
3. Repository lock / stage-code helpers.  
4. `transitions.py` guard (edge-only, applied audit, fail-closed, no deny audit).  
5. Wire four WorkflowService paths (CRM before overlay).  
6. E1c tests + rewrite T14/A10.  
7. Green checks → code commit.  
8. Stop — no E1c2 / evidence / API.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Bypass via close/reopen | Locked L3 + C14 |
| Scope creep into conditions | Non-goals + C13 |
| Accidental auto-complete | L14 + C16 |
| Duplicate Activity / audit | L10/L11 tests |
| Dirty-root contamination | Clean worktree only |
| Shared DB pollution | Ephemeral PostgreSQL for full suite |

---

## Rollback

Revert the code commit (and plan commit if needed). No schema. Operational escape: `cancel_run` / `complete_run` removes ACTIVE enforcement.

---

## Separation matrix

| Concern | E1a | E1b | E1b2 | **E1c** | E1c2 |
|---------|-----|-----|------|---------|------|
| Config / publish / versions | ✅ | reuse | reuse | reuse | reuse |
| ProcessRun lifecycle | — | ✅ | reuse | reuse | may auto-complete |
| Auto-start on create | — | — | ✅ | — | — |
| Edge allow/deny on stage change | — | — | — | ✅ | — |
| Shared guard on four writers | — | — | — | ✅ | — |
| Applied audit only | — | — | — | ✅ | — |
| Evidence / approvals | schema | — | — | ❌ | later |
| Auto-complete on terminal | — | — | — | ❌ | ✅ |

---

## GO / NO-GO

**GO for local implementation** under locked L1–L14, clean worktree, no push/merge/deploy, Alembic head stays `0023_mkt_storage_profiles`.

**Approval Gate:** **APPROVED** (this corrected plan).

---

## Finish block (plan correction)

1. **Files changed:** this plan (corrected to locked decisions).  
2. **Files intentionally not touched:** application code (until code commit); dirty root; Alembic; remote.  
3. **Tests/checks:** documentation-only for plan commit.  
4. **Risks:** see above.  
5. **Next safe step:** implement guard + wiring + tests; local code commit after green checks.  
6. **Handoff:** after code verification.
