# Flexity Process Overlay E1 — Architecture Plan

**Date:** 2026-07-17
**Type:** documentation_only architecture plan
**Project:** Flexity
**Category:** platform_core (thin overlay) + reuse of universal CRM (`workflows`)
**Status:** draft — **Approval Gate before any code**
**Parent:** `docs/ai/reviews/2026-07-17-flexity-existing-process-architecture-reconciliation.md` (accepted)
**Code / migrations / API / UI / deploy:** none in this document
**Git staged files:** 0

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | documentation_only (architecture plan for future platform_core overlay) |
| Risk level | low (docs only) |
| Intended scope | this plan file only |
| Forbidden scope | production code, migrations, API, UI, deploy, BPMN, tenant-fork Core |
| Required plan | this document |

---

## 1. Executive decision

HQ decision (binding for E1):

1. **Do not** create a separate universal Process Engine.
2. Design a **thin Process Overlay** on top of existing foundations:
   - Party
   - WorkItem
   - tenant Pipeline / Stage
   - tasks / activities
   - audit
   - ModuleGuard / entitlements
   - industry templates
3. **WorkItem is process context**, not an automatic Process Instance.
4. **Do not** create tenant-fork Core.
5. Preserve **CRM backward compatibility**; tenants without overlay keep current behavior.
6. First concrete process: constrained path on existing pipeline `flexity_sales`
   (`new_lead` → `contacted` → `diagnosis` → `accepted` | `rejected`).
   Stages `proposal_*`, `negotiation`, `converted_to_tenant` remain in the pipeline for CRM display/manual use, but are **out of E1 mandatory process path**.

**Recommended runtime model for E1:** **Variant B** — thin **Process Run / Binding** linked to WorkItem (see §4–§5).

---

## 2. Existing reusable foundation

| Foundation | Role today | Reuse in overlay |
|------------|------------|------------------|
| **Party** | Counterparty / person | Process subject / party context |
| **WorkItem** | CRM case on pipeline | **Business context** of a process; FK target for Process Run |
| **Pipeline / Stage** | Tenant-owned funnel + stages | Display + stage movement target; **not** process versioning |
| **Task / Activity** | Execution + communication trail | Required work evidence; activity log stays SoT for actions |
| **Audit** | Significant change trail | Overlay publishes / activates / transitions / policy denials |
| **ModuleGuard / entitlements** | Capability gates | Policy may require modules; cannot deactivate if active policy depends |
| **Industry templates** | Seed pipelines (e.g. `flexity_sales`) | Source of **Process Template** defaults (config, not runtime engine) |
| **workflows service** | `move_stage`, close/reopen, create | Future enforcement hook point (after activation only) |

**Explicit non-reuse as “engine”:** renaming `workflows` to Process Engine — rejected.

---

## 3. Boundary and ownership

| Component | Responsibility | Owns | Does not own |
|-----------|----------------|------|--------------|
| **WorkItem** | Business context of work (party, assignee, status, current stage, custom fields) | CRM case data | Process version, transition policy, activation |
| **Pipeline / Stage** | Stages and **display** of work movement | Stage codes, sort, terminal flags | Immutable process version, allowed edges, required evidence |
| **Process Overlay** | Versioned definition, transition policy, mandatory conditions, activation / deactivation | Template → tenant config → definition version → run binding → policy evaluation | Domain document/finance ops; UI designer; BPMN |
| **Tasks / Activities** | Execution and recording of actions | Task lifecycle, activity notes/calls | Policy authorship; stage graph versioning |
| **Domain modules** | Business operations (documents, finance, consulting import, etc.) | Domain entities and ops | Generic process runtime |
| **Audit** | History of significant changes | Audit events | Business decision logic |
| **ModuleGuard / Entitlements** | Whether tenant may use a capability | Module enablement graph | Stage movement UX |

