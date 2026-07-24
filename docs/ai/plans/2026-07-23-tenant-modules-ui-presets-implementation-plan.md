# Audit + Implementation Plan: Tenant Modules UI + Presets Readiness

**Date:** 2026-07-23
**Type:** research_only / documentation_only → **Slice 1 implementation approved (HQ Decision A)**
**Status:** Slice 1 implemented on `feature/tenant-modules-ui-slice1` — **waiting for commit approval**
**Risk:** low
**Code / migrations / seed / deploy / server:** Slice 1 code in dedicated worktree only; **no migrations; no commit/push yet**

**Related (read-only reuse):**
- `docs/ai/plans/2026-07-18-consulting-basic-industry-template-design.md` (design draft; seed not approved)
- `docs/ai/PRODUCT_ARCHITECTURE.md` (layers: core → modules → template/package → tenant customization)
- First-client / qonsulting migration track (import later into tenant; not this slice)

---

## Task classification

| Field | Value |
|-------|-------|
| Project | Flexity |
| Category | `platform_core` (+ documentation for `industry_template` presets) |
| Risk | low (this document); medium when implementing enablement UX |
| Intended scope | one plan file only |
| Forbidden | backend/frontend code, migrations, seed/template changes, tenant/module activation, qonsulting data, Hoster/AWS/DNS/deploy, Marketing M8, commit/push |

---

## 1. Verdict

**Reusable foundation EXISTS. Provider Tenant Modules Console is partially live. Presets / three-state model / monetization gates are NOT ready.**

| Layer | Verdict |
|-------|---------|
| Module catalog (`module_definitions`) | **READY** (shared catalog for Asem + client tenants) |
| Tenant enable/disable API | **READY** (provider-owner scoped) |
| Platform Console Modules tab | **PARTIAL** (list + enable/disable buttons only) |
| Plan entitlement vs enable | **PARTIAL** (plans exist; enable API does **not** enforce entitlement) |
| Dependency enable check | **READY** (`required` only) |
| Dependency disable protection | **MISSING** |
| Configuration readiness | **MISSING** as first-class state |
| `consulting_basic` as editable preset | **DESIGN ONLY** — not in seed; must not be hard-coded tenant seed |
| `trailers_basic` same mechanism | **FUTURE** (same preset pattern; out of slice 1) |
| Billing / add-ons UI | **LATER** |

**Safe next code slice (after separate HQ approval):** provider-controlled Tenant Modules UI hardening on existing APIs — **no** Alembic, **no** new industry seed, **no** qonsulting activation.

---

## 2. Existing reusable foundation (audit)

### 2.1 Backend — module registry

| Asset | Path | What it does |
|-------|------|----------------|
| Models | `backend/app/modules/module_registry/models.py` | `ModuleDefinition` (catalog); `TenantModule` (per-tenant status/mode/`settings_json`) |
| Seed catalog | `backend/app/modules/module_registry/seed.py` | Shared codes: `parties`, `crm`, `catalog`, `documents`, `finance`, `accounting`, `integrations`, `ai`, `booking`, `marketing` |
| Service | `…/module_registry/service.py` | `list_registry`, `provision_tenant_modules` (idempotent row create, all **DISABLED**), `enable_module`, `disable_module`, `set_module_mode`, `enable_modules_ordered`, `apply_plan_modules` |
| Routes | `…/module_registry/routes.py` | `GET /modules/registry`; `GET/PATCH /tenants/{id}/modules…`; `POST …/enable`; `POST …/disable`; `PATCH …/mode` |
| Guard | `backend/app/core/modules.py` | `ModuleGuard.is_active` / `assert_enabled` / `assert_dependencies`; `require_module(...)` |
| Entitlements | `backend/app/core/entitlements.py` | Plan feature + module-enabled check via `require_feature` |
| Tests | `backend/tests/test_modules.py` | registry list, provision on create, enable dep check, external mode, require_module |

**Catalog codes present today:** no separate `consulting` or `reports` module codes.

### 2.2 Tenant create / template apply / plans

| Flow | Behavior |
|------|----------|
| `TenantService.create` | Creates tenant → default branch → optional owner → **`provision_tenant_modules`** (all disabled) → optional `assign_plan` → optional `apply_to_tenant` |
| `SubscriptionService.assign_plan` | Enables plan `default_modules_json` as **TRIAL** via `apply_plan_modules` |
| `IndustryTemplateService.apply_to_tenant` | Enables template `default_modules` ordered; sets labels/pipelines/docs/catalog/AI config; **does not** invent new apps |
| Plans seed | `starter` / `business` / `enterprise` with `default_modules_json` + features (`subscriptions/seed.py`) |
| Templates seed | `kindergarten_basic`, `flexity_sales_basic` only — **`consulting_basic` absent** |

