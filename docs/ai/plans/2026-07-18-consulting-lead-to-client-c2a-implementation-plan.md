# Implementation Plan: Consulting Lead-to-Client Automation — C2a

**Date:** 2026-07-18  
**Type:** implementation plan  
**Status:** HQ APPROVED (corrected) — implement in worktree only  
**Project:** Flexity  
**Category:** universal_module (wiring) + process_overlay catalog policy  
**Truth baseline:** `origin/main` @ `50d6780`  
**Branch / worktree:** `feature/consulting-lead-c2a-process-run`  
**Tenant:** `flexity-sales` (internal; do **not** create a new consulting tenant in C2a)  
**Related research:** `docs/ai/research/2026-07-18-consulting-lead-to-client-automation-research-brief.md`  
**Related design (graph source):** `docs/ai/plans/2026-07-18-consulting-basic-industry-template-design.md` §7.2  

## Goal

Когда `/demo` (или curl) шлёт `POST /api/v1/public/leads` на tenant `flexity-sales`:

1. Party match/reuse (уже live) — **preserve**  
2. Один WorkItem на pipeline `flexity_sales` / stage `new_lead` (уже live) — **preserve**  
3. Free-form inbound metadata в `WorkItem.custom_fields_json` (utm_*, form_name, party_match, …) — **preserve**  
4. Если overlay config **ACTIVE** для pipeline → **также** Active `ProcessRun` (те же семантики, что E1b2 via `WorkflowService._maybe_auto_start_process_run`)  
5. Если overlay **нет / INACTIVE** → прежнее поведение: WorkItem only, **no** ProcessRun (no-op)

## Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | universal_module (wiring) |
| Risk | medium (public inbound + fail-closed overlay + policy graph change) |
| Intended scope | public_leads wiring + full sales intake blueprint + local bootstrap helper + tests |
| Forbidden | push; deploy; production activation; dirty root edits; migrations; force push; `consulting_basic` seed; staging import code |

## HQ decisions (authoritative)

1. **Tenant = `flexity-sales` only** for C2a (internal sales). No new consulting tenant.  
2. **Wire public inbound through `WorkflowService.create_work_item`** (NOT `WorkflowRepository.create_work_item`) so E1b2 auto-start applies.  
3. **Full transition graph** for `flexity_sales_intake` default_policy_blueprint (replace shortened E1 graph).  
4. **Terminal stages:** `accepted`, `rejected`.  
5. **New immutable definition version** on publish — never mutate a published version; bootstrap always publishes a **new** version from current blueprint.  
6. **No production activation in C2a** — bootstrap helper is LOCAL/ops only; do not flip prod overlay ACTIVE as part of this PR.  
7. **Do not enable production inbound** — leave default `public_leads_enabled=False`; no env/deploy changes.  
8. **No migrations.** No `consulting_basic` seed. No staging import code.  
9. **Custom fields pattern (critical):** free-form public-lead keys must **not** go through `CustomFieldService.validate_and_prepare` (unknown keys → `ConflictError`). Create via `WorkflowService` with `custom_fields={}` + participants; then merge `_custom_fields(...)` into ORM `work_item.custom_fields_json` and `flush`.

## Non-goals

- Assignment / SLA / tasks automation (C2b)  
- Documents / finance templates (C2c)  
- Social inbound connectors (C2d)  
- Auto-create client tenant (E8)  
- New `consulting_basic` / second tenant  
- Production live overlay activation / deploy  
- Changing default `public_leads_enabled`

## Current state (main @ 50d6780)

- Public inbound + match + rate limit: **ready**  
- E1a/E1b/E1b2/E1c: **on main**  
- **Gap A:** `PublicLeadService._create_work_item` → `WorkflowRepository.create_work_item` → bypasses `_maybe_auto_start_process_run`  
- **Gap B:** catalog `flexity_sales_intake` blueprint is **short** (`diagnosis→accepted|rejected`); missing proposal/negotiation path used by real `flexity_sales` pipeline  
- **Gap C:** tenant overlay for `flexity-sales` may be missing/INACTIVE (ops; bootstrap helper only)  

## Full policy graph (HQ)

`stage_codes`:

`new_lead`, `contacted`, `diagnosis`, `proposal_prepared`, `proposal_sent`, `negotiation`, `accepted`, `rejected`

`transitions`:

| from | to |
|------|-----|
| `new_lead` | `contacted` |
| `new_lead` | `rejected` |
| `contacted` | `diagnosis` |
| `contacted` | `rejected` |
| `diagnosis` | `proposal_prepared` |
| `diagnosis` | `rejected` |
| `proposal_prepared` | `proposal_sent` |
| `proposal_prepared` | `rejected` |
| `proposal_sent` | `negotiation` |
| `proposal_sent` | `accepted` |
| `proposal_sent` | `rejected` |
| `negotiation` | `accepted` |
| `negotiation` | `rejected` |

`terminal_stage_codes`: `accepted`, `rejected`  
`schema_version`: 1  
`process_template_code`: `flexity_sales_intake`  
`pipeline_code`: `flexity_sales`  
`module_requirements`: `["crm"]`  
`conditions`: `required_roles: ["sales"]`, `requires_approval: false` (same style as existing seed)

**Removed edge:** `diagnosis → accepted` (illegal under full graph).

## Scope

### Files to modify