**Ownership principle:** Overlay **enforces** when activated; Pipeline **shows** stages; WorkItem **carries** the case; Tasks **prove** work; Domain modules **do** business ops; Audit **records**; ModuleGuard **gates** capabilities.

---

## 4. Options comparison

### Variant A — Process fields on WorkItem

Add columns / JSON on `WorkItem` (e.g. `process_definition_version_id`, `process_state`, `overlay_active`).

| Criterion | Assessment |
|-----------|------------|
| Complexity | Low initially |
| Backward compatibility | Risky — every WorkItem looks “process-aware”; hard to keep null semantics clean |
| Versioning | Awkward — version on the case row mixes CRM and process |
| Multiple processes per WorkItem | **Poor** — one set of fields |
| Audit | Need careful separation from CRM stage moves |
| Tenant isolation | Feasible via existing `tenant_id` |
| Extension | Couples Core CRM entity to overlay forever |
| Core overload risk | **High** — WorkItem becomes god-object |

### Variant B — Thin Process Run / Binding (recommended)

Separate entity: references WorkItem, pins Process Definition Version, holds execution state; optional 1:N later.

| Criterion | Assessment |
|-----------|------------|
| Complexity | Medium (one new thin runtime table + config tables) |
| Backward compatibility | **Best** — no Run ⇒ no overlay semantics |
| Versioning | Clean pin of immutable definition version on the Run |
| Multiple processes per WorkItem | **Supported by design** (E1 may still enforce 0..1 active Run) |
| Audit | Run create / transition / deny / deactivate as first-class events |
| Tenant isolation | Run and definitions scoped by `tenant_id` |
| Extension | Overlay grows without bloating WorkItem |
| Core overload risk | **Low–medium** — Core stays CRM; overlay is additive |

### Variant C — Pipeline / Stage only

Encode all process meaning into Pipeline/Stage (and maybe stage metadata JSON).

| Criterion | Assessment |
|-----------|------------|
| Complexity | Low short-term |
| Backward compatibility | Confusing — every pipeline change becomes “process change” |
| Versioning | **Weak** — stages mutate in place; no immutable snapshot |
| Multiple processes | Poor / confusing |
| Audit | Blurs CRM stage rename vs process publish |
| Tenant isolation | OK |
| Extension | Forces Pipeline into BPM-lite |
| Core overload risk | **High** — overloads CRM display model |

### Recommendation

**Variant B** for E1.

- WorkItem remains CRM context.
- Overlay attaches only when a **Process Run** exists (and tenant+pipeline activation is on).
- Pipeline/Stage remain display + move targets.
- Avoids tenant-fork and avoids Process Engine platform.

---

## 5. Recommended minimal model

### Concepts — necessity check

| Concept | Needed in E1? | Rationale |
|---------|---------------|-----------|
| **Process Template** | **Yes (catalog)** | Platform/industry seed (e.g. `flexity_sales_intake_v1` mapping). Not a BPMN designer. |
| **Tenant Process Configuration** | **Yes** | Binds template to tenant + pipeline; holds activation flags. |
| **Process Definition Version** | **Yes** | Immutable published snapshot of policy + stage mapping for that config. |
| **Process Run / Binding** | **Yes** | Opt-in runtime link WorkItem ↔ pinned definition version + state. |
| **Transition Policy** | **Yes (as data inside version)** | Allowed edges + conditions; evaluated server-side. Not a separate free-floating entity unless storage needs it. |
| **Transition History** | **Partial** | Prefer **audit (+ optional activity)** first; dedicated history table only if audit cannot answer “who moved under which version”. E1 default: **audit-first**, optional thin history later. |
| **Activation State** | **Yes (on Tenant Process Configuration)** | `inactive` / `active` (and optionally `draft` for unpublished edits). Not a WorkItem flag. |

**Reuse instead of inventing:**

- Stage **codes** and names → existing `Stage`
- Case data → `WorkItem`
- Work evidence → `Task` / `Activity`
- Capability checks → `ModuleGuard`

