# Implementation Plan: Process Overlay E1b — ProcessRun Runtime Binding

**Date:** 2026-07-17
**Type:** implementation plan (approved for local E1b code)
**Project:** Flexity
**Category:** platform_core (thin Process Overlay)
**Parent architecture:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1-architecture-plan.md` (HQ approved)
**Parent E1a plan:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1a-implementation-plan.md`
**Parent reconciliation:** `docs/ai/reviews/2026-07-17-flexity-existing-process-architecture-reconciliation.md`
**Status:** **approved for local implementation** on `feature/process-overlay-e1b` (base `8ec55cd`)
**Depends on:** E1a code + migration `0019_process_overlay_e1a` (tables `process_templates`, `tenant_process_configurations`, `process_definition_versions`)
**Proposed Alembic revision:** `0020_process_overlay_e1b`
**Parent migration (plan):** `0019_process_overlay_e1a`
**Note on chain:** On `feature/process-overlay-e1a` / E1b base, E1a has `down_revision = "0015_marketing_cabinet_mvp"`. E1b parent remains revision id `0019_process_overlay_e1a`. After `0020` lands, Alembic **head = `0020_process_overlay_e1b`**; `0019` is verified as a **chain ancestor**, not as sole head.
**Git staged files:** 0

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | platform_core |
| Risk level | medium (new runtime table + service; **no** CRM hook / enforcement) |
| Intended scope | `ProcessRun` model/table, run service (`start` / `complete` / `cancel`), repository, audit, migration, tests |
| Forbidden scope | hook in `create_work_item`, `move_stage` / `update_work_item` enforcement, automatic transitions, API/routes, UI, required fields/tasks/documents/approvals, industry template auto-activation, deploy |
| Required plan | this document |

---

## Goal

Deliver **E1b minimal runtime binding**: thin `ProcessRun` entity that links a WorkItem to a **pinned** immutable `ProcessDefinitionVersion` under a tenant configuration — started **only** via explicit `start_run()`, with lifecycle `active` / `completed` / `cancelled` and audit — **without** changing CRM create/move behavior and **without** transition policy enforcement.

Empty overlay / no Run = current CRM behavior unchanged (same as E1a guarantee).

---

## Exact scope E1b

### In scope

| Deliverable | Detail |
|-------------|--------|
| ORM model | `ProcessRun` |
| Alembic migration | `0020_process_overlay_e1b` → creates `process_runs` (+ enum) only |
| Enum | `ProcessRunState`: `ACTIVE` / `COMPLETED` / `CANCELLED` |
| Binding | `tenant_id` + `tenant_process_configuration_id` + `process_definition_version_id` (pinned) + `work_item_id` |
| Version pinning | At `start_run()`: copy `config.active_definition_version_id` into Run; never mutate pin afterward |
| Explicit start | `ProcessOverlayRunService.start_run(...)` — **not** called from `WorkflowService.create_work_item` |
| Lifecycle methods | `complete_run()` / `cancel_run()` as service methods for lifecycle only — **no** auto-complete from CRM stage moves |
| Audit | `process_run.started` / `completed` / `cancelled` (via existing `AuditRecorder` + stable summary/details) |
| Repository / service | Tenant-scoped persistence + business invariants |
| Tests | Model constraints, start/complete/cancel, pinning, isolation, no CRM hook, migration up/down |

### Out of scope (explicit)

| Item | Deferred to |
|------|-------------|
| Hook in `create_work_item` / auto-start | **E1b2** (future plan section; not code now) |
| `move_stage` / `update_work_item` enforcement | **E1c** |
| Automatic transitions / policy evaluation | **E1c** |
| Auto-complete Run on terminal stages | **E1c** |
| HTTP routes / OpenAPI / UI | later |
| Required fields / tasks / documents / approvals | **E1c** (+ policy execution) |
| ModuleGuard disable blocking | **E1c** |
| `superseded_inactive` run state | later (architecture mentioned; **not** E1b) |
| Industry template auto-provision / deploy | out |

---

## Separation matrix