- `docs/ai/plans/2026-07-18-consulting-lead-to-client-c2a-implementation-plan.md` — this plan (plan-only commit first)  
- `backend/app/modules/public_leads/service.py` — WorkflowService wiring + custom_fields merge  
- `backend/app/modules/process_overlay/seed.py` — full graph blueprint  
- `backend/app/modules/process_overlay/service/bootstrap.py` (new) — LOCAL/ops bootstrap helper  
- `backend/app/modules/process_overlay/service/__init__.py` — export bootstrap  
- `backend/tests/test_public_leads.py` — ACTIVE / missing overlay + custom_fields + party reuse  
- `backend/tests/test_process_overlay_e1a_*.py`, `e1b_*.py`, `e1b2_*.py`, `e1c_*.py` — pipeline stages + legal paths  

### Files not to touch

- Dirty root WIP outside this worktree  
- Alembic migrations  
- `industry_templates/seed.py` (`consulting_basic`)  
- Landing / M8 publish / staging import  
- Production `.env` / Nginx / deploy scripts  
- Default `public_leads_enabled`  

## Steps

### Commit 1 — plan only

Overwrite this plan with HQ decisions above; commit message: `docs(plan): C2a corrected plan`.

### Commit 2 — code

1. **`public_leads/service.py`**  
   - Resolve `User` (already from `_assert_runtime_targets`).  
   - Call `WorkflowService(self.db, tenant_id).create_work_item(user, WorkItemCreate(...))` with `custom_fields={}` and participant CLIENT.  
   - Load ORM WorkItem; merge `_custom_fields(...)` into `custom_fields_json`; `flush`.  
   - Rely on existing `_maybe_auto_start_process_run` for ACTIVE overlay (no-op if missing/INACTIVE).  
   - Preserve party match/dedup, single WorkItem, participants, audit, commit, Telegram notify.

2. **`process_overlay/seed.py`**  
   - Replace `default_policy_blueprint_json` with full graph (above). Update description text.

3. **Bootstrap helper** (`ProcessOverlayBootstrapService.bootstrap_flexity_sales_intake`)  
   - `seed_templates()`  
   - Ensure `TenantProcessConfiguration` for pipeline `flexity_sales` + template `flexity_sales_intake` (create if missing)  
   - Publish **new** immutable definition version from current blueprint  
   - `set_active_definition_version` + `activate_configuration`  
   - Document: LOCAL/ops only; **production activation NOT in C2a**

4. **Tests**  
   - `test_public_leads.py`: ACTIVE → ProcessRun; without → no run; one WorkItem; `custom_fields_json` preserved; party reuse  
   - Overlay test helpers: add `proposal_sent` + `negotiation` wherever flexity_sales stages listed  
   - Replace `diagnosis→accepted` paths with legal path via proposal_*/negotiation  
   - E1c: deny illegal jump; allow `new_lead→contacted`; allow full path to `accepted`  
   - Fix `close` tests: under full graph `new_lead→rejected` **is** legal  

5. **Checks** (worktree backend): public_leads + e1a/e1b/e1b2/e1c + workflows + optional ephemeral PG race; `git diff --check`

## Tests/checks

```text
pytest backend/tests/test_public_leads.py
pytest backend/tests/test_process_overlay_e1a_models.py \
       backend/tests/test_process_overlay_e1a_publication.py \
       backend/tests/test_process_overlay_e1b_models.py \
       backend/tests/test_process_overlay_e1b_runs.py \
       backend/tests/test_process_overlay_e1b2_auto_start.py \
       backend/tests/test_process_overlay_e1c_transition_enforcement.py
pytest backend/tests/test_workflows.py
# optional: e1c ephemeral PG race (local PG 17 initdb ~55434)
git diff --check
```

## Risks

- Fail-closed auto-start rolls back entire lead create if `start_run` fails (same as CRM E1b2)  
- Catalog blueprint change affects any test that publishes `_policy_from_blueprint()` — pipeline fixtures must include all stage_codes  
- Existing published prod versions (if any) are **not** mutated; ops must publish new version intentionally — C2a does not activate prod  
- Confusion with consulting **import** C2a — this plan is Lead-to-Client C2a only  

## Rollback

- Revert code commit (public_leads + seed + bootstrap + tests)  
- Ops: `deactivate_configuration` on overlay (WorkItems continue; no new ProcessRuns)  
- `PUBLIC_LEADS_ENABLED=false` if public surface regresses  

## C2 roadmap (planning only — not this plan)

| Stage | Scope |
|-------|--------|
| **C2a** (this) | Landing → WorkItem + ProcessRun + full sales intake policy |
| **C2b** | assignment / tasks / SLA / reminders |
| **C2c** | documents / finance after `accepted` |
| **C2d** | Instagram / TikTok / WhatsApp inbound connectors |

## Approval

**Status: HQ APPROVED (corrected plan)**

Approved:

1. Tenant = `flexity-sales` internal only  
2. `WorkflowService` wiring + custom_fields merge pattern  
3. Full graph in catalog seed; new immutable definition versions only  
4. Bootstrap = local/ops helper; **no** production activation in C2a  
5. No migrations / no `consulting_basic` / no staging import / no push / no deploy  

## Commits (required)

1. `docs(plan): C2a corrected plan`  
2. `feat(consulting): C2a public inbound ProcessRun wiring + full sales intake policy`  

## Next after C2a GREEN

Local smoke on worktree; separate HQ gate for any ops bootstrap on a real tenant; then C2b.
