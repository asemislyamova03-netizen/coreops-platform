# Review: Flexity existing process architecture reconciliation

**Date:** 2026-07-17
**Project:** Flexity / `coreops-platform`
**Category:** `documentation_only` / architecture reconciliation
**Risk:** medium (product direction; no code in this task)
**Method:** read-only docs + code inspection (`rg`, models/services). Old docs not treated as truth without code check.
**Scope:** no code, no migrations, no API/UI/deploy changes, no new Process Engine design from scratch, **no implementation plan**.

**Product frame under review:**

- Module = what the system can do.
- Process = sequence, roles, conditions, actions, module links.
- Process levels: (1) Process Template → (2) Tenant Process Configuration → (3) Process Definition Version → (4) Process Instance.
- Client-specific process must **not** fork Core.
- Prefer existing Party, WorkItem, CRM stages, tasks, documents, events, module controls, tenant isolation.

---

## Task Classification

| Field | Value |
|-------|-------|
| Project | Flexity |
| Category | `documentation_only` |
| Risk | medium |
| Forbidden | code, migrations, Process Engine greenfield, implementation plan |

---

## 1. File map (relevant)

### Architecture / product docs

| Path | Role |
|------|------|
| `docs/ai/PRODUCT_ARCHITECTURE.md` | Layered Core → modules → templates → tenant customization; lists CRM/workflows as universal |
| `docs/FLEXITY_SALES_TENANT_BOOTSTRAP_PLAN.md` | Sales funnel via industry template + pipelines |
| `docs/ai/plans/2026-07-10-core-crm-e1-lead-disposition-implementation-plan.md` | Disposition / stage moves |
| `docs/FLEXITY_LEAD_PROCESSING_WORKFLOW.md` | Operational lead narrative (verify vs code) |

### Core / tenancy / modules

| Path | Role |
|------|------|
| `backend/app/core/modules.py` | `ModuleGuard`: enablement, mode, **dependency check** |
| `backend/app/core/entitlements.py` | Subscription **features** + module gate |
| `backend/app/modules/module_registry/{models,service,seed}.py` | `ModuleDefinition`, `TenantModule`, deps JSON, provisioning |
| `backend/app/modules/tenants/models.py` | Tenant, `TenantSettings` (labels + industry_config JSON) |
| `backend/app/modules/subscriptions/models.py` | Plan / Feature / entitlements |
| `backend/app/modules/industry_templates/{seed,service}.py` | Template apply: modules, **pipelines/stages**, docs, catalog |

### Parties / CRM / workflows

| Path | Role |
|------|------|
| `backend/app/modules/parties/models.py` | Party (+ contacts/addresses elsewhere) |
| `backend/app/modules/workflows/models.py` | Pipeline, PipelineStage, WorkItem, Participant, Activity, Note, Task, Reminder |
| `backend/app/modules/workflows/service.py` | CRUD, `move_stage`, close/reopen disposition, tasks/activities |
| `backend/app/modules/workflows/{routes,schemas,repository}.py` | HTTP/API surface |

### Events / audit / approvals / integrations

| Path | Role |
|------|------|
| `backend/app/modules/audit/{models,recorder}.py` | AuditLog, DataAccessLog, SecurityEvent |
| `backend/app/modules/documents/models.py` | DocumentInstance, SignatureRequest statuses |
| `backend/app/modules/marketing/service/approval.py` | Marketing pack approval/preflight (domain-specific) |
| `backend/app/modules/ai/models.py` | AIApproval / AIActionProposal |
| `backend/app/modules/integrations/models.py` | IntegrationConnection, SyncJob, WebhookEvent |

### Finance / “HR / Motivation”

| Path | Role |
|------|------|
| `backend/app/modules/finance/` | Invoices, payments — **present** |
| `backend/app/modules/accounting/` | Legal entities / tax profiles — **present** |
| HR / payroll / motivation packages | **Absent** as modules under `backend/app/modules/` (listed in PRODUCT_ARCHITECTURE as future universal modules) |

---

## 2. Mechanism status (docs vs code)