| Concern | E1a (done) | E1b (this plan) | E1b2 (future) | E1c (future) |
|---------|------------|-----------------|---------------|--------------|
| ProcessTemplate / TenantProcessConfiguration / ProcessDefinitionVersion | ✅ | reuse | reuse | reuse |
| Publish / set active version / activation state | ✅ | read-only for start preconditions | same | same |
| ProcessRun table + lifecycle | — | ✅ | reuse | reuse |
| Explicit `start_run()` | — | ✅ | still available | still available |
| Auto-start on WorkItem create (opt-in) | — | ❌ | ✅ | — |
| Hook `workflows.service.create_work_item` | — | ❌ **forbidden** | optional thin call only if config ACTIVE | — |
| `move_stage` policy enforcement | — | ❌ | ❌ | ✅ |
| Auto complete/cancel from stage moves | — | ❌ | ❌ | ✅ |
| Required evidence (fields/tasks/docs/approvals) | validate-only in policy JSON | ❌ | ❌ | ✅ evaluate |
| API / UI | ❌ | ❌ | ❌ | ❌ (separate) |

**Architecture note:** Parent architecture §15 described E1b as “Create Run on qualifying new WorkItem when config active”. This **implementation plan intentionally narrows** E1b to **explicit start only**. Auto-start is isolated as **E1b2** so CRM create path stays untouched until a separate Approval Gate.

---

## Relevant existing code (anchors)

| Area | Path | Reuse in E1b |
|------|------|--------------|
| Overlay models (E1a) | `backend/app/modules/process_overlay/models.py` | Add `ProcessRun`; FK to config + version |
| Overlay enums | `backend/app/modules/process_overlay/enums.py` | Add `ProcessRunState` |
| Overlay constants | `backend/app/modules/process_overlay/constants.py` | Add `ENTITY_PROCESS_RUN` |
| Overlay exceptions | `backend/app/modules/process_overlay/exceptions.py` | Add run-specific errors as needed |
| Overlay repository | `backend/app/modules/process_overlay/repository.py` | Insert/get/list runs (tenant-scoped); **no** version update |
| Config / publication services | `service/configuration.py`, `service/publication.py` | Read config + active version for start preconditions |
| WorkItem ORM | `backend/app/modules/workflows/models.py` | FK target; load for tenant/pipeline checks |
| CRM create/move (unchanged) | `backend/app/modules/workflows/service.py` | **Not modified** in E1b |
| Audit writer | `backend/app/modules/audit/recorder.py` | Run lifecycle events |
| ORM registration | `backend/app/modules/models.py` | Register `ProcessRun` |
| Migration parent | `backend/alembic/versions/20260717_0019_process_overlay_e1a.py` | `revision = "0019_process_overlay_e1a"` |
| Migration test pattern | `backend/tests/test_migration_0019_process_overlay_e1a.py` | Copy for 0020 |
| E1a publication tests | `backend/tests/test_process_overlay_e1a_*.py` | Fixture patterns for config + published version |

---

## Entity design — ProcessRun

### Needed in E1b: **Yes** — Variant B runtime binding (architecture §4–§6).

| Aspect | Specification |
|--------|---------------|
| **Responsibility** | Opt-in runtime link: WorkItem ↔ pinned definition version under tenant config; holds run lifecycle state only. Does **not** evaluate policy or move stages. |
| **Table** | `process_runs` |
| **Tenant ownership** | `tenant_id` NOT NULL; all reads/writes scoped by tenant |
| **WorkItem link** | FK `work_item_id` → `work_items.id` RESTRICT (or CASCADE only if product later decides; **E1b default: RESTRICT** to avoid silent run loss) |
| **Config link** | FK `tenant_process_configuration_id` → `tenant_process_configurations.id` RESTRICT |
| **Version pin** | FK `process_definition_version_id` → `process_definition_versions.id` RESTRICT; set once at start; **immutable** |
| **Deletion** | No application delete in E1b. Terminal states are `completed` / `cancelled`. Downgrade drops table (dev only). |