**Do not create entities only to match names.**

---

## 6. Data model proposal — conceptual only

> Conceptual. No migrations. No ORM. Names are working titles.

```
ProcessTemplate (platform / industry catalog)
  - code (e.g. flexity_sales_intake)
  - name, description
  - default_pipeline_code (e.g. flexity_sales)
  - default_policy_blueprint (JSON conceptual)

TenantProcessConfiguration (per tenant)
  - tenant_id
  - process_template_code (or FK)
  - pipeline_id (tenant Pipeline, typically flexity_sales)
  - activation_state: inactive | active
  - active_definition_version_id (nullable until first publish)
  - created/updated metadata

ProcessDefinitionVersion (immutable)
  - tenant_id
  - tenant_process_configuration_id
  - version_number
  - published_at, published_by, publish_reason
  - stage_code_set / mapping snapshot (codes that exist on pipeline at publish)
  - transition_policy_snapshot (JSON): edges + conditions
  - module_requirements_snapshot
  - is_immutable = true after publish

ProcessRun (binding)
  - tenant_id
  - work_item_id
  - process_definition_version_id  (pinned)
  - tenant_process_configuration_id
  - run_state: active | completed | cancelled | superseded_inactive
  - started_at, completed_at
  - current_stage_code (cache/mirror of WorkItem.stage for convenience; WorkItem.stage remains CRM SoT for display)
  - E1 constraint: at most one active ProcessRun per WorkItem (relax later)
```

**Transition Policy** lives **inside** `ProcessDefinitionVersion` snapshot (not a mutable live table that changes under running runs).

**Transition History:** E1 — rely on **audit** events keyed by `work_item_id` + `process_run_id` + `definition_version_id`. Dedicated table = later slice if needed.

---

## 7. Versioning

### What is versioned

Immutable snapshot of:

1. Allowed stage codes referenced by the process (subset of pipeline stages).
2. Transition edges (from → to).
3. Conditions per edge (required fields, tasks, documents, roles, approval flag, module deps).
4. Terminal / completion rules.
5. Module/capability requirements for enforcement.

**Not versioned as process definition:** Party data, Task content, Activity text, finance documents themselves.

### Immutable snapshot

- Editing a draft config does **not** change published versions.
- **Publish** creates a new `ProcessDefinitionVersion` row (or equivalent) that is read-only.
- Running ProcessRuns keep their **pinned** version_id forever (E1: **no migration of active runs** between versions).

### Link to tenant Pipeline / Stage

- Configuration binds to a **pipeline_id**.
- Snapshot stores **stage codes** (stable), not only stage UUID (IDs can be recreated on reseed).
- Publish validation: all referenced codes must exist on that pipeline at publish time.
- Pipeline may still contain extra stages (proposal, negotiation, …) unused by E1 process path.

### New WorkItems and active version

- Creating a WorkItem **does not** auto-create a ProcessRun.
- ProcessRun is created only when:
  - tenant config `activation_state = active`, **and**
  - an explicit start rule fires (e.g. WorkItem created on that pipeline with stage `new_lead`, or operator “Start process”), **and**
  - policy/product rule for E1 says auto-start for that template.
- New runs pin `active_definition_version_id` at start time.

### Already running processes

- Keep pinned version.
- Continue evaluating transitions against that snapshot.
- Pipeline UI may still show other stages; overlay only enforces edges in the pinned policy when Run is active.

### Rollback of **new** starts to previous version

- Allowed by setting `active_definition_version_id` back to a previous published version (or publishing a copy).
- Does **not** rewrite existing Runs.
- Requires publish metadata / admin action with reason.

### Publish metadata

Store on each Definition Version:

- `published_by` (user id)
- `published_at`
- `publish_reason` (required non-empty string for E1)

---

## 8. Transition policy

### Evaluation locus

**Server-side only** (workflows/service or overlay service called from the same path as `move_stage`).
Frontend must not duplicate allow/deny rules as source of truth.