### 2.3 Platform Console UI (already)

| Asset | Behavior |
|-------|----------|
| `platform-console/src/pages/TenantDetailPage.tsx` | Tab **«Модули»**: table of tenant modules; **Включить** / **Отключить** |
| `platform-console/src/api/modules.ts` | `listTenantModules`, `enableModule`, `disableModule` |
| `platform-console/src/types/module.ts` | status: `enabled \| disabled \| trial \| suspended`; mode enums |

**Not in Console today:** registry catalog join, dependency preview, entitlement badges, readiness, mode editor, preset apply, plan upgrade CTA, client self-service.

### 2.4 RBAC / audit / isolation

| Control | Current |
|---------|---------|
| Manage modules API | `require_provider_owner` + `_ensure_provider_access` (same `provider_company_id`) |
| Runtime module use | `require_module` / `require_feature` under tenant context |
| Tenant isolation | `tenant_modules.tenant_id` FK; guards scoped by tenant |
| Audit | Generic mutation middleware (`audit/middleware.py`) may log HTTP mutations; **no** dedicated module-enable audit payload in `ModuleRegistryService` |

### 2.5 What is already true vs business needs for `qonsulting`

| Business need | Existing code mapping |
|---------------|------------------------|
| CRM | module `crm` (+ required `parties`) |
| Consulting | **not a registry module** — intended as **preset/template package** (`consulting_basic`) over universal modules |
| Documents/Templates | module `documents` |
| Finance/Debtors | module `finance` (receivables live under finance; no separate `debtors` code) |
| Reports | **no** `reports` module — workspace/report pages compose from enabled modules (CRM/finance); treat as readiness/UI surface later, not new Alembic |
| Marketing Cabinet | module `marketing` (optional / add-on) |

**Import of Flask Consulting data** into `qonsulting` remains a **separate** migration track; this plan only ensures module enablement UX/presets can prepare the tenant.

---

## 3. Exact gaps

| # | Gap | Blocks |
|---|-----|--------|
| G1 | Console Modules tab = raw enable/disable only (no entitlement / readiness / deps UX) | Provider clarity for `qonsulting` |
| G2 | `POST …/enable` does **not** check plan entitlement / paid add-on | Monetization |
| G3 | `disable` does **not** block when dependents are active | Safe disable |
| G4 | No first-class **configuration readiness** (pipelines/templates/settings) | “Enabled but empty” confusion |
| G5 | Console does not call `GET /modules/registry` (names/deps unused in UI) | UX |
| G6 | No dedicated audit event fields for module toggle (beyond generic middleware) | Ops accountability |
| G7 | `consulting_basic` missing from seed; design exists but must stay **editable preset**, not hard tenant seed | First client package |
| G8 | Plans omit `marketing` in defaults; no add-on purchase flow | Paid Marketing |
| G9 | No client self-service modules API (tenant_owner cannot toggle) | Later slice (intentional for slice 1) |
| G10 | No preset preview API (“required / recommended / optional”) | Presets slice |
| G11 | Priority sort in `enable_modules_ordered` hardcodes list; `marketing` appended ad-hoc | Ordering hygiene (small) |

---

## 4. Proposed state / permission / dependency model

### 4.1 Three independent states (design lock)

For each `(tenant, module_code)` the UI/API must expose **three orthogonal axes**:

| Axis | Meaning | Source of truth (proposed) |
|------|---------|----------------------------|
| **A. Entitlement / availability** | May this tenant turn the module on? (`included` / `add_on_available` / `restricted` / `unavailable`) | Subscription plan features + plan `default_modules` / future add-on entitlements — **not** overwritten by enable click |
| **B. Enabled / disabled** | Is the module active for runtime guards? (`enabled` / `trial` / `disabled` / `suspended`) | Existing `tenant_modules.status` (+ mode) |
| **C. Configuration readiness** | Is the module usable for Day-1 ops? (`not_applicable` / `not_ready` / `ready` / `needs_attention`) | Derived: pipeline exists, doc templates imported, finance refs, marketing connections, etc. — **computed**, stored optionally later in `settings_json.readiness` |

**Rules:**
- Enabled ≠ entitled: entitled+disabled is valid (provider can leave off).
- Enabled ≠ ready: enabled without pipeline/templates shows readiness warning — **does not** auto-run migrations.
- UI click **never** runs Alembic / never creates industry DB schemas.
- Enable provisioning = idempotent row upsert + optional config ensure hooks that are **safe to re-run**.
- Disable = status/mode flip only — **never** deletes parties/work items/documents/payments/files.
- Enable requires `required` dependencies active (already).
- Disable must refuse if other **enabled** modules list this code in `dependencies_json.required` (new guard).
- Provider owner/admin (current: provider owner staff) manages any tenant in company.
- Client self-service (later): only modules with entitlement `included` or purchased add-on; cannot enable `restricted`.
- Paid/restricted modules: UI shows **Upgrade / Request approval**, not silent enable.