### Fields

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID PK | PK | `UUIDPrimaryKeyMixin` |
| `tenant_id` | UUID FK | FK → `tenants.id` CASCADE, indexed | Must match config / work_item / version tenant |
| `tenant_process_configuration_id` | UUID FK | FK → `tenant_process_configurations.id` RESTRICT, indexed | |
| `process_definition_version_id` | UUID FK | FK → `process_definition_versions.id` RESTRICT, indexed | **Pinned** at start from `config.active_definition_version_id` |
| `work_item_id` | UUID FK | FK → `work_items.id` RESTRICT, indexed | |
| `run_state` | Enum | NOT NULL, default `ACTIVE` | `ProcessRunState` |
| `started_at` | timestamptz | NOT NULL | Set at insert |
| `started_by_user_id` | UUID | NOT NULL | Actor at start |
| `completed_at` | timestamptz | NULL | Set on complete/cancel |
| `completed_by_user_id` | UUID | NULL | Actor at complete/cancel |
| `completion_reason` | Text | NULL | Optional on complete; recommended non-empty on cancel |
| `current_stage_code` | String(64) | NULL | Optional cache of WorkItem stage **code** at start (convenience); WorkItem.stage remains CRM SoT. **No** sync on `move_stage` in E1b. |
| `created_at` / `updated_at` | timestamptz | NOT NULL | `TimestampMixin` |

### Unique / partial uniqueness (E1 constraint)

| Name | Rule | Purpose |
|------|------|---------|
| `uq_process_run_one_active_per_work_item` | At most **one** row with `run_state = ACTIVE` per `work_item_id` | Architecture E1: 0..1 active Run per WorkItem |

**Enforcement:**

1. **Service:** before insert, query active run for `(tenant_id, work_item_id)` → conflict if exists.
2. **DB:** prefer **partial unique index** where supported:

```sql
CREATE UNIQUE INDEX uq_process_run_one_active_per_work_item
  ON process_runs (work_item_id)
  WHERE run_state = 'active';
```

If Alembic/Postgres test env supports it (same as other partial indexes in repo), use it. If SQLite unit tests cannot express partial unique the same way, service + integration tests remain primary; document dialect note in migration docstring.

**Historical runs:** multiple `COMPLETED` / `CANCELLED` rows for the same WorkItem are **allowed** in E1b (operator may start again after cancel/complete — product may tighten later). Second `ACTIVE` while one exists → conflict.

### Statuses — `ProcessRunState` (new enum in `process_overlay/enums.py`)

| Value | Meaning |
|-------|---------|
| `ACTIVE` | Run started; no enforcement yet (E1c). Pin fixed. |
| `COMPLETED` | Explicitly completed via `complete_run()` (not via CRM stage in E1b) |
| `CANCELLED` | Explicitly cancelled via `cancel_run()` |

**Not in E1b:** `superseded_inactive` (architecture sketch only).

### Critical invariants

| # | Invariant |
|---|-----------|
| R1 | `run.tenant_id == config.tenant_id == version.tenant_id == work_item.tenant_id` |
| R2 | `version.tenant_process_configuration_id == config.id` |
| R3 | `work_item.pipeline_id == config.pipeline_id` (WorkItem must sit on the configured pipeline) |
| R4 | At start: `config.activation_state == ACTIVE` |
| R5 | At start: `config.active_definition_version_id` is NOT NULL; pin that id (do **not** accept arbitrary version id from caller in E1b minimal — always pin active pointer) |
| R6 | Version pin never updates after insert (no repository update of `process_definition_version_id`) |
| R7 | At most one `ACTIVE` Run per WorkItem |
| R8 | `complete_run` / `cancel_run` only from `ACTIVE`; terminal states are terminal (no reopen in E1b) |
| R9 | `start_run` is **never** invoked from `WorkflowService.create_work_item` / `move_stage` in E1b |
| R10 | Creating WorkItem with or without overlay config does **not** create a Run |

---

## start_run contract

```
ProcessOverlayRunService.start_run(
  tenant_id: UUID,
  work_item_id: UUID,
  configuration_id: UUID,   # explicit which overlay config
  actor_user_id: UUID,
) -> ProcessRunDTO
```

**Note:** `completion_reason` is **not** part of `start_run` (only used on `complete_run` / `cancel_run`).

### Preconditions (fail closed)