| Mechanism | Status | Evidence (short) |
|-----------|--------|------------------|
| **Party** | **implemented and used** | Models + service/routes; CRM/public leads/templates depend on it |
| **WorkItem** | **implemented and used** | Central CRM entity; console CRM board; linked to party, pipeline, stage |
| **CRM pipelines & stages** | **implemented and used** | `Pipeline` / `PipelineStage` tenant-scoped; seeded via industry templates (`flexity_sales`, kindergarten, etc.) |
| **Status transitions (WorkItem.status)** | **implemented partially** | Enum OPEN/IN_PROGRESS/WON/LOST; set opportunistically on `move_stage` / close / reopen — **no transition graph table** |
| **Stage moves** | **implemented partially** | `move_stage` allows any stage in same pipeline (sort_order not enforced as FSM); terminal stages flip status heuristically by **stage code** |
| **Workflows / processes (generic engine)** | **absent** as Process Template/Instance layer; **CRM pipeline used as stand-in** | Module named `workflows` but implements CRM pipeline semantics |
| **Tasks & activities** | **implemented and used** (basic) | Create on work item; Task has `due_at`; Activity timeline |
| **Notes** | **implemented partially** | Model exists; lighter API surface than work items |
| **Reminders** | **implemented partially / barely used** | Model + enum present; **no Reminder create/run service** found in workflows service |
| **Events / audit** | **implemented and used** (audit trail) | `AuditRecorder` on CRM actions; SecurityEvent on auth; **not** a general domain event bus |
| **Approvals** | **implemented partially / domain-siloed** | Documents signatures; Marketing pack approval; AI approvals — **no universal Process Approval entity** |
| **SLA / timers** | **absent** as SLA engine; **partial** due dates | Task.`due_at`, Reminder.`remind_at` without scheduler/SLA policy |
| **Modules / capabilities** | **implemented and used** | Registry + TenantModule + ModuleGuard + dependencies_json |
| **Feature flags / entitlements** | **implemented and used** | Subscription Feature + `require_feature` / plan checks |
| **Tenant configuration** | **implemented partially** | TenantSettings labels/industry_config; TenantModule.settings_json; pipeline rows per tenant — **not** versioned process definitions |
| **Templates & versioning** | **implemented partially** | Industry templates seed pipelines/modules (snapshot apply); **no versioned Process Definition**; document templates exist separately |
| **Automation** | **absent / stubby** | No process automation engine; AI proposals exist separately; integrations SyncJob/WebhookEvent are integration-oriented |
| **Integrations** | **implemented partially** | Models + services; not wired as process actions |
| **Finance hooks** | **implemented partially** | Finance module exists; **not** invoked as process-step actions from CRM |
| **HR / Motivation hooks** | **documented only / absent in code** | PRODUCT_ARCHITECTURE lists HR/payroll; no module package |

---

## 3. Answers to HQ questions

### Is there already a universal process foundation, or only CRM pipeline?

**Only CRM pipeline + WorkItem context today.**
The package `workflows` is the CRM operational model (pipeline/stage/work item/task/activity), not a multi-module Process Engine with Template → Tenant Config → Version → Instance.

### Can WorkItem be the context of a Process Instance?

**Yes — strongest reuse candidate.**
WorkItem already has: `tenant_id`, `pipeline_id`/`stage_id`, `primary_party_id`, participants, tasks, activities, custom_fields_json, status.
A future Process Instance can **reference** WorkItem as business context (or treat one WorkItem run as the instance) without inventing a parallel “case” entity first.
Caveat: WorkItem today is tightly coupled to **one pipeline**; multi-module processes may need an optional process-definition link later (extend, not fork Core).

### Can current pipeline/stage/status models be the basis for process stages?

**Yes for stage-like UX and tenant-specific stage lists; no as a full process FSM.**
Reusable: tenant-scoped stages, ordering (`sort_order`), terminal flags, template-seeded defaults (`flexity_sales` already has `new_lead` → `diagnosis` → …).
Not sufficient alone: no typed transitions, guards, roles-per-transition, multi-module actions, versioning.

### Where do transition rules live now?

**In application code + conventions, not data:**

1. `WorkflowService.move_stage` — any stage in pipeline; terminal code heuristics (`lost`/`cancelled`/`rejected` → LOST else WON).
2. `close_work_item` / `reopen_work_item` — hardcoded stage codes `rejected` / `new_lead` + disposition in `custom_fields_json`.
3. Industry template seed — defines stage **catalog**, not allowed edges.
4. No `allowed_transitions` table/config found (`rg` empty).

### Is there tenant-specific stage/process configuration?

**Stages/pipelines: yes (tenant rows).**
Created/copied via industry template apply; CRUD for pipelines exists.
**Process Template / Definition Version: no.**
TenantSettings / TenantModule.settings_json can hold opaque JSON but are **not** a process configuration model.

### How do module dependencies / capabilities work?

**Implemented:**

- `ModuleDefinition.dependencies_json.required`
- `ModuleGuard.assert_dependencies` on enable
- Runtime `require_module` / entitlements `assert_feature` (feature may require module)

This is the right control plane for “module defines capability”; processes should **call** modules behind these gates, not reimplement them.

### Is there an event model that can be extended?

**Partial.**

- **AuditLog** — append-only business/security trail (good for compliance, weak as automation trigger).
- **WebhookEvent / SyncJob** — integration ingress/egress.
- **No** first-class domain Event → Process Trigger registry.

