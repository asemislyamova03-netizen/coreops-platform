# Implementation Plan: Process Overlay E1b2 — Opt-in Auto-Start on WorkItem Create

**Date:** 2026-07-17  
**Type:** implementation plan (documentation only — **no application code in this step**)  
**Project:** Flexity  
**Category:** platform_core (thin Process Overlay)  
**Studied baseline:** `origin/main` @ `76773ec` (post E1b + later merges incl. marketing M8 PR #109)  
**Worktree for this plan file:** `.worktrees/process-overlay-e1b2-plan` (branch `docs/process-overlay-e1b2-plan`)  
**Parent architecture:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1-architecture-plan.md`  
**Parent E1a plan:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1a-implementation-plan.md`  
**Parent E1b plan:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1b-implementation-plan.md` (E1b2 sketched as future; this document is the Approval Gate for that slice)  
**Status:** waiting for **Approval Gate before code**  
**Depends on:** E1a (`0019_process_overlay_e1a`) + E1b (`0020_process_overlay_e1b`) already on `origin/main`  
**Proposed migration:** **none** (reuse existing `process_runs` + E1b `start_run`)  
**Git:** plan written as **untracked** local file in clean worktree; **no commit required**; **no push**

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | platform_core |
| Risk level | medium (CRM create path gains optional overlay side-effect; fail-closed when ACTIVE) |
| Intended scope | thin opt-in hook in `WorkflowService.create_work_item` → existing `ProcessOverlayRunService.start_run`; repo lookup by pipeline; tests; **no** new tables |
| Forbidden scope | dirty root WIP; `move_stage` / `update_work_item` enforcement; required fields/tasks/documents/approvals; automatic transitions; API/UI; E1c; deploy; push/merge; new dependencies; schema migrations unless HQ later expands scope |
| Required plan | this document |

---

## Goal

Deliver **E1b2 opt-in auto-start**: when CRM creates a WorkItem on a pipeline that has an **ACTIVE** `TenantProcessConfiguration` with an `active_definition_version_id`, automatically create a `ProcessRun` (pinned version + audit) in the **same DB transaction** as the WorkItem — by calling existing `ProcessOverlayRunService.start_run`, not by duplicating run logic.

Empty / missing / inactive overlay must leave **current CRM create behavior unchanged**.

---

## Non-goals (explicit)

| Item | Deferred to |
|------|-------------|
| `move_stage` / `update_work_item` policy enforcement | **E1c** |
| Required fields / tasks / documents / approvals evaluation | **E1c** |
| Automatic transitions / auto-complete Run from CRM stages | **E1c** |
| HTTP routes / OpenAPI / UI for overlay | later |
| Retrospective Runs for pre-existing WorkItems | out |
| New Alembic revision / schema change | out (unless unexpected gap found during impl — stop and revise plan) |
| Separate product feature-flag beyond config `activation_state` | out for E1b2 (ACTIVE config **is** the opt-in) |
| Stage-code filter (e.g. only `new_lead`) | **out of default E1b2** — see Design Decision D3 |
| Changing `complete_run` / `cancel_run` contracts | out |
| Industry template auto-provision of configs | out |

---

## Current state findings (from `origin/main` @ `76773ec`)

### What already exists (E1a + E1b)

| Area | Path | Finding |
|------|------|---------|
| Config + unique per pipeline | `backend/app/modules/process_overlay/models.py` (`TenantProcessConfiguration`) | `uq_tenant_process_config_tenant_pipeline` on `(tenant_id, pipeline_id)` — at most one config per pipeline |
| Activation requires version | `backend/app/modules/process_overlay/service/configuration.py` (`activate_configuration`) | Cannot activate without `active_definition_version_id` |
| Explicit run lifecycle | `backend/app/modules/process_overlay/service/runs.py` | `start_run` / `complete_run` / `cancel_run`; pins `config.active_definition_version_id`; audit `process_run.started`; race → `ProcessRunConflictError` (service check + `IntegrityError` on partial unique) |
| Active run uniqueness | `ProcessRun` model + migration `0020` | Partial unique index `uq_process_run_one_active_per_work_item` where `run_state = 'active'` |
| Run repo helpers | `backend/app/modules/process_overlay/repository.py` | `get_active_run_for_work_item`, `create_run`, `get_run`; **no** `get_configuration_by_pipeline` yet |
| CRM create | `backend/app/modules/workflows/service.py` (`create_work_item` ~L81–134) | Creates WorkItem + participants + custom fields; `flush`; **no** overlay import/call |
| CRM create commit boundary | `backend/app/modules/workflows/routes.py` (~L99–107) | Service call then `db.commit()` — entire service work is one outer transaction |
| E1b anti-hook test | `backend/tests/test_process_overlay_e1b_runs.py` (`test_create_work_item_creates_zero_runs_even_with_active_config`) | Asserts **zero** runs + source does not contain `start_run` / `ProcessOverlayRunService` — **must be rewritten** for E1b2 |
| Architecture intent | architecture plan §7 / §15 / §16 | Auto-start when config active was originally part of “E1b”; E1b plan **narrowed** explicit-only start and deferred auto-start to **E1b2** |

### Gaps for E1b2

1. No pipeline-scoped config lookup helper (`get_configuration_by_pipeline`).
2. `WorkflowService.create_work_item` does not call overlay.
3. E1b tests explicitly forbid the hook (T13) — expected to invert for ACTIVE path after E1b2.

### Intentionally unchanged today

- `move_stage` / `update_work_item` ignore ProcessRun (legacy CRM).
- Explicit `start_run` remains valid for manual/internal use (e.g. after cancel, or if create skipped).

---

## Design decisions (propose for Approval Gate)

### D1 — Opt-in signal = ACTIVE tenant config for that pipeline

Auto-start fires **only if** there exists `TenantProcessConfiguration` for `(tenant_id, work_item.pipeline_id)` with:

- `activation_state == ACTIVE`, **and**
- `active_definition_version_id IS NOT NULL` (defense in depth; activation already enforces this).

Otherwise: **no-op** (WorkItem create succeeds exactly as today).

No separate env flag / ModuleGuard gate in E1b2.

### D2 — Reuse `start_run` (do not fork pin/audit/race logic)

After WorkItem is persisted (`flush` so `item.id` exists), call:

```text
ProcessOverlayRunService(db).start_run(
  tenant_id=self.tenant_id,
  work_item_id=item.id,
  configuration_id=config.id,
  actor_user_id=user.id,
)
```

Benefits: version pinning, pipeline match checks, tenant isolation, conflict + IntegrityError mapping, audit — all stay in one place.

### D3 — No stage-code filter in default E1b2

Architecture text mentioned `new_lead` as an example start rule. **E1b2 default:** auto-start on **any** successful `create_work_item` for that pipeline when config is ACTIVE (payload may set `stage_id`; default remains first stage).

Rationale: user scope for this plan does not require stage filtering; keeps hook tiny. If HQ requires `new_lead`-only, treat as a **plan amendment** before code (small `if stage.code != "new_lead": return`).

### D4 — Fail-closed when auto-start is attempted

| Situation | Behavior |
|-----------|----------|
| No config for pipeline | Skip — WorkItem created |
| Config INACTIVE | Skip — WorkItem created |
| Config ACTIVE + version set | Call `start_run`; on success flush; route commits WorkItem+Run+audit together |
| Config ACTIVE but `start_run` raises (`ValidationError`, `ActivationError`, `ConflictError`, `NotFoundError`, isolation, etc.) | **Propagate** — outer transaction not committed → **WorkItem create fails** (no orphan WorkItem without required Run) |

Rationale: tenant opted in by activating overlay; partial success (WorkItem without Run) would break E1c assumptions later and is harder to repair.

**Exception note:** true concurrent double-ACTIVE on the **same** new WorkItem is vanishingly rare at create time; if it happens, fail-closed is still correct.

### D5 — One transaction = same Session, no intermediate commit

- Do **not** `commit()` inside service.
- Do **not** start a separate connection for overlay.
- Rely on route-level `db.commit()` after successful `create_work_item`.
- `start_run` already uses `begin_nested()` only around run insert+audit for IntegrityError mapping; nested savepoint still participates in the outer transaction.

### D6 — Explicit `start_run` remains available

E1b2 does not remove manual `start_run`. After cancel/complete, a new ACTIVE run may still be started explicitly (E1b T16 semantics). Auto-start only applies at **create**.

### D7 — No API / response shape change required

`WorkItemResponse` unchanged. Run is discoverable later via overlay services/tests; exposing run id on create is **out of scope** for E1b2.

---

## Detailed design

### Lookup helper (repository)

Add to `ProcessOverlayRepository`:

```text
get_configuration_by_pipeline(tenant_id, pipeline_id) -> TenantProcessConfiguration | None
```

- Filter: `tenant_id` + `pipeline_id` (unique).
- Tenant isolation: never query without `tenant_id`.

Optional thin helper on run or configuration service:

```text
maybe_get_active_configuration_for_pipeline(tenant_id, pipeline_id) -> config | None
```

Returns config only when `activation_state == ACTIVE` (and optionally asserts version present); else `None` for skip.

### Hook placement

Inside `WorkflowService.create_work_item`, **after**:

1. WorkItem insert  
2. participants  
3. custom field upserts  
4. `self.db.flush()` (WorkItem id stable)

**before** `return self.get_work_item(item.id)`:

```text
_maybe_auto_start_process_run(user=user, work_item=item)
```

Private method keeps create path readable and testable.

### Pseudocode

```text
def _maybe_auto_start_process_run(self, *, user, work_item):
    config = ProcessOverlayRepository(self.db).get_configuration_by_pipeline(
        self.tenant_id, work_item.pipeline_id
    )
    if config is None:
        return
    if config.activation_state != ACTIVE:
        return
    if config.active_definition_version_id is None:
        # Defensive: ACTIVE without version should not occur after activate_configuration.
        # Fail closed via start_run validation rather than silent skip.
        pass  # fall through to start_run

    ProcessOverlayRunService(self.db).start_run(
        tenant_id=self.tenant_id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=user.id,
    )
```

Prefer constructing `ProcessOverlayRunService` per call (same pattern as E1b tests) to avoid circular import weight; if import cycle appears, extract a tiny function in `process_overlay/service/auto_start.py` that workflows imports.

### What `start_run` already enforces (reuse)

From `runs.py` on main:

| Check | Error |
|-------|--------|
| Config missing | `NotFoundError` |
| Config not ACTIVE | `ProcessOverlayActivationError` |
| No `active_definition_version_id` | `ProcessOverlayValidationError` |
| Version not owned by config/tenant | validation / `ProcessOverlayTenantIsolationError` |
| WorkItem missing / wrong tenant | `NotFoundError` |
| WorkItem pipeline ≠ config pipeline | `ProcessOverlayValidationError` |
| Existing ACTIVE run | `ProcessRunConflictError` |
| Concurrent unique violation | `ProcessRunConflictError` from `IntegrityError` |
| Effects | INSERT ACTIVE run; pin version; audit `process_run.started`; optional `current_stage_code` snapshot |

### Tenant / pipeline isolation

| Rule | Enforcement |
|------|-------------|
| Tenant A create never reads tenant B config | lookup always includes `self.tenant_id` |
| Config for pipeline X never starts for WorkItem on pipeline Y | `start_run` R3 + unique config per pipeline |
| Cross-tenant WorkItem id | `WorkflowRepository.get_work_item(tenant_id, …)` inside `start_run` |

---

## Transaction / flow diagram

```text
HTTP POST /work-items
  └─ routes.create_work_item
       ├─ WorkflowService.create_work_item(user, payload)
       │    ├─ validate pipeline/stage/party/custom fields
       │    ├─ INSERT work_item (+ participants + custom values)
       │    ├─ flush
       │    ├─ _maybe_auto_start_process_run
       │    │    ├─ lookup config by (tenant, pipeline)
       │    │    ├─ if missing/INACTIVE → return
       │    │    └─ else ProcessOverlayRunService.start_run(...)
       │    │         ├─ begin_nested: INSERT process_run + audit
       │    │         └─ flush
       │    └─ return WorkItemResponse
       └─ db.commit()   # WorkItem + Run + audit commit together
            OR exception → session rollback (nothing persisted)
```

---

## Error semantics summary

| Case | Auto-start? | WorkItem persisted? | Run? | Notes |
|------|-------------|---------------------|------|-------|
| No overlay config | No | Yes | No | Identical to pre-E1b2 CRM |
| Config INACTIVE | No | Yes | No | Identical to pre-E1b2 CRM |
| Config ACTIVE + healthy version | Yes | Yes (same txn) | Yes ACTIVE | Pin + audit |
| Config ACTIVE + `start_run` fails | Attempted | **No** (rollback) | No | Fail-closed |
| Duplicate ACTIVE race | Attempted | **No** if conflict raised before commit | No | `ProcessRunConflictError` |
| Explicit `start_run` after create (inactive path) | N/A | already created | via explicit API/service | Unchanged E1b |

HTTP mapping: existing exception handlers for `ConflictError` / overlay errors apply; no new API error types required for E1b2.

---

## Test plan

New file (preferred): `backend/tests/test_process_overlay_e1b2_auto_start.py`  
Update: rewrite E1b T13 in `test_process_overlay_e1b_runs.py` **or** move anti-hook assertion into e1b2 matrix and replace T13 with a pointer comment.

| ID | Scenario | Assertion |
|----|----------|-----------|
| A1 | No config for pipeline | `create_work_item` → WorkItem ok; `_count_runs == 0` |
| A2 | Config INACTIVE (even with published version) | WorkItem ok; zero runs |
| A3 | Config ACTIVE + active version | WorkItem ok; **exactly one** ACTIVE run; pin == `active_definition_version_id` |
| A4 | Audit on auto-start | audit row with `event=process_run.started` for that run |
| A5 | Tenant isolation | Tenant B ACTIVE config does not create run for tenant A create |
| A6 | Pipeline isolation | ACTIVE config on pipeline X; create on pipeline Y → zero runs |
| A7 | Fail-closed | Force `start_run` failure (e.g. monkeypatch or corrupt ACTIVE without version) → create raises; **zero** WorkItems and **zero** runs after rollback |
| A8 | Explicit start still works | After inactive create (no run), `start_run` succeeds |
| A9 | Source/integration | `create_work_item` path **does** call overlay when ACTIVE (invert old T13 source assert) |
| A10 | `move_stage` still unbound | With auto-started ACTIVE run, `move_stage` still moves (no E1c) — regression from E1b T14 |
| A11 | No retrospective | Pre-existing WorkItem without run stays without run after activating config (activation alone creates no runs) |

### Commands (after code approval)

```bash
cd backend
python -m pytest tests/test_process_overlay_e1b2_auto_start.py -q
python -m pytest tests/test_process_overlay_e1b_runs.py tests/test_process_overlay_e1b_models.py -q
python -m pytest tests/test_process_overlay_e1a_models.py tests/test_process_overlay_e1a_publication.py -q
python -m compileall app/modules/workflows app/modules/process_overlay
```

No migration test required unless a migration is unexpectedly introduced (should not be).

---

## Proposed file touch list

### Create

| Path | Purpose |
|------|---------|
| `backend/tests/test_process_overlay_e1b2_auto_start.py` | A1–A11 matrix |

### Modify

| Path | Change |
|------|--------|
| `backend/app/modules/process_overlay/repository.py` | Add `get_configuration_by_pipeline` |
| `backend/app/modules/workflows/service.py` | Thin `_maybe_auto_start_process_run` + call from `create_work_item` |
| `backend/tests/test_process_overlay_e1b_runs.py` | Replace/adjust former T13 (zero-run-with-ACTIVE) for E1b2 semantics |

### Optional (only if import cycle)

| Path | Purpose |
|------|---------|
| `backend/app/modules/process_overlay/service/auto_start.py` | Isolate hook helper to avoid workflows↔overlay cycles |

### Intentionally NOT touched

| Path | Reason |
|------|--------|
| Dirty root WIP / marketing branch working tree | Forbidden |
| `workflows/routes.py` | Commit boundary already correct; no API change |
| `workflows/models.py` | Variant B — no WorkItem columns |
| `process_overlay/service/runs.py` | Reuse as-is unless tiny public helper needed (prefer no change) |
| `move_stage` / `update_work_item` | E1c |
| Alembic versions | No schema change |
| Frontend / OpenAPI | Out |
| Industry templates / seed auto-activate | Out |

---

## Implementation steps (after Approval Gate only)

1. Add `get_configuration_by_pipeline` + unit coverage via e1b2 tests.  
2. Add `_maybe_auto_start_process_run` in `WorkflowService`; call after flush in `create_work_item`.  
3. Write `test_process_overlay_e1b2_auto_start.py` (A1–A11).  
4. Update former E1b T13 expectations.  
5. Run pytest commands above.  
6. Stop — do **not** start E1c in the same slice.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Fail-closed surprises tenants who activate overlay before noticing create failures | Medium | Medium | Document ops precondition: only activate when version set + pipeline ready; deactivate to restore legacy create |
| Import cycle workflows ↔ process_overlay | Low | Medium | Optional `auto_start.py` helper; keep hook thin |
| Scope creep into stage filter / enforcement | Medium | High | Forbidden list; A10 proves no E1c |
| Old E1b T13 becomes a false red | High | Low | Explicitly rewrite test in same PR/slice |
| Silent skip when ACTIVE but version null | Low | Medium | Fall through to `start_run` (fail-closed) rather than soft skip |
| Dirty-root contamination | Medium | High | Implement only in clean worktree from `origin/main`; never edit dirty marketing WIP |

---

## Rollback

| Level | Action |
|-------|--------|
| Code | Revert commit(s) touching `workflows/service.py` hook + repo helper + e1b2 tests; restore E1b T13 if needed |
| Schema | N/A (no migration) |
| Data | Any Runs created while hook was live remain; no automatic cleanup — acceptable for local/staging; production deploy only after separate approval |
| Operational | `deactivate_configuration` immediately restores “create without Run” behavior without code rollback |

---

## GO / NO-GO verdict

### Verdict for **this documentation step**

**GO** — plan is complete and grounded in current `origin/main` E1b runtime.

### Verdict for **future E1b2 application code**

**Conditional GO** after HQ Approval Gate, if all criteria below are accepted:

| # | Criterion |
|---|-----------|
| 1 | Opt-in = ACTIVE config for `(tenant, pipeline)` only; no config / INACTIVE = unchanged CRM create |
| 2 | Auto-start implemented **only** via existing `start_run` (pin + audit + conflict) |
| 3 | WorkItem + ProcessRun + audit share **one** outer transaction (route commit); fail-closed on start failure |
| 4 | No migration; no API/UI; no `move_stage`/`update_work_item` changes; no E1c evidence/transitions |
| 5 | Tenant + pipeline isolation covered by tests A5–A6 |
| 6 | Former E1b “zero runs on create” test updated intentionally |
| 7 | Implementation happens in a **clean** worktree from `origin/main` — **not** dirty root WIP |
| 8 | No push / merge / deploy without separate explicit approval |

**NO-GO for code now** — this artifact is documentation-only; wait for explicit approval before editing application code.

---

## Approval Gate before code

Approver confirms:

- [ ] D1–D7 design decisions accepted (especially fail-closed D4 and no stage filter D3)
- [ ] File touch list acceptable
- [ ] Test matrix A1–A11 acceptable
- [ ] No E1c / no API / no migration in this slice
- [ ] Implement only after approval, in clean worktree, no push

**Status: waiting for approval**

---

## Finish block (this documentation step)

1. **Files changed:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1b2-auto-start-implementation-plan.md` (created in clean worktree `.worktrees/process-overlay-e1b2-plan` only)  
2. **Files intentionally not touched:** all application code; dirty root WIP; Alembic; workflows runtime; E1c surfaces; remote git  
3. **Tests/checks run:** none (documentation-only); baseline read from `origin/main` @ `76773ec`  
4. **Risks:** fail-closed UX when overlay ACTIVE; import cycle; test T13 rewrite  
5. **Next safe step:** HQ approves this E1b2 plan → implement hook + tests in a clean worktree (no push)  
6. **Handoff:** optional after code; not required for plan-only step  

**Confirmations:** no E1b2 runtime application code written; no push; no merge; no deploy; dirty root WIP not modified.