1. Load config via repository scoped to `tenant_id` + `configuration_id`. Missing → `NotFoundError`.
2. Assert `config.activation_state == ACTIVE`. Else → `ProcessOverlayActivationError` / validation error (“overlay inactive”).
3. Assert `config.active_definition_version_id` is set. Else → `ProcessOverlayValidationError` (“no active definition version”).
4. Load version by id; assert belongs to same config + tenant (R1–R2).
5. Load WorkItem via `WorkflowRepository` (or equivalent tenant-scoped get). Missing → `NotFoundError`.
6. Assert `work_item.pipeline_id == config.pipeline_id` (R3).
7. Assert no existing `ACTIVE` ProcessRun for this `work_item_id` (R7). Else → `ConflictError` / `ProcessRunConflictError`.
8. Optionally snapshot `current_stage_code` from WorkItem’s current stage code (read-only convenience).

### Effects

1. INSERT `ProcessRun` with:
   - `run_state=ACTIVE`
   - `process_definition_version_id = config.active_definition_version_id` (**pin**)
   - `started_at=now`, `started_by_user_id=actor`
2. Audit: `entity_type="process_run"`, action=`CREATE` or `EXECUTE`, summary indicating **started** (see Audit section).
3. flush / return DTO.
4. **Does not** change WorkItem stage, status, custom fields, tasks, or pipeline.

### Explicit non-behavior

- Does **not** validate transition policy.
- Does **not** require WorkItem to be on `new_lead` (E1b keeps start flexible; E1b2/E1c may add start-stage rules).
- Does **not** auto-call from CRM.

---

## Lifecycle: complete_run / cancel_run

Needed so Run is not a dead-end row before E1c auto-completion. These are **manual service methods** only.

### complete_run

```
complete_run(tenant_id, process_run_id, actor_user_id, *, reason: str | None = None)
  1. Load run tenant-scoped; must be ACTIVE
  2. run_state = COMPLETED; completed_at/by; optional reason
  3. Audit completed
  4. No WorkItem mutation
```

### cancel_run

```
cancel_run(tenant_id, process_run_id, actor_user_id, *, reason: str)
  1. Load run tenant-scoped; must be ACTIVE
  2. Require non-empty reason (service + optional DB check on cancel path)
  3. run_state = CANCELLED; completed_at/by; completion_reason=reason
  4. Audit cancelled
  5. No WorkItem mutation
```

**E1b guarantee:** No CRM stage move, close, or reopen triggers these methods.

---

## Audit

Reuse `AuditRecorder.audit_log` **in the same style as E1a** (`configuration.py` / `publication.py`):

- Human-readable `summary` (sentence), not bare event codes as the only summary text.
- Structured payload in `changes_json` with a **stable** `"event"` key for tests.

| Event (logical) | `action` | `entity_type` | `summary` (human) | `changes_json` (required keys) |
|-----------------|----------|---------------|-------------------|--------------------------------|
| started | `AuditAction.CREATE` | `process_run` | `Process run started` | `event="process_run.started"`, `work_item_id`, `configuration_id`, `definition_version_id`, `version_number` |
| completed | `AuditAction.UPDATE` | `process_run` | `Process run completed` | `event="process_run.completed"`, optional `completion_reason` |
| cancelled | `AuditAction.UPDATE` | `process_run` | `Process run cancelled` | `event="process_run.cancelled"`, `completion_reason` |

**Constant:** add `ENTITY_PROCESS_RUN = "process_run"` in `constants.py`.

**Test asserts:** prefer `changes_json["event"] == "process_run.started"` (etc.), not fragile free-form summary matching alone.

---

## Migration structure

**File:** `backend/alembic/versions/20260717_0020_process_overlay_e1b.py`
(filename date may match implement day; revision id is authoritative)

| Property | Value |
|----------|--------|
| `revision` | `0020_process_overlay_e1b` (≤ 32 chars) |
| `down_revision` | **`0019_process_overlay_e1a`** |
| Docstring | Local/schema readiness; creates ProcessRun only; does not hook CRM; does not enforce transitions; does not auto-start |

### Migration order (upgrade)

1. Create enum storage for `process_run_state` (`ACTIVE`/`COMPLETED`/`CANCELLED` or lowercase values matching E1a style — **follow E1a**: `native_enum=False`, values consistent with `ProcessOverlayActivationState` storage style, i.e. lowercase `"active"` etc. if that is what E1a uses).
2. Create table `process_runs` with FKs to `tenants`, `tenant_process_configurations`, `process_definition_versions`, `work_items`.
3. Create indexes: `tenant_id`, `work_item_id`, `configuration_id`, `definition_version_id`, `run_state`.
4. Create partial unique index for one ACTIVE run per work_item (Postgres).