### Policy dimensions (per edge `from_stage_code` → `to_stage_code`)

| Dimension | E1 support |
|-----------|------------|
| Allowed directions | Explicit edge list; deny everything else when overlay enforces |
| Required data | WorkItem fields / custom_fields keys |
| Required tasks | Open/completed task codes or “at least one completed task of type X” (minimal) |
| Required documents | Optional stub: “document of type X exists” only if documents module linked; else defer |
| Required role | Role codes / permissions check |
| Approval | **Single-level flag only** in E1 (approve required yes/no); no multi-level chain |
| Module / capability deps | Module codes must be enabled |
| Success result | Update WorkItem.stage (+ optional status); Activity/audit; Run state if terminal |
| Denial error | Stable error code + human message (e.g. `PROCESS_TRANSITION_DENIED`) listing failed conditions |

### Application rules

1. If tenant config inactive **or** WorkItem has **no** active ProcessRun → **legacy CRM** `move_stage` behavior (no edge policy).
2. If active Run exists → evaluate pinned policy; on deny, **no** stage change.
3. Same rules for API and any future UI.
4. `close_work_item` / `reopen_work_item` must either:
   - map onto allowed terminal transitions, or
   - remain legacy until overlay explicitly covers them (E1 should define mapping for `rejected` / reopen to `new_lead` under policy).

---

## 9. First `flexity_sales` process

### Process identity (conceptual)

- **Template code:** `flexity_sales_intake` (working name)
- **Pipeline:** existing `flexity_sales`
- **E1 path stages:** `new_lead` → `contacted` → `diagnosis` → (`accepted` | `rejected`)
- **Pipeline stages not in E1 mandatory path:** `proposal_prepared`, `proposal_sent`, `negotiation`, `converted_to_tenant`
  - Remain in CRM pipeline.
  - Under active Run + enforcement: moves onto these stages are **denied by E1 policy** (or only allowed via explicit “exit overlay / cancel run” — prefer **deny** in E1 to keep path simple).
  - When overlay inactive / no Run: CRM can still move there (compatibility).

### Start

- Preconditions: TenantProcessConfiguration active; published Definition Version exists; WorkItem on `flexity_sales`.
- Auto-start (recommended E1 default for this template): when WorkItem is created at `new_lead` **and** config active → create ProcessRun pinned to active version.
- Manual start: optional later; not required if auto-start defined.
- Existing WorkItems at any stage: **no** auto Run (see §10).

### Allowed transitions (E1)

```
new_lead      → contacted
contacted     → diagnosis
diagnosis     → accepted
diagnosis     → rejected

# Optional E1a/E1b stretch (document in policy, implement only if approved):
# contacted → new_lead (reopen contact) — default OFF
# diagnosis → contacted — default OFF
```

Terminal:

- `accepted` → Run `completed` (success)
- `rejected` → Run `completed` (lost/reject)

No E1 edges into proposal/negotiation/conversion.

### Minimal mandatory conditions (starter)

| Edge | Minimal conditions (E1 proposal) |
|------|----------------------------------|
| `new_lead` → `contacted` | Party linked **or** contact channel recorded (activity of type call/email/meeting **or** non-empty note). Role: sales / tenant admin. |
| `contacted` → `diagnosis` | At least one Activity since start **or** completed Task `qualify_lead` (if task created). Role: sales. |
| `diagnosis` → `accepted` | Custom field or note capturing diagnosis outcome (minimal: non-empty activity “diagnosis summary”). Role: sales or manager. Approval flag: optional OFF by default. |
| `diagnosis` → `rejected` | Disposition / reason required (reuse existing custom field `disposition` where present). Role: sales. |

Exact field keys finalized in implementation slice — keep **minimal**.

### Roles