Extension path: introduce process-oriented domain events **or** thin subscription on audit/outbox later — **new/extend**, do not pretend AuditLog is a process engine.

### What can be reused without changes?

Party, WorkItem (as case context), Pipeline/PipelineStage (as stage catalog / CRM view), Task/Activity, ModuleGuard + TenantModule, tenant isolation patterns, AuditRecorder, Document templates/instances (as actions targets), Finance entities (as later hooks), industry template seeding pattern for **initial** stage lists.

### Where does the new product model conflict with current architecture?

| Conflict | Detail |
|----------|--------|
| Naming | `workflows` module ≈ CRM, not Process Engine — risk of overloading meaning |
| Implicit FSM | Free stage moves vs required guarded transitions |
| Hardcoded stage codes | `rejected`/`new_lead` in close/reopen assume sales-shaped pipelines |
| Versioning | Template apply is copy-on-write snapshot; no immutable Process Definition Version |
| Client customization | Today = more pipeline rows / settings JSON; product wants Tenant Process Configuration without Core fork — **aligned in intent**, **missing as typed layer** |
| Approvals | Siloed per domain vs process-level approval steps |
| Docs vs code | PRODUCT_ARCHITECTURE lists HR/payroll/inventory/…; several **not present** as packages |

### What is truly missing and needs a new layer?

Minimal **process overlay** (not a full BPM suite):

1. Process Template (platform catalog)
2. Tenant Process Configuration (enable/bind template + params)
3. Process Definition Version (immutable)
4. Process Instance (runtime) linked to WorkItem
5. Transition rules / actions / triggers (data-driven)
6. Optional SLA policy runner

**Do not** rebuild Party/CRM/modules underneath.

---

## 4. Reconciliation table

| Область | Предусмотрено в документации | Есть в коде | Используется сейчас | Можно переиспользовать | Gap |
|---------|------------------------------|-------------|---------------------|------------------------|-----|
| Party | Universal contacts | Yes | Yes (CRM, leads, templates) | Yes | — |
| WorkItem | CRM case / lead | Yes | Yes | Yes as Process Instance context | Link to process definition/version |
| Pipeline / stages | CRM funnel | Yes | Yes | Yes as stage catalog / board | Transition graph; process semantics |
| WorkItem status | Lifecycle enum | Yes | Partial | Yes | Formal transition matrix |
| Tasks / activities | Work tracking | Yes | Yes (basic) | Yes as process actions/outcomes | Richer role/automation hooks |
| Reminders / SLA | Mentioned loosely | Reminder model only | Little/none | due_at fields | SLA engine, timer worker |
| Audit / events | Audit required | AuditLog + security | Yes | Audit yes; events extend | Domain event/trigger bus |
| Approvals | Per-domain | Docs / Marketing / AI | Yes in silos | Patterns only | Universal process approval step |
| Modules / deps | Core architecture | Registry + Guard | Yes | Yes as capability gates | Process→module action mapping |
| Features / plans | Subscriptions | Yes | Yes | Yes | Process feature codes if needed |
| Industry templates | Seed industry | Yes | Yes | Yes for Process Template **bootstrap** | Not Process Definition Version |
| Tenant settings | Customization CR | JSON settings | Partial | Soft params only | Typed Tenant Process Configuration |
| Documents | Universal module | Yes | Yes | Yes as actions | Process binding |
| Finance | Universal module | Yes | Yes | Later hooks | Process actions not wired |
| HR / Motivation | Listed in architecture | **No package** | No | N/A | Module first, then hooks |
| Integrations | Foundation | Partial | Partial | As action adapters later | Process trigger wiring |
| Process Template/Version/Instance | New product model | **Absent** | No | — | **New thin layer** |

---

## 5. Mapping: new concepts → existing analogues

| Новое понятие | Возможный существующий аналог | Решение |
|---------------|-------------------------------|---------|
| **Process Template** | Industry template `default_pipelines` + module list (partial analogue) | **extend** industry/process catalog — or **new** typed Process Template entity if pipelines alone are too CRM-shaped |
| **Tenant Process Configuration** | Tenant pipelines + `TenantModule.settings_json` + `TenantSettings.industry_config_json` | **extend** — typed config; do not invent parallel tenant fork of Core |
| **Process Definition Version** | None (template apply is unversioned copy) | **new** |
| **Process Instance** | **WorkItem** (best fit) | **reuse / extend** (add FK/metadata to definition version; keep WorkItem as case) |
| **Stage / Transition** | `PipelineStage` + `move_stage` | **reuse** stages; **extend** with transition rules (do not replace board) |
| **Process Action** | Task create, Activity, document/finance service calls (implicit) | **extend** — action descriptors invoking existing modules via ModuleGuard |
| **Event / Trigger** | AuditLog, WebhookEvent (partial) | **extend** thin trigger model; **reuse** audit for trail |
| **SLA / Approval** | Task.due_at / Reminder; domain approvals | **extend** approvals pattern; **new** SLA policy if required beyond due dates |