### Downgrade

1. Drop partial unique index.
2. Drop `process_runs`.
3. Drop enum type if created as DB enum (if string/`native_enum=False` only, no separate type drop beyond column).

**Does not:** ALTER `work_items`, `pipelines`, `pipeline_stages`, or E1a overlay tables beyond FK targets existing. No CRM data migration.

### ORM registration

Extend `backend/app/modules/models.py`:

```python
from app.modules.process_overlay.models import (  # noqa: F401
    ProcessDefinitionVersion,
    ProcessRun,
    ProcessTemplate,
    TenantProcessConfiguration,
)
```

---

## Model / service / repository boundaries

```
process_overlay/
├── ... (E1a unchanged conceptually)
├── enums.py                 # + ProcessRunState
├── exceptions.py            # + ProcessRunConflictError / ProcessRunStateError (as needed)
├── constants.py             # + ENTITY_PROCESS_RUN
├── models.py                # + ProcessRun
├── schemas.py               # + ProcessRun DTOs
├── repository.py            # + run insert/get/list/active-by-work-item; update state only
└── service/
    ├── ...                  # E1a services unchanged in behavior
    └── runs.py              # NEW: start_run / complete_run / cancel_run
```

| Layer | Responsibility | Must NOT |
|-------|----------------|----------|
| **Repository** | Persist runs; tenant filters; find active by work_item | Policy evaluation; CRM mutations |
| **Run service** | Preconditions R1–R10; pin version; lifecycle; audit | Call `move_stage`; hook create_work_item; evaluate policy JSON |
| **WorkflowService** | Unchanged | Import or call run service in E1b |
| **AuditRecorder** | Append audit rows | Validation |

**No routes** in E1b — services invoked from tests (and future internal callers / E1b2).

---

## Files to create

| Path | Purpose |
|------|---------|
| `backend/app/modules/process_overlay/service/runs.py` | `ProcessOverlayRunService` |
| `backend/alembic/versions/20260717_0020_process_overlay_e1b.py` | Migration |
| `backend/tests/test_process_overlay_e1b_models.py` | ORM / constraints / metadata |
| `backend/tests/test_process_overlay_e1b_runs.py` | start/complete/cancel + invariants |
| `backend/tests/test_migration_0020_process_overlay_e1b.py` | Alembic up/down; CRM + E1a tables intact |

## Files to modify

| Path | Change |
|------|--------|
| `backend/app/modules/process_overlay/models.py` | Add `ProcessRun` |
| `backend/app/modules/process_overlay/enums.py` | Add `ProcessRunState` |
| `backend/app/modules/process_overlay/exceptions.py` | Run conflict / invalid state errors |
| `backend/app/modules/process_overlay/constants.py` | `ENTITY_PROCESS_RUN` |
| `backend/app/modules/process_overlay/schemas.py` | Run DTOs |
| `backend/app/modules/process_overlay/repository.py` | Run persistence helpers |
| `backend/app/modules/process_overlay/service/__init__.py` | Export run service |
| `backend/app/modules/models.py` | Register `ProcessRun` |
| `backend/tests/test_migration_0019_process_overlay_e1a.py` | After 0020: assert head=`0020`; `0019` remains in chain (ancestor / reachable), not sole head |

## Files intentionally NOT touched

| Path | Reason |
|------|--------|
| `backend/app/modules/workflows/service.py` | No create/move hooks (E1b); E1b2/E1c only after separate approval |
| `backend/app/modules/workflows/routes.py` | No API |
| `backend/app/modules/workflows/models.py` | No WorkItem columns (Variant B) |
| `backend/app/modules/workflows/repository.py` | Prefer read-only usage from overlay; no write API changes required |
| `backend/app/modules/industry_templates/*` | No auto overlay / auto run |
| `backend/app/main.py` | No router |
| `backend/app/core/modules.py` | ModuleGuard blocking = E1c |
| E1a migration file | Do not rewrite; E1b only adds child revision |
| `feature/marketing-m8` branch | Out of scope for this task’s git ops |

---

## Test matrix