- Reuse existing tenant roles / permissions; do not invent HR matrix.
- E1: `sales`-capable user + tenant admin bypass for config publish only (not for skipping policy unless explicit admin override capability — **default no silent bypass**).

### Tasks

- Optional seeded task templates on start: e.g. `first_contact`, `run_diagnosis` — **not mandatory to implement all in E1a**.
- Policy may require task completion only after task templates exist.

### Events (audit / activity)

- `process_run.started`
- `process_transition.allowed` / `.denied`
- `process_run.completed`
- `process_config.activated` / `.deactivated`
- `process_definition.published`

### Completion

- Entering `accepted` or `rejected` under policy completes the Run.
- WorkItem status may map to existing `won`/`lost`/`closed` patterns without new status enum in E1 if avoidable.

### Behavior of existing WorkItems

- No Run created retrospectively.
- Stage moves continue under legacy CRM until a Run is explicitly started (out of E1 auto-backfill) or overlay remains inactive.

---

## 10. Backward compatibility

| Rule | Behavior |
|------|----------|
| Tenant without active Process Overlay | Identical to today |
| Existing WorkItems | No new semantics automatically; no auto Process Instance |
| CRM stage moves | Unchanged until enforcement path is active for that WorkItem (active config **and** active Run) |
| Activation | Separate admin action per tenant/pipeline (TenantProcessConfiguration) |
| Deactivation | Stops **enforcement for new actions**; does not delete versions, runs, or audit |
| Runs after deactivation | Existing Runs: either freeze (deny further overlay transitions) **or** allow legacy moves — **E1 choice: freeze overlay transitions + allow legacy CRM move only if product sets `legacy_escape=true`; default freeze with clear error, admin can deactivate then use documented escape** |
| Module disable | If active published policy lists module X as required, ModuleGuard / disable API must **block** with clear error until config deactivated or version without dep published |

---

## 11. Dependencies and module guards

- Overlay enforcement may declare required modules in definition snapshot (e.g. `workflows` always; `documents` only if document conditions used).
- E1 `flexity_sales_intake` should depend only on **workflows** (+ parties) by default — **no** finance/HR requirement.
- ModuleGuard remains SoT for enablement; overlay **reads** it, does not replace it.
- Industry template seeds Process Template defaults; does not fork Core.

---

## 12. Risks

| Risk | Mitigation |
|------|------------|
| Accidental Process Engine scope creep | Hard out-of-scope list; Approval Gate; thin Variant B only |
| WorkItem treated as Instance | Explicit Run binding; no auto-semantics on old rows |
| Breaking CRM for all tenants | Activation opt-in; default inactive |
| Pipeline stages vs process path confusion | Document E1 subset; deny non-path edges only when Run active |
| Duplicate rules in frontend | Server-only policy evaluation |
| Version drift vs live Stage rows | Snapshot by **code**; validate on publish |
| close/reopen hardcoded `rejected`/`new_lead` | Map into policy in same slice that hooks `move_stage` |
| Overloading audit | Stable event types; avoid logging every read |
| Multiple processes later | Variant B allows 1:N; E1 keeps 0..1 active Run |

---

## 13. MVP scope (E1)

Documentation + (after approval) minimal implementation slices that deliver:

1. Conceptual model Variant B.
2. Tenant activation inactive by default.
3. Publish immutable Definition Version with publish metadata.
4. ProcessRun create on start rule for `flexity_sales_intake`.
5. Server-side transition policy for E1 edges only.
6. Audit events for publish / activate / transition allow|deny / complete.
7. Module dependency check on deactivate module when policy requires it.
8. Tests per slice (below).
9. **No UI**, no BPMN, no deploy.

---

## 14. Explicit out of scope

- Visual editor / BPMN / arbitrary scripts
- Parallel branches / join-fork
- Complex timers / SLA engine
- Multi-level approval chains
- AI-autonomous transitions
- Finance / HR / Payroll / Motivation implementation
- Cross-tenant processes
- Migration of active Runs between versions
- UI / production / deploy
- Tenant-fork Core
- Universal Process Engine product
- Making every WorkItem a Process Instance
- Mandatory inclusion of proposal / negotiation / tenant conversion in E1 path