### 4.2 Permission matrix (target)

| Actor | List modules | Enable entitled | Enable restricted/paid | Disable | Edit settings | Apply preset |
|-------|--------------|-----------------|--------------------------|---------|---------------|--------------|
| Provider owner | yes | yes | yes (ops override + audit) | yes (with dep guard) | yes | yes |
| Provider admin (if introduced) | yes | yes | request/approve flow | yes | limited | yes |
| Tenant owner (self-service later) | own tenant | entitled only | no → upgrade CTA | entitled optional only | own settings | no (or request) |
| Tenant member | read if allowed | no | no | no | no | no |

**Slice 1 keeps provider-only writes** (matches current API).

### 4.3 Dependency model

Reuse `ModuleDefinition.dependencies_json`:

```json
{ "required": ["parties"], "recommended": ["catalog"] }
```

| Action | Behavior |
|--------|----------|
| Enable | Fail if any `required` inactive (existing `ModuleDependencyError`) |
| Enable UX | Show `recommended` as soft checklist |
| Disable | Fail if any other active module requires this one (**new**) |
| Preset apply | Enable `required` then `recommended` (ordered); optional only if selected |

### 4.4 Preset vs industry template vs package

| Concept | Role |
|---------|------|
| **Module** | Universal capability in shared catalog (`crm`, `documents`, …) |
| **Preset / industry template** (`consulting_basic`, later `trailers_basic`) | Editable configuration package: default modules tiers + pipelines + labels + doc/finance defaults — **not** a separate Flask app |
| **Tenant customization** | Client logo/legal/labels overrides — later; not mixed into preset seed without approval |

`consulting_basic` must remain **editable** (update template record / re-apply with idempotent enables). It must **not** become a one-shot hard-coded tenant create path that cannot be reviewed in Console.

---

## 5. `consulting_basic` preset definition (design for later seed — **do not seed in slice 1**)

**Preset code:** `consulting_basic`
**Target first client tenant slug (ops):** `qonsulting` (activation out of this plan)
**Mechanism:** same as `kindergarten_basic` / `flexity_sales_basic` — `industry_templates` row + `default_modules` + config JSON — applied via existing `apply_to_tenant`.

| Tier | Business label | Module codes (existing) | Notes |
|------|----------------|-------------------------|-------|
| **Required** | Parties / CRM; Consulting package | `parties`, `crm` | “Consulting” = preset pipelines/labels/process overlay on CRM — **not** a new app |
| **Recommended** | Documents/Templates; Finance/Debtors; Reports | `documents`, `finance` (+ `catalog` recommended for services) | Reports = readiness of CRM/finance views; no new `reports` registry code in v1 |
| **Optional / configurable** | Marketing Cabinet | `marketing` | Entitlement/add-on; off by default unless plan includes it |

**Explicit non-goals for preset v1:** inventory, trailers production, clinic booking, auto full-history import, Marketing M8 publish bridge work.

**Future sibling:** `trailers_basic` — same three-tier preset pattern; industry-specific modules/packages only when approved — **separate slice**.

---

## 6. Minimal first implementation slice (HQ approval required)

### Slice 1 — Provider-controlled Tenant Modules UI (first)

**Goal:** Make Platform Console Tenant → Modules usable for ops (Asem) without inventing presets/billing yet.

**In scope:**
1. Console: join tenant modules with `GET /modules/registry` (display name, description, required deps).
2. Console: show **entitlement** as read-only badge if cheaply available from existing plan endpoints; if not, show placeholder `unknown` + status only (no fake billing).
3. Console: surface dependency errors from API (409) in Russian alerts.
4. Backend (minimal, only if needed for UI):
   - optional response enrichment OR thin `GET /tenants/{id}/modules` include definition fields;
   - **disable dependents guard**;
   - optional entitlement check on enable (provider override flag allowed with audit note).
5. Confirm disable never deletes data (test).
6. Confirm enable is idempotent (re-enable already enabled = 200/no-op).

**Out of scope for Slice 1:**
- `consulting_basic` seed
- preset apply UI
- client self-service
- billing/add-on purchase
- `trailers_basic`
- qonsulting create/enable
- Alembic
- Marketing M8

### Later slices (separate approvals)