| ID | Invariant | Test file | Assertion |
|----|-----------|-----------|-----------|
| T1 | `ProcessRun` registered in metadata | models | Table in `Base.metadata` |
| T2 | FK / tenant isolation on read | runs | Tenant A cannot load tenant B run |
| T3 | start pins `active_definition_version_id` | runs | Run version id == config active pointer |
| T4 | start fails if config INACTIVE | runs | validation / activation error; zero rows |
| T5 | start fails if no active version | runs | validation error |
| T6 | start fails if WorkItem pipeline ≠ config pipeline | runs | validation error |
| T7 | start fails cross-tenant WorkItem | runs | not found / isolation error |
| T8 | second ACTIVE run on same WorkItem rejected | runs | conflict; still one ACTIVE |
| T9 | complete from ACTIVE → COMPLETED + audit | runs | state + `process_run.completed` |
| T10 | cancel from ACTIVE → CANCELLED + audit + reason | runs | state + `process_run.cancelled` |
| T11 | complete/cancel from non-ACTIVE rejected | runs | state error |
| T12 | start does not change WorkItem stage/status | runs | before/after equal |
| T13 | `create_work_item` creates **zero** Runs (even if config ACTIVE) | runs | CRM create only; no overlay hook |
| T14 | `move_stage` unchanged with active Run | runs | stage moves as legacy CRM; run state stays ACTIVE |
| T15 | Version pin immutable | runs | no update path for `process_definition_version_id` |
| T16 | After cancel, new start allowed (new ACTIVE) | runs | second run row ACTIVE; first CANCELLED |
| T17 | Migration upgrade creates `process_runs` | migration | table exists |
| T18 | Migration downgrade drops runs only | migration | E1a tables + work_items/pipelines intact |
| T19 | Audit `process_run.started` on start | runs | audit row; `changes_json.event` |
| T20 | Changing config active version after start does **not** change existing Run pin | runs | pin stays old version id |
| T21 | After `0020`, Alembic **head = 0020**; `0019` is in ancestors/chain | migration (+ update E1a migration test) | not `get_heads() == [0019]` |

### Commands (after code approval)

```bash
cd backend
python -m pytest tests/test_process_overlay_e1b_models.py tests/test_process_overlay_e1b_runs.py -q
python -m pytest tests/test_migration_0020_process_overlay_e1b.py -q   # Postgres required
python -m compileall app/modules/process_overlay
```

**Regression (recommended):** keep E1a tests green:

```bash
python -m pytest tests/test_process_overlay_e1a_models.py tests/test_process_overlay_e1a_publication.py -q
```

---

## Implementation steps (ordered — after Approval Gate)

1. Add `ProcessRunState` enum + exceptions + `ENTITY_PROCESS_RUN` constant.
2. Add `ProcessRun` ORM model + register in `app/modules/models.py`.
3. Write migration `0020_process_overlay_e1b` with `down_revision = "0019_process_overlay_e1a"`.
4. Extend repository: create run, get by id (tenant), get active by work_item, update state fields only.
5. Implement `ProcessOverlayRunService.start_run` / `complete_run` / `cancel_run` + audit.
6. Export from `service/__init__.py`.
7. Add model tests (T1, constraints).
8. Add run service tests (T2–T16, T19–T20) including **explicit** T13/T14 proving no CRM hooks.
9. Add migration test (T17–T18).
10. Stop — do **not** implement E1b2 auto-start in the same slice.

---

## E1b2 (future — not code in this slice)

**Purpose:** opt-in automatic `ProcessRun` start when a WorkItem is created, **without** changing behavior for tenants without active overlay.

### Proposed rule (draft for future Approval Gate)

1. Only inside `WorkflowService.create_work_item` **after** successful WorkItem insert (or via a narrowly injected callback) — still prefer calling `ProcessOverlayRunService.start_run` rather than duplicating logic.
2. Fire **only if**:
   - there exists `TenantProcessConfiguration` for `(tenant_id, work_item.pipeline_id)` with `activation_state=ACTIVE`, **and**
   - `active_definition_version_id` is set, **and**
   - product flag / template rule allows auto-start (e.g. `flexity_sales_intake` only), **and**
   - no ACTIVE run already exists.