---

## 15. Suggested implementation slices (after Approval Gate)

### E1a — Config + versioning skeleton (no enforcement)

- Process Template catalog (seed/code constants) + TenantProcessConfiguration + ProcessDefinitionVersion publish
- Activation state inactive by default
- No change to `move_stage` behavior yet
- Tests: publish immutability, tenant isolation, activation flags

### E1b — ProcessRun + start rule + audit

- Create Run on qualifying new WorkItem when config active
- No retrospective Runs
- Audit `process_run.started`
- Tests: no Run when inactive; pin version; one active Run per WorkItem

### E1c — Transition enforcement hook

- Hook server stage-move path: if active Run → evaluate pinned policy
- Deny non-edges and failed conditions with stable errors
- Complete Run on `accepted`/`rejected`
- ModuleGuard block when active policy depends on module
- Tests: allow path; deny skip; legacy path without Run; deactivate stops enforcement for new checks per §10

**Smallest first code slice after approval:** **E1a only.**

---

## 16. Tests required by slice

### E1a

- Tenant A cannot read/write tenant B configuration/versions
- Publish creates immutable version with author/date/reason
- Active version pointer updates without mutating old versions
- Default activation = inactive
- Publish fails if referenced stage codes missing on pipeline

### E1b

- Inactive config → WorkItem create → **zero** ProcessRuns
- Active config + new WorkItem on `new_lead` → one Run pinned to active version
- Pre-existing WorkItem unchanged (no Run)
- Second start attempt does not create second **active** Run (E1)

### E1c

- Active Run: `new_lead`→`contacted` allowed under minimal conditions
- Active Run: `new_lead`→`accepted` denied
- Active Run: `diagnosis`→`proposal_sent` denied
- No Run: same moves behave as legacy CRM
- Denied transition emits audit + does not change stage
- Module disable blocked while active policy requires module

---

## 17. Approval Gate before any code

**Stop here until explicit user approval.**

Before code, approve:

1. Variant **B** (Process Run / Binding).
2. E1 process path on `flexity_sales` as specified.
3. Slice order E1a → E1b → E1c.
4. No UI / no migrations outside approved slice plans.
5. Confirmation that WorkItem is **not** auto Process Instance.

After approval, next artifact should be a **narrow E1a implementation plan** (exact files, migration yes/no decision, test commands) — still separate from this architecture plan.

---

## Final summary (for HQ)

| Item | Value |
|------|--------|
| **Recommended variant** | **B** — thin Process Run / Binding |
| **Presumed entities (not implemented)** | ProcessTemplate, TenantProcessConfiguration, ProcessDefinitionVersion, ProcessRun; Transition Policy as version snapshot; Activation on config; Transition History = audit-first |
| **Reused** | Party, WorkItem, Pipeline/Stage, Task/Activity, Audit, ModuleGuard, industry template pipeline seed `flexity_sales` |
| **Created new (future)** | Overlay config + immutable versions + Run binding + server policy evaluation |
| **Smallest first code slice** | **E1a** — config/version skeleton, no enforcement |
| **staged** | **0** |

---

## Finish block

1. **Files changed:** `docs/ai/plans/2026-07-17-flexity-process-overlay-e1-architecture-plan.md` (created)
2. **Files intentionally not touched:** all production code, migrations, API, UI, deploy, reconciliation review (accepted as-is)
3. **Tests/checks run:** existence of parent reconciliation; `staged=0`
4. **Risks:** scope creep into Process Engine if Approval Gate skipped; ambiguity on post-deactivation escape hatch (documented default)
5. **Next safe step:** user reviews and **approves** this architecture plan; then request E1a implementation plan only
6. **Handoff:** optional after approval; not required for docs-only step
)
