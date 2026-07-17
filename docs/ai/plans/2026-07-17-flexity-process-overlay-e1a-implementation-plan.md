# Implementation Plan: Process Overlay E1a — Config & Versioning Skeleton

**Date:** 2026-07-17
**Type:** implementation plan (documentation only — **no code yet**)
**Project:** Flexity
**Category:** platform_core (thin Process Overlay)
**Parent architecture:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1-architecture-plan.md` (HQ approved)
**Parent reconciliation:** `docs/ai/reviews/2026-07-17-flexity-existing-process-architecture-reconciliation.md`
**Status:** waiting for **Approval Gate before code**
**Current Alembic head (baseline):** `0018_mkt_storage_profiles`
**Git staged files:** 0

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | platform_core |
| Risk level | medium (new tables + service layer; no CRM behavior change) |
| Intended scope | new `process_overlay` module, one migration, tests |
| Forbidden scope | ProcessRun, enforcement hooks, API/routes, UI, workflows changes, industry template auto-activation, deploy |
| Required plan | this document |

---

## Goal

Deliver **E1a skeleton**: platform catalog + tenant configuration + immutable published definition versions, with server-side validation and audit — **without** changing CRM stage movement, without ProcessRun, without API/UI.

Empty overlay = current CRM behavior unchanged.

---

## Exact scope E1a

### In scope

| Deliverable | Detail |
|-------------|--------|
| ORM models | `ProcessTemplate`, `TenantProcessConfiguration`, `ProcessDefinitionVersion` |
| Alembic migration | `0019_process_overlay_e1a` → creates 3 tables only |
| Module package | `backend/app/modules/process_overlay/` |
| Seed catalog | Platform `process_templates` row(s), incl. `flexity_sales_intake` blueprint |
| Service layer | Catalog seed, config create, publish version, set active version, activate/deactivate config (state only) |
| Policy validation | Pydantic schema v1; stage-code validation against tenant pipeline |
| Audit | publish / activate / deactivate via existing `AuditRecorder` |
| Tests | Model invariants, publication flow, tenant isolation, migration up/down |

### Out of scope (explicit — see §14)

ProcessRun, transition enforcement, `workflows.service.move_stage` changes, routes, UI, tasks/approvals/SLA, ModuleGuard disable blocking (E1c), industry template hooks, production deploy.

---

## Relevant existing code (anchors)

| Area | Path | Reuse in E1a |
|------|------|--------------|
| Pipeline / Stage ORM | `backend/app/modules/workflows/models.py` | Read-only validation via `WorkflowRepository` |
| Pipeline tenant lookup | `backend/app/modules/workflows/repository.py` | `get_pipeline`, `get_pipeline_by_code`, stage codes |
| CRM movement (unchanged) | `backend/app/modules/workflows/service.py` | **Not modified** |
| Industry pipeline seed | `backend/app/modules/industry_templates/seed.py` | Reference only (`flexity_sales` stages) |
| Template apply (no hook) | `backend/app/modules/industry_templates/service.py` | **Not modified** — no auto overlay |
| Module catalog codes | `backend/app/modules/module_registry/seed.py` | Policy `module_requirements` uses `"crm"`, `"parties"` |
| Audit writer | `backend/app/modules/audit/recorder.py` | Publish / activation events |
| ORM registration | `backend/app/modules/models.py` | Add imports |
| Test DB bootstrap | `backend/tests/conftest.py` | Optional: seed process templates in fixture |
| Migration test pattern | `backend/tests/test_migration_0014_branches.py` | Copy pattern for 0019 |
| Booking module pattern | `backend/app/modules/booking/*` | Module layout reference |
| Branches module pattern | `backend/app/modules/branches/*` | Thin service/repository reference |

**Alembic naming convention (from 0018):** revision id ≤ 32 chars; docstring notes local/schema readiness.

---

## Entity design

### 1. ProcessTemplate (platform catalog)

**Needed in E1a:** **Yes** — gives stable FK + seed surface without tenant-fork Core.

| Aspect | Specification |
|--------|---------------|
| **Responsibility** | Platform-level blueprint catalog: which process exists, default pipeline code, starter policy blueprint, required modules. Not tenant runtime. |
| **Table** | `process_templates` |
| **Tenant ownership** | **None** (platform/global catalog, like `industry_templates` / `module_definitions`) |
| **Pipeline/Stage link** | `default_pipeline_code: str` — logical reference only (pipelines are tenant-scoped). No FK to `pipelines`. |
| **Deletion** | No hard delete in E1a. `is_active=false` soft retire. DB `ON DELETE RESTRICT` from tenant configs prevents orphan-breaking deletes. |

**Fields**

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID PK | PK | `UUIDPrimaryKeyMixin` |
| `code` | String(64) | UNIQUE, NOT NULL, indexed | e.g. `flexity_sales_intake` |
| `name` | String(255) | NOT NULL | |
| `description` | Text | NULL | |
| `default_pipeline_code` | String(64) | NOT NULL | e.g. `flexity_sales` |
| `default_policy_blueprint_json` | JSON | NOT NULL, default `{}` | Seed-only starter; **not** executable; copied/merged at publish input time in tests |
| `required_module_codes_json` | JSON | NOT NULL, default `[]` | e.g. `["crm", "parties"]` — module_registry codes |
| `is_active` | Boolean | NOT NULL, default true | |
| `created_at` / `updated_at` | timestamptz | NOT NULL | `TimestampMixin` |

**Statuses:** `is_active` boolean only (no lifecycle enum in E1a).

**Audit:** catalog seed changes are dev/test concern in E1a; no runtime API. Optional audit on manual template deactivate — defer.

---

### 2. TenantProcessConfiguration (tenant binding)

**Needed in E1a:** **Yes** — holds activation state + pointer to active published version.

| Aspect | Specification |
|--------|---------------|
| **Responsibility** | Bind one process template to one tenant pipeline; store activation state; point to active definition version for future runs (E1b). |
| **Table** | `tenant_process_configurations` |
| **Tenant ownership** | `tenant_id` NOT NULL; all reads/writes scoped by tenant |
| **Pipeline/Stage link** | FK `pipeline_id` → `pipelines.id`. Service **must** verify `pipeline.tenant_id == config.tenant_id`. |
| **Deletion** | No delete if versions exist (`ON DELETE RESTRICT` from versions). E1a: no delete API; orphan prevention via FK. |

**Fields**

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID PK | PK | |
| `tenant_id` | UUID FK | FK → `tenants.id` CASCADE, indexed | |
| `process_template_id` | UUID FK | FK → `process_templates.id` RESTRICT, indexed | |
| `pipeline_id` | UUID FK | FK → `pipelines.id` RESTRICT, indexed | Must belong to same tenant (service invariant) |
| `activation_state` | Enum | NOT NULL, default `INACTIVE` | `ProcessOverlayActivationState` |
| `active_definition_version_id` | UUID FK | FK → `process_definition_versions.id` SET NULL, nullable | At most one active version per config via single pointer |
| `created_at` / `updated_at` | timestamptz | NOT NULL | |
| `created_by_user_id` / `updated_by_user_id` | UUID | NULL | `AuditUserMixin` on config only |

**Unique constraints**

| Name | Columns | Purpose |
|------|---------|---------|
| `uq_tenant_process_config_tenant_template` | `(tenant_id, process_template_id)` | One config per template per tenant |
| `uq_tenant_process_config_tenant_pipeline` | `(tenant_id, pipeline_id)` | One overlay config per pipeline per tenant (E1) |

**Statuses — `ProcessOverlayActivationState` (new enum in `process_overlay/enums.py`)**

| Value | Meaning |
|-------|---------|
| `INACTIVE` | Default. Overlay metadata may exist; **no enforcement**, no side effects on CRM |
| `ACTIVE` | Flag only in E1a. Stored + audited; enforcement deferred to E1c |

**Critical invariant #1 (cross-tenant pipeline):**
On create/update, service loads pipeline via `WorkflowRepository.get_pipeline(tenant_id, pipeline_id)`. If missing → `NotFoundError`. Never accept `pipeline_id` without tenant match.

**Critical invariant #2 (template/pipeline alignment):**
`process_template.default_pipeline_code` must equal bound `pipeline.code`. Mismatch → `ProcessOverlayValidationError`.

---

### 3. ProcessDefinitionVersion (immutable published snapshot)

**Needed in E1a:** **Yes** — versioning + policy snapshot storage.

| Aspect | Specification |
|--------|---------------|
| **Responsibility** | Immutable published snapshot: policy, stage codes, module requirements, publish metadata. |
| **Table** | `process_definition_versions` |
| **Tenant ownership** | `tenant_id` NOT NULL (denormalized for isolation queries; must match parent config) |
| **Pipeline/Stage link** | `pipeline_id` + `pipeline_code` snapshot; `stage_codes_json` list; policy references stage **codes** only |
| **Deletion** | **No application delete** in E1a. Rows are append-only. Migration downgrade drops table (dev only). |
| **Immutability** | Repository exposes **no update** method. ORM `updated_at` omitted intentionally (publish-only row). |

**Fields**

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID PK | PK | |
| `tenant_id` | UUID FK | FK → `tenants.id` CASCADE, indexed | Must equal parent config `tenant_id` |
| `tenant_process_configuration_id` | UUID FK | FK → `tenant_process_configurations.id` RESTRICT, indexed | |
| `version_number` | Integer | NOT NULL | Starts at 1; monotonic per config |
| `pipeline_id` | UUID FK | FK → `pipelines.id` RESTRICT | Snapshot of pipeline at publish |
| `pipeline_code` | String(64) | NOT NULL | Denormalized snapshot |
| `stage_codes_json` | JSON | NOT NULL | Sorted unique list of allowed stage codes in this version |
| `policy_snapshot_json` | JSON | NOT NULL | Validated declarative policy (see §8) |
| `module_requirements_json` | JSON | NOT NULL, default `[]` | Copy from policy/template at publish |
| `published_at` | timestamptz | NOT NULL | Set at insert |
| `published_by_user_id` | UUID | NOT NULL | |
| `publish_reason` | Text | NOT NULL | Non-empty string required |
| `created_at` | timestamptz | NOT NULL | No `updated_at` — immutable row |

**Unique constraints**

| Name | Columns |
|------|---------|
| `uq_process_def_version_config_number` | `(tenant_process_configuration_id, version_number)` |

**Check constraints (DB + service)**

| Rule | Enforcement |
|------|-------------|
| `publish_reason` non-empty | Service + DB `CHECK (length(trim(publish_reason)) > 0)` |
| `version_number > 0` | DB CHECK |
| `stage_codes_json` is JSON array | Service validation |
| Tenant match | Service: `version.tenant_id == config.tenant_id == pipeline.tenant_id` |

**Active version rule (#4):**
Only one active version per configuration — enforced by **single nullable FK** `tenant_process_configurations.active_definition_version_id`.
`set_active_definition_version()` validates version belongs to same config and tenant.

**ProcessRun:** **Not included in E1a.** No table, no FK, no service.

---

## Policy snapshot (E1a — validation only, no execution)

Stored in `policy_snapshot_json`. Validated by Pydantic model `PolicySnapshotV1` in `process_overlay/policy_schema.py`.

### Allowed top-level shape

```json
{
  "schema_version": 1,
  "process_template_code": "flexity_sales_intake",
  "pipeline_code": "flexity_sales",
  "stage_codes": ["new_lead", "contacted", "diagnosis", "accepted", "rejected"],
  "transitions": [
    {
      "from_stage_code": "new_lead",
      "to_stage_code": "contacted",
      "conditions": {
        "required_fields": [],
        "required_roles": ["sales"],
        "requires_approval": false
      }
    }
  ],
  "module_requirements": ["crm"],
  "terminal_stage_codes": ["accepted", "rejected"]
}
```

### Rules (invariant #5, #6)

1. **Stage codes** — every code in `stage_codes`, `transitions`, `terminal_stage_codes` must exist on the bound pipeline at publish time (`WorkflowRepository` + stage list).
2. **Transition endpoints** — `from_stage_code` / `to_stage_code` ∈ `stage_codes`.
3. **No executable code** — Pydantic `extra=forbid` on all models; **denylist** keys: `script`, `expression`, `eval`, `exec`, `lambda`, `handler`, `code`, `sql`, `raw`, `template_engine`. Reject unknown condition keys (whitelist only).
4. **Conditions whitelist (E1a):** `required_fields`, `required_roles`, `requires_approval`, `required_task_codes`, `required_document_types` (latter two validated structurally only; no execution in E1a).
5. **Module codes** — must exist in `MODULE_DEFINITIONS` seed codes.
6. Policy is **data**, not code — no Jinja, no Python, no JS.

### JSON snapshot risks (§ rollback companion)

| Risk | Mitigation in E1a |
|------|-------------------|
| Schema drift | `schema_version` field; explicit Pydantic v1 class |
| Invalid stage codes | Publish-time pipeline validation |
| Silent typos | Fail publish with `ProcessOverlayValidationError` + structured errors |
| Code injection | Whitelist keys; forbid executable fields; never `eval`/`exec` |
| Blob growth | Reasonable max lengths: transitions list ≤ 100; reason ≤ 2000 chars |
| Tenant A policy leaking to tenant B | `tenant_id` on version + config scoping in repository |

---

## Model / service / repository boundaries

```
process_overlay/
├── models.py              # 3 ORM models
├── enums.py               # ProcessOverlayActivationState
├── exceptions.py          # ProcessOverlayValidationError, ProcessDefinitionImmutableError
├── schemas.py             # Pydantic DTOs for service I/O (internal/tests, not HTTP)
├── policy_schema.py       # PolicySnapshotV1 + validators
├── seed.py                # PROCESS_TEMPLATE_DEFINITIONS constant
├── repository.py          # DB access only, tenant-scoped queries
└── service/
    ├── catalog.py         # seed_templates(), get_template_by_code()
    ├── configuration.py   # create/get config, activate/deactivate (state only)
    └── publication.py     # publish_definition_version(), set_active_definition_version()
```

| Layer | Responsibility | Must NOT |
|-------|----------------|----------|
| **Repository** | CRUD queries, flush, tenant filters | Business validation, audit, pipeline loading |
| **Configuration service** | Tenant invariants, template/pipeline alignment, activation state, audit | Policy execution, WorkItem changes |
| **Publication service** | Policy validation, version numbering, immutability insert, active pointer update, audit | Transition enforcement |
| **WorkflowRepository** | Read pipeline/stages | Overlay persistence |
| **AuditRecorder** | Append audit rows | Validation |

**No routes** in E1a — services invoked from tests (and future internal scripts only).

---

## Validation and publication flow

### Flow A — Ensure catalog (test bootstrap / explicit seed)

```
ProcessOverlayCatalogService.seed_templates()
  → upsert process_templates from PROCESS_TEMPLATE_DEFINITIONS
  → idempotent by code
```

**Not** called from `IndustryTemplateService.apply_template()`.

### Flow B — Create tenant configuration

```
ProcessOverlayConfigurationService.create_configuration(
  tenant_id, process_template_code, pipeline_id, actor_user_id
)
  1. Load template by code; fail if inactive/missing
  2. Load pipeline via WorkflowRepository.get_pipeline(tenant_id, pipeline_id)
  3. Assert pipeline.code == template.default_pipeline_code
  4. Insert TenantProcessConfiguration(
       activation_state=INACTIVE,
       active_definition_version_id=NULL
     )
  5. Audit: entity_type="tenant_process_configuration", action=CREATE
  6. flush
```

### Flow C — Publish definition version

```
ProcessOverlayPublicationService.publish_definition_version(
  tenant_id, configuration_id, policy_input: PolicySnapshotV1,
  publish_reason, actor_user_id
)
  1. Load config scoped to tenant_id
  2. Load pipeline + stages (fresh)
  3. Validate policy_input.pipeline_code == pipeline.code == template.default_pipeline_code
  4. Validate policy_input.process_template_code == template.code
  5. Validate all stage codes exist on pipeline
  6. Validate transitions/endpoints/terminals
  7. Validate module_requirements against MODULE_DEFINITIONS
  8. version_number = repo.max_version_number(config_id) + 1  (or 1)
  9. INSERT ProcessDefinitionVersion(...) — no UPDATE path
  10. Audit: action=CREATE (or EXECUTE), entity_type="process_definition_version"
  11. Return version DTO
```

**Note:** Publish does **not** auto-set active version unless `set_active_on_publish=true` flag in service (default **false** in E1a tests; explicit separate call preferred for invariant clarity).

### Flow D — Set active version

```
ProcessOverlayPublicationService.set_active_definition_version(
  tenant_id, configuration_id, version_id, actor_user_id
)
  1. Load config (tenant scoped)
  2. Load version; assert version.tenant_process_configuration_id == config.id
  3. Assert version.tenant_id == tenant_id
  4. config.active_definition_version_id = version.id
  5. Audit: action=UPDATE, summary="active definition version set"
```

### Flow E — Activate / deactivate configuration (state only)

```
activate_configuration(...)   → activation_state=ACTIVE + audit
deactivate_configuration(...) → activation_state=INACTIVE + audit
```

**E1a guarantee:** These methods change **only** overlay config row + audit. No WorkItem, Pipeline, Task, or `move_stage` side effects.

---

## Migration structure

**File:** `backend/alembic/versions/20260717_0019_process_overlay_e1a.py`

| Property | Value |
|----------|--------|
| `revision` | `0019_process_overlay_e1a` |
| `down_revision` | `0018_mkt_storage_profiles` |
| Docstring | Local/schema readiness only; does not auto-create tenant configs; does not activate overlay |

### Migration order (upgrade)

1. Create enum `process_overlay_activation_state` (`INACTIVE`, `ACTIVE`) — `native_enum=False`, uppercase names (match 0018 convention).
2. Create table `process_templates`.
3. Create table `tenant_process_configurations` **without** FK to `process_definition_versions` yet.
4. Create table `process_definition_versions`.
5. Add FK `tenant_process_configurations.active_definition_version_id` → `process_definition_versions.id` ON DELETE SET NULL.
6. Create indexes as listed in entity sections.

### Downgrade (invariant #10)

1. Drop FK `active_definition_version_id`.
2. Drop `process_definition_versions`.
3. Drop `tenant_process_configurations`.
4. Drop `process_templates`.
5. Drop enum.

**Does not:** ALTER/DROP/UPDATE `pipelines`, `pipeline_stages`, `work_items`, or any CRM table. Existing CRM data untouched.

### ORM registration

Add to `backend/app/modules/models.py`:

```python
from app.modules.process_overlay.models import (  # noqa: F401
    ProcessDefinitionVersion,
    ProcessTemplate,
    TenantProcessConfiguration,
)
```

---

## Seed: `flexity_sales_intake`

**File:** `backend/app/modules/process_overlay/seed.py`

Catalog entry (constant → DB on seed):

| Field | Value |
|-------|--------|
| `code` | `flexity_sales_intake` |
| `default_pipeline_code` | `flexity_sales` |
| `required_module_codes_json` | `["crm", "parties"]` |
| `default_policy_blueprint_json` | E1 path only: stages `new_lead`, `contacted`, `diagnosis`, `accepted`, `rejected`; transitions matching architecture §9; **excludes** proposal/negotiation/conversion |

**Explicit non-behavior:**

- Seeding catalog does **not** create `TenantProcessConfiguration`.
- Applying industry template `flexity_sales_basic` continues to create pipelines only (existing behavior).
- No tenant gets `activation_state=ACTIVE` from seed/migration.

---

## Files to create

| Path | Purpose |
|------|---------|
| `backend/app/modules/process_overlay/__init__.py` | Package marker |
| `backend/app/modules/process_overlay/enums.py` | `ProcessOverlayActivationState` |
| `backend/app/modules/process_overlay/exceptions.py` | Domain errors |
| `backend/app/modules/process_overlay/models.py` | 3 ORM models |
| `backend/app/modules/process_overlay/schemas.py` | Internal DTOs |
| `backend/app/modules/process_overlay/policy_schema.py` | `PolicySnapshotV1` |
| `backend/app/modules/process_overlay/seed.py` | `PROCESS_TEMPLATE_DEFINITIONS` |
| `backend/app/modules/process_overlay/repository.py` | Tenant-scoped persistence |
| `backend/app/modules/process_overlay/service/__init__.py` | Service exports |
| `backend/app/modules/process_overlay/service/catalog.py` | Template seed/get |
| `backend/app/modules/process_overlay/service/configuration.py` | Config CRUD + activation |
| `backend/app/modules/process_overlay/service/publication.py` | Publish + set active version |
| `backend/alembic/versions/20260717_0019_process_overlay_e1a.py` | Migration |
| `backend/tests/test_process_overlay_e1a_models.py` | ORM / metadata / constraints |
| `backend/tests/test_process_overlay_e1a_publication.py` | Service flows + invariants |
| `backend/tests/test_migration_0019_process_overlay_e1a.py` | Alembic up/down isolation |

## Files to modify

| Path | Change |
|------|--------|
| `backend/app/modules/models.py` | Register 3 ORM models |
| `backend/tests/conftest.py` | Optional: call `ProcessOverlayCatalogService.seed_templates()` inside existing `seed_catalog` fixture |

## Files intentionally NOT touched

| Path | Reason |
|------|--------|
| `backend/app/modules/workflows/service.py` | No CRM movement change |
| `backend/app/modules/workflows/routes.py` | No API |
| `backend/app/modules/workflows/models.py` | No WorkItem changes |
| `backend/app/modules/industry_templates/service.py` | No auto-activation |
| `backend/app/modules/industry_templates/seed.py` | Pipeline seed unchanged |
| `backend/app/main.py` | No router |
| `backend/app/core/modules.py` | ModuleGuard blocking deferred to E1c |
| `backend/app/modules/module_registry/seed.py` | Optional later: `process_overlay` module definition — **not E1a** |

---

## Test matrix

| ID | Invariant | Test file | Assertion |
|----|-----------|-----------|-----------|
| T1 | ProcessTemplate registered in metadata | `test_process_overlay_e1a_models.py` | Tables in `Base.metadata` |
| T2 | Config unique per (tenant, template) | models | IntegrityError on duplicate |
| T3 | Config unique per (tenant, pipeline) | models | IntegrityError on duplicate |
| T4 | Version unique per (config, version_number) | models | IntegrityError on duplicate |
| T5 | Cross-tenant pipeline rejected | publication | `create_configuration` with other tenant's pipeline → error |
| T6 | Template/pipeline code mismatch rejected | configuration | template expects `flexity_sales`, pipeline `other` → validation error |
| T7 | Publish fails on unknown stage code | publication | stage code not on pipeline → validation error |
| T8 | Publish fails on transition to unknown stage | publication | bad edge → validation error |
| T9 | Publish fails on empty publish_reason | publication | validation error |
| T10 | Published version immutable | publication | repository update attempt → error / no update method |
| T11 | Version numbers monotonic | publication | publish twice → v1, v2 |
| T12 | Set active version same config only | publication | foreign version id → error |
| T13 | At most one active pointer | publication | setting v2 active replaces pointer; v1 row unchanged |
| T14 | Default activation INACTIVE | configuration | new config → INACTIVE |
| T15 | Activate/deactivate no WorkItem change | publication | create WorkItem, activate overlay, assert stage unchanged |
| T16 | No config → CRM unchanged | publication | move_stage works as before without overlay config |
| T17 | Policy rejects forbidden keys | publication | policy with `script` key → validation error |
| T18 | Tenant A cannot read tenant B config | publication | repo scoped query returns none |
| T19 | Migration upgrade creates 3 tables | migration | inspect tables exist |
| T20 | Migration downgrade drops overlay only | migration | pipelines/work_items counts unchanged |
| T21 | Industry template apply creates no overlay config | publication | apply template → zero `tenant_process_configurations` |
| T22 | Catalog seed idempotent | publication | seed twice → one row per code |

### Commands (after code approval)

```bash
cd backend
python -m pytest tests/test_process_overlay_e1a_models.py tests/test_process_overlay_e1a_publication.py -q
python -m pytest tests/test_migration_0019_process_overlay_e1a.py -q   # Postgres required
python -m compileall app/modules/process_overlay
```

---

## Implementation steps (ordered — after Approval Gate)

1. Create `process_overlay` package: enums, exceptions, policy_schema, seed constant.
2. Add ORM models + register in `app/modules/models.py`.
3. Write migration `0019_process_overlay_e1a` (3 tables, FK order as above).
4. Implement repository (tenant-scoped; no version update).
5. Implement catalog service + seed.
6. Implement configuration service (create, activate/deactivate).
7. Implement publication service (validate, publish, set active).
8. Wire audit calls.
9. Add model tests.
10. Add publication/integration tests (include WorkItem move_stage unchanged case).
11. Add migration test (up to 0019, down to 0018, CRM tables intact).
12. Optional: extend `conftest.seed_catalog` with process template seed.

---

## Rollback

| Level | Action |
|-------|--------|
| **Code rollback** | Revert commit(s) touching `process_overlay/*`, migration, models import, tests |
| **Schema rollback** | `alembic downgrade 0018_mkt_storage_profiles` — drops overlay tables only |
| **Data impact** | Overlay rows lost on downgrade; CRM/pipelines/work_items unaffected |
| **Forward again** | `alembic upgrade 0019_process_overlay_e1a` recreates empty overlay tables; re-seed catalog |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep into enforcement | Medium | High | No imports from publication into workflows service |
| Accidental template apply hook | Low | High | Explicit file denylist; test T21 |
| JSON policy complexity | Medium | Medium | Strict Pydantic v1 whitelist |
| Migration branch conflict (M8 branch) | Medium | Medium | Plan assumes head `0018`; rebase migration down_revision if needed before implement |
| `active_definition_version_id` circular FK | Low | Low | Two-step migration: tables → then FK |
| Enum naming drift | Low | Medium | Follow 0018 uppercase NAME storage |

---

## Explicit out of scope (E1a)

- ProcessRun / Process Instance binding
- Transition enforcement on `move_stage`
- HTTP routes / OpenAPI exposure
- UI / admin screens
- BPMN / visual editor
- Tasks, approvals, SLA, timers
- Finance / HR / Motivation
- ModuleGuard disable blocking
- Cross-tenant processes
- Industry template auto-provisioning of overlay config
- Production deploy / staging upgrade execution
- AI-autonomous transitions
- Migration of active runs between versions
- Arbitrary executable policy code

---

## Approval Gate before code

**Stop — do not write code until explicit approval of this E1a plan.**

Approver confirms:

- [ ] Three entities only (`ProcessTemplate`, `TenantProcessConfiguration`, `ProcessDefinitionVersion`); **no ProcessRun**
- [ ] Migration `0019_process_overlay_e1a` after `0018_mkt_storage_profiles`
- [ ] No changes to `workflows.service` / routes / industry template apply
- [ ] Activation stored but does not affect CRM in E1a
- [ ] Policy snapshot declarative-only validation
- [ ] Test matrix T1–T22 acceptable

**After approval:** implement E1a in a single focused commit series; then request E1b implementation plan.

---

## Final summary

| Item | Value |
|------|--------|
| **Exact scope E1a** | Config + versioning skeleton: 3 tables, seed catalog, services, tests; zero CRM behavior change |
| **Models / tables** | `process_templates`, `tenant_process_configurations`, `process_definition_versions` |
| **ProcessRun** | **Not in E1a** (E1b runtime slice) |
| **Files to create** | 16 new files (see § Files to create) |
| **Files to modify** | `backend/app/modules/models.py`; optionally `backend/tests/conftest.py` |
| **Migration order** | enum → process_templates → tenant_process_configurations → process_definition_versions → FK active_definition_version_id |
| **Test matrix** | T1–T22 (22 cases) |
| **Out of scope** | Enforcement, Run, API, UI, deploy, CRM hooks |
| **Approval Gate** | Required before any code |
| **staged** | **0** |

---

## Finish block

1. **Files changed:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1a-implementation-plan.md` (created)
2. **Files intentionally not touched:** all backend production code
3. **Tests/checks run:** Alembic head verified (`0018_mkt_storage_profiles`); `staged=0`
4. **Risks:** migration branch divergence if not on latest head; JSON policy scope creep
5. **Next safe step:** HQ approves this E1a plan → then implement E1a code in isolated commit(s)
6. **Handoff:** recommended after E1a code complete; not required for plan-only step