3. If overlay inactive / no config / no active version → **no-op** (identical to today).
4. Failures during auto-start: define product choice later (fail WorkItem create vs log-and-continue). Default recommendation for future plan: **fail closed** only if tenant explicitly opted into mandatory overlay; otherwise log + leave WorkItem without Run — **decide in E1b2 plan**, not now.
5. Still **no** `move_stage` enforcement (that remains E1c).
6. No retrospective Runs for pre-existing WorkItems.

### Explicitly out of E1b (again)

Do **not** implement any of E1b2 in the E1b code Approval Gate.

---

## Rollback

| Level | Action |
|-------|--------|
| **Code rollback** | Revert commit(s) touching ProcessRun model/service/tests/migration/`models.py` import |
| **Schema rollback** | `alembic downgrade 0019_process_overlay_e1a` — drops `process_runs` only |
| **Data impact** | Run rows lost on downgrade; E1a overlay + CRM/pipelines/work_items unaffected |
| **Forward again** | `alembic upgrade 0020_process_overlay_e1b` recreates empty `process_runs` |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep into auto-start / enforcement | Medium | High | Forbidden file list; tests T13/T14; E1b2 separated |
| Architecture vs this plan mismatch (auto-start in arch §15) | Medium | Low | Documented narrowing + E1b2 section; HQ re-approves |
| Partial unique index dialect differences | Medium | Medium | Service conflict check primary; Postgres partial unique in migration test |
| Pinning wrong version if active pointer races | Low | Medium | Read config+version in one service transaction; tests T3/T20 |
| Accidental WorkItem FK CASCADE delete wiping history | Low | Medium | Prefer `ON DELETE RESTRICT` in E1b |
| Migration parent drift after E1a rebase | Medium | Medium | Always set `down_revision = "0019_process_overlay_e1a"`; do not chain to marketing heads |
| Completing runs without CRM meaning confuses operators | Low | Low | E1b is internal/test surface; no API/UI |

---

## Approval Gate before code

**Stop — do not write E1b code until explicit approval of this E1b plan.**

Approver confirms:

- [ ] One new entity only: `ProcessRun` (+ enum/migration/tests/service)
- [ ] Migration `0020_process_overlay_e1b` with parent **`0019_process_overlay_e1a`**
- [ ] Explicit `start_run()` only — **no** `create_work_item` hook in E1b
- [ ] Lifecycle `active` / `completed` / `cancelled` via service methods; **no** auto transitions from CRM
- [ ] Immutable version pin at start from `active_definition_version_id`
- [ ] No API / UI / enforcement / required evidence
- [ ] E1b2 auto-start is **future-only** (documented here, not implemented)
- [ ] Test matrix T1–T20 acceptable

**After approval:** implement E1b in a focused commit series; then either E1b2 plan or E1c enforcement plan as HQ directs.

---

## Final summary

| Item | Value |
|------|--------|
| **Exact scope E1b** | ProcessRun binding + explicit start/complete/cancel + audit + migration + tests |
| **Models / tables** | `process_runs` (+ `ProcessRunState`) |
| **CRM hooks** | **None** in E1b |
| **E1b2** | Future opt-in auto-start only when config ACTIVE; documented, not coded |
| **Files to create** | ~5 (run service, migration, 3 test files) |
| **Files to modify** | overlay enums/models/exceptions/constants/schemas/repository/service `__init__` + `app/modules/models.py` |
| **Migration parent** | `0019_process_overlay_e1a` |
| **Test matrix** | T1–T20 |
| **Out of scope** | Enforcement, auto-start, API, UI, evidence checks, deploy |
| **Approval Gate** | Required before any E1b code |
| **staged** | **0** |

---

## Finish block

1. **Files changed:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1b-implementation-plan.md` (created)
2. **Files intentionally not touched:** all backend production code; E1a migration; workflows; marketing-m8 branch
3. **Tests/checks run:** none (documentation-only); E1a revision id verified as `0019_process_overlay_e1a`
4. **Risks:** architecture auto-start wording vs narrowed E1b; partial unique index dialect; migration chain rebase
5. **Next safe step:** HQ approves this E1b plan → then implement E1b code only (no E1b2)
6. **Handoff:** optional after E1b code complete; not required for plan-only step
