# Report: M7.5-C Prompt Export + JSON Preview/Import

**Date:** 2026-07-27  
**Worktree:** `.worktrees/m7-5-c-plan-import`  
**Branch:** `feature/marketing-m7-5-c-plan-import`  
**Baseline:** `origin/main` @ `b5ad21cf25b9ddd5c16ad0a3f0a19e7e257756d8`  
**Category:** `universal_module` (Marketing Cabinet)  
**Slice:** M7.5-C only  
**Status:** implemented locally — **not committed** (await HQ)  
**VERDICT:** `M7_5_C_READY_FOR_COMMIT`

## Scope delivered

1. **Prompt export** — server builds copyable prompt from active Guide + active Rubrics; **no AI/network calls**, **no DB writes**.
2. **Shared schema** `m7.5.plan.v1` — prompt JSON Schema + pydantic importer use one module.
3. **Preview** — validate + resolve rubrics + server fingerprint; **no writes**.
4. **Commit** — re-validate server-side; atomic plan+items; fingerprint idempotency with `replayed=true`.
5. **Manual rubric map** — `rubric_code_map: {code → active rubric_id}` same tenant; cross-tenant → 404.
6. **No** UI / topics / packs / auto-rubric / M7.5-D / migration.

## Migration

| Item | Value |
|------|-------|
| New migration for C | **none** (STOP not triggered) |
| Fingerprint column | already in `0028_mkt_content_plans` |
| Alembic head | still `0028` |

## Endpoints (`/api/v1/marketing`)

| Method | Path | RBAC | Writes |
|--------|------|------|--------|
| POST | `/content-plans/prompt-export` | `require_module("marketing")` | no |
| POST | `/content-plans/import/preview` | `require_module("marketing")` | no |
| POST | `/content-plans/import/commit` | `require_marketing_settings_admin` | yes (or replay) |

**HTTP commit:** first import → **201**; fingerprint replay → **200** + `replayed=true` (HQ override of older plan text that said reject).

**Source value:** DB/API enum remains **`json_import`** (locked in M7.5-B / 0028). HQ wording “source=import” maps to this existing value — **not** renamed (would need migration → STOP).

## Shared schema (`content_plan_schema.py`)

- `SCHEMA_VERSION = "m7.5.plan.v1"`
- Root: `schema_version`, `period_start`, `period_end`, `title`, `items[]`
- Item: `line_key`, `date` (→ DB `planned_date`), `rubric_code`, `working_title`, `channels`, editorial fields
- JSON `line_key` → DB `external_line_key` (B contract)
- `plan_json_schema()` embedded in prompt export
- `parse_plan_document()` / `PlanDocument` used by preview + commit

## Fingerprint algorithm

1. Parse/validate to `PlanDocument`.
2. Build canonical dict: items sorted by `line_key`; channels sorted; dates ISO; null editorial fields preserved.
3. Wrap `{tenant_id, plan}` → `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
4. `sha256(utf-8).hexdigest()`.
5. Client **cannot** supply fingerprint; only server computes/stores.
6. Same semantic payload + same tenant → same fingerprint → replay returns existing plan (no duplicate).

## Limits (documented + enforced)

| Limit | Value |
|-------|-------|
| `MAX_JSON_BYTES` | 256_000 |
| `MAX_ITEMS` | 200 |
| `MAX_TITLE_LEN` | 512 |
| `MAX_LINE_KEY_LEN` | 128 |
| `MAX_WORKING_TITLE_LEN` | 512 |
| `MAX_TEXT_FIELD_LEN` | 4_000 |
| `MAX_CHANNELS_PER_ITEM` | 8 |
| `MAX_MAPPING_ENTRIES` | 100 |
| `MAX_ADDITIONAL_INSTRUCTIONS_LEN` | 4_000 |
| `MAX_TARGET_ITEM_COUNT` | 366 |
| `MAX_RUBRIC_FILTER` | 100 |
| Allowed channels | `telegram`, `instagram`, `threads`, `insights` |

## Audit

Uses existing `AuditRecorder.audit_log`:
- CREATE on first import
- EXECUTE on replay  
No new global audit subsystem.

## Files changed

### New
- `backend/app/modules/marketing/content_plan_schema.py`
- `backend/app/modules/marketing/service/content_plan_prompt.py`
- `backend/app/modules/marketing/service/content_plan_import.py`
- `backend/tests/test_marketing_content_plan_import_api.py`
- `docs/ai/reports/2026-07-27-marketing-m7-5-c-plan-import-implementation-report.md`

### Modified
- `backend/app/modules/marketing/repository.py` — `get_content_plan_by_fingerprint`
- `backend/app/modules/marketing/routes.py` — C endpoints before `{plan_id}`
- `backend/app/modules/marketing/schemas.py` — prompt/import request+response models

## Tests

| Suite | Result |
|-------|--------|
| `test_marketing_content_plan_import_api.py` | pass (14) |
| `test_marketing_content_plans_api.py` (M7.5-B) | pass |
| `test_marketing_guides_rubrics_api.py` (M7.5-A) | pass |
| **Total targeted** | **31 passed** |

Covered: prompt from Guide+Rubrics; fail-closed no guide/rubrics; tenant isolation; preview no writes; invalid schema/malformed/dup line_key/out-of-period; unknown + inactive rubric; explicit map; cross-tenant map 404; fingerprint canonicalize + tenant scope; commit create; replay; validation zero writes; item failure rollback; source/status draft; topics not created; A/B+Topics smoke.

## Security / tenant-isolation verdict

| Check | Result |
|-------|--------|
| Tenant scoped reads/writes | PASS |
| Cross-tenant rubric map | FAIL CLOSED (404) |
| Cross-tenant plan visibility | PASS (404 / empty list) |
| No AI / outbound network in C paths | PASS |
| No secrets/tokens in prompt payload | PASS (contract text forbids; response has no tokens) |
| Preview read-only | PASS |
| Commit re-validates (does not trust preview) | PASS |
| Fingerprint server-only | PASS |
| Unknown rubric auto-create | NOT DONE (correct) |
| Topics/packs side effects | NONE |
| Migration / auth / billing / deploy | untouched |

**Security verdict: PASS**

## Compatibility evidence

- Base = approved `b5ad21c` (`origin/main` post M7.5-B merge)
- Dirty root / M7.5-A / M7.5-B worktrees **not modified**
- No new Alembic revision; uses `import_fingerprint` from 0028
- M7.5-A/B API regression suites green
- Topics create smoke still works with `rubric` code

## Intentionally not touched

- UI / platform-console
- AI providers / model calls
- ContentTopic / packs / publish adapters
- M7.5-D / M8-D3/D4/E
- Auth, tenant core, subscriptions, Nginx, deploy
- Sibling worktrees and dirty root

## Risks

1. Shared test `db_session` requires explicit `rollback()` after mid-request exceptions (documented in rollback test); production `Session.close()` rolls back uncommitted work.
2. HQ doc historically said reject replay; **implemented HQ C approval**: return existing plan + `replayed=true`.
3. `source` stays `json_import` (not literal `"import"`).

## Next safe step

HQ review → separate approval to **commit** branch `feature/marketing-m7-5-c-plan-import` only.  
Do **not** start M7.5-D without new HQ approval.