---

## 6. Recommendation (no implementation plan)

### Preferred approach: **small process layer on top of existing CRM/modules**

**Not** a greenfield Process Engine replacing WorkItem/pipelines.
**Not** “only extend pipelines forever” if product needs versioning, guards, and multi-module actions.

**Rationale:**

1. WorkItem + Party + tenant pipelines already cover the **case + stage UI** for “Лид → диагностика → решение о работе”.
2. `flexity_sales` template **already encodes** those stages (`new_lead`, `contacted`, `diagnosis`, … `rejected` / `converted_to_tenant`).
3. Missing pieces are **versioning, transition policy, process-level actions/approvals, instance↔definition link** — overlay concerns.
4. ModuleGuard/entitlements already express “what system can do”; process layer should orchestrate, not duplicate.

### Minimal first process: «Лид → диагностика → решение о работе»

| Step | Existing fit |
|------|----------------|
| Лид | WorkItem on `flexity_sales` / `new_lead` |
| Диагностика | Stage `diagnosis` (+ tasks/activities/notes) |
| Решение о работе | Move to terminal-ish outcomes (`accepted` / `rejected` / later `converted_to_tenant`) via existing move/close semantics |

**First product increment (concept only — needs Approval Gate):** declare this funnel as a **Process Template** that **binds** to existing pipeline stage codes, add **allowed transitions** for that template, run instances as WorkItems — without rewriting CRM UI.

### Explicitly avoid

- Second case entity competing with WorkItem
- Client-specific Core forks
- Copying Margosya/legacy FS workflows as SoT
- Building full BPMN before one guarded sales path works
- Duplicating module capability checks inside process JSON

---

## 7. Final status block

### Итоговый статус

**RECONCILIATION COMPLETE — NO CODE.**
Architecture supports CRM-centric cases well; **universal Process Template→Instance layer is absent** and should be a **thin overlay**, not a replacement.

### Найденная основа

- Party + WorkItem + Pipeline/Stage (tenant-scoped)
- Tasks / Activities
- Module registry + dependencies + entitlements
- Industry templates as bootstrap
- Audit trail
- Domain approvals (documents / marketing / AI) as patterns
- Concrete sales stage path already in `flexity_sales_basic`

### Критические пробелы

1. No Process Template / Tenant Process Configuration / Definition Version / Instance model
2. No data-driven transition guards (code + stage-code conventions only)
3. No universal process approval / SLA runner
4. No domain event→automation bus
5. Docs list modules (HR/payroll/…) not present in tree — do not design process hooks against fictional packages

### Что нельзя дублировать

- Party, WorkItem, Pipeline board semantics
- ModuleGuard / subscription entitlements
- Tenant isolation patterns
- Document/Finance modules as parallel “mini-CRMs”
- Audit as a second silent write path without policy

### Самый маленький следующий этап

**Documentation / design gate only:** Approval Gate for a **Process Overlay research brief + D0-style mapping** of Process Template → existing `flexity_sales` stages for «Лид → диагностика → решение», including transition policy shape — **still no code**.

### Approval Gate (mandatory before any code)

> **No migrations, models, APIs, or UI for Process Template/Instance until HQ accepts this reconciliation and approves a subsequent research/implementation plan.**

---

## Key files studied

- `docs/ai/PRODUCT_ARCHITECTURE.md`
- `docs/FLEXITY_SALES_TENANT_BOOTSTRAP_PLAN.md`
- `docs/ai/plans/2026-07-10-core-crm-e1-lead-disposition-implementation-plan.md`
- `backend/app/modules/workflows/{models,service,schemas,routes,repository}.py`
- `backend/app/modules/parties/models.py`
- `backend/app/modules/module_registry/{models,service,seed}.py`
- `backend/app/core/modules.py`, `backend/app/core/entitlements.py`
- `backend/app/modules/tenants/models.py`
- `backend/app/modules/industry_templates/seed.py`
- `backend/app/modules/audit/{models,recorder}.py`
- `backend/app/modules/documents/models.py`
- `backend/app/modules/subscriptions/models.py`
- `backend/app/modules/integrations/` (presence)
- `backend/app/modules/finance/` (presence)
- Module package list under `backend/app/modules/` (HR absent)

**Checks:** no code changes beyond this report file; no commit/push; staged untouched by this task intent.