| Slice | Content |
|-------|---------|
| **2 — Presets + dependency preview** | Seed/edit `consulting_basic` as editable template; Console “Apply preset” preview (required/recommended/optional); readiness checklist |
| **3 — Client self-service** | Tenant-owner modules page within entitlement; upgrade CTA for restricted |
| **4 — Billing / add-ons** | Paid module SKUs (e.g. Marketing); entitlement grants before enable |
| **5 — `trailers_basic`** | Same preset mechanism for Trailers industry |

---

## 7. Exact proposed file manifest (Slice 1)

### Likely modify (after approval)

| File | Change |
|------|--------|
| `platform-console/src/api/modules.ts` | Add `listModuleRegistry()`; optionally richer list type |
| `platform-console/src/types/module.ts` | Registry + display/entitlement/readiness view types |
| `platform-console/src/pages/TenantDetailPage.tsx` | Modules tab UX: names, deps, badges, better errors |
| `backend/app/modules/module_registry/service.py` | Disable dependents guard; idempotent enable; optional entitlement assert |
| `backend/app/modules/module_registry/schemas.py` | Optional enriched list response |
| `backend/app/modules/module_registry/routes.py` | Only if response shape changes |
| `backend/tests/test_modules.py` | Dependents-on-disable; idempotent enable; entitlement cases |

### Do not touch (Slice 1)

- `backend/alembic/**`
- `backend/app/modules/industry_templates/seed.py` (no `consulting_basic` yet)
- Marketing M8 / publish bridge worktrees
- Import / consulting SQLite migration code
- Deploy / nginx / DNS / Hoster / AWS
- Tenant data for `qonsulting`

### Slice 2+ (preview only — not authorized now)

- `industry_templates/seed.py` — add editable `consulting_basic`
- Console preset preview components
- Subscriptions add-on models (may need migration — **separate** plan)

---

## 8. Migration impact

| Slice | Alembic / DB schema |
|-------|---------------------|
| **1** | **None expected** — uses existing `module_definitions`, `tenant_modules`, plans/features |
| **2** | Prefer seed/upsert of template row only (no schema) if models already support fields |
| **4** | Possible new add-on entitlement tables — **requires separate migration plan + approval** |

**UI enable click must never invoke Alembic.**

---

## 9. Tests / checks (Slice 1)

| Check | Type |
|-------|------|
| Registry list returns known codes | existing + keep green |
| Tenant create provisions disabled rows | existing |
| Enable CRM without parties → 409 | existing |
| Disable `parties` while `crm` enabled → 409 (new) | new |
| Re-enable already enabled → success / no duplicate row | new |
| Disable leaves parties/work_items counts unchanged | new / integration |
| Console typecheck / smoke Modules tab | manual + existing FE tests if any |
| Provider isolation: other provider cannot toggle | existing permission path |
| No migration files in diff | QA gate |

---

## 10. Blockers / decisions for HQ

1. **Confirm three-state model** (entitlement / enabled / readiness) as product lock.
2. **Confirm “Consulting” is preset-on-CRM**, not a new `module_definitions` code in v1.
3. **Confirm “Reports”** stays composed UI (no `reports` module) for v1.
4. **Provider override:** may provider enable a module not on the plan? (recommended: yes + audit; client self-service: no).
5. **Slice 1 scope:** UI-only vs UI + disable-dependents backend guard (recommended: **both**, still no migration).
6. **When to seed `consulting_basic`:** only after Slice 1 green + separate approval (Slice 2).
7. **`qonsulting` activation:** separate ops gate after preset exists — not part of Modules UI slice.
8. **Marketing paid vs included** for consulting clients.

---

## 11. Files changed (this gate)

| File | Action |
|------|--------|
| `docs/ai/plans/2026-07-23-tenant-modules-ui-presets-implementation-plan.md` | **created** (this document) |

No other files.

---

## 12. Confirmation — no code / server changes

| Action | Status |
|--------|--------|
| Backend / frontend code | **not modified** |
| Migrations / seed / template apply | **not run** |
| Tenant / module activation | **not performed** |
| qonsulting / Hoster / AWS / DNS / deploy | **not touched** |
| Marketing M8 | **not touched** |
| commit / push | **not performed** |

---

## Approval

**Status:** HQ Decision **A** approved Slice 1 (2026-07-23).

**Slice 1 implementation:** done in worktree `.worktrees/tenant-modules-ui-slice1` on branch `feature/tenant-modules-ui-slice1` (base `308b804`).
**Report:** `docs/ai/reports/2026-07-23-tenant-modules-ui-slice1-implementation-report.md`
**Commit:** not created — stop before commit per HQ.

Further slices (presets / self-service / billing / trailers_basic) still require separate HQ approval.
