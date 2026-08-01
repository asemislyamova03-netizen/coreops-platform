# Implementation Report: Generic Client Self-Service Onboarding D1–D3

**Date:** 2026-08-01  
**HQ approval:** `APPROVE_GENERIC_SELF_SERVICE_ONBOARDING_IMPLEMENTATION_D1_D3`  
**Canonical plan:** `docs/ai/plans/2026-08-01-generic-client-self-service-onboarding-d1-d3-plan.md`  
**Final verdict:** `READY_FOR_GENERIC_ONBOARDING_CANDIDATE_VALIDATION`

---

## 1. Branch / worktree / base SHA

| Item | Value |
|---|---|
| Worktree | `.worktrees/generic-client-onboarding-d1-d3` |
| Branch | `feature/generic-client-onboarding-d1-d3` |
| Base SHA | `ea045164c37531cda106cfd8442cd23499a8ed99` |
| HEAD (uncommitted impl) | still based on `ea045164` (no commit yet) |
| Untouched | `main` (`b4f2683…`), `.worktrees/m7-5-prod-candidate` @ `ea045164` / `release/m7-5-prod-candidate` |

No merge, push, PR, deploy, nginx, production/stage writes, or test-identity cleanup.

---

## 2. Changed files

### Backend (modified)

- `backend/app/api/v1/router.py` — include client-onboarding router
- `backend/app/core/config.py` — feature flag + provider slug settings
- `backend/app/core/enums.py` — `SecurityEventType.CLIENT_ONB_DONE` (`client_onb_done`, ≤15 for `security_events.event_type`)
- `backend/app/core/exceptions.py` — `ServiceUnavailableError`
- `backend/app/core/exception_handlers.py` — map 503
- `backend/app/modules/models.py` — register idempotency model

### Backend (added)

- `backend/app/modules/client_onboarding/__init__.py`
- `backend/app/modules/client_onboarding/constants.py` — whitelist `parties`, `marketing`
- `backend/app/modules/client_onboarding/models.py` — idempotency table ORM
- `backend/app/modules/client_onboarding/schemas.py` — request/response (`extra=forbid`)
- `backend/app/modules/client_onboarding/service.py` — atomic signup
- `backend/app/modules/client_onboarding/routes.py` — `POST /client-onboarding/signup`
- `backend/alembic/versions/20260801_0030_client_onboarding_idempotency.py`
- `backend/tests/test_client_onboarding_d1_d3.py`

### Frontend (modified)

- `platform-console/src/routes.tsx` — `/register`
- `platform-console/src/pages/LoginPage.tsx` — link to register

### Frontend (added)

- `platform-console/src/api/clientOnboarding.ts`
- `platform-console/src/pages/ClientSignupPage.tsx`
- `platform-console/src/pages/clientSignupHelpers.ts`
- `platform-console/src/pages/clientSignup.contract.test.ts`

### Docs (this report)

- `docs/ai/reports/2026-08-01-generic-client-self-service-onboarding-d1-d3-implementation-report.md`

---

## 3. Migrations

| Field | Value |
|---|---|
| Revision | `0030_client_onboarding_idem` (≤32; was briefly `…_idempotency` at 34 chars, fixed in follow-up commit) |
| Down revision | `0029_mkt_timestamp_defaults` |
| Alembic head (script) | `0030_client_onboarding_idem` |
| Table | `client_onboarding_idempotency_keys` |

**Validation notes:**

- Chain verified via `ScriptDirectory` (`DOWN_OF_0030=['0029_mkt_timestamp_defaults']`).
- ORM table covered by pytest `Base.metadata.create_all` (SQLite in-memory).
- Live `alembic upgrade/downgrade` against a disposable DB was **not** completed in this session: `alembic/env.py` always rebinds URL from `get_settings().database_url`, so a roundtrip attempt aborted early against the developer-configured DB (pre-existing `DuplicateTable` on unrelated `secret_envelope_versions`, **before** reaching 0030). **No production migrate/deploy performed.** Candidate validation should run 0030 upgrade/downgrade on an isolated candidate DB.

---

## 4. Endpoint and transaction behavior

```http
POST /api/v1/client-onboarding/signup
Idempotency-Key: <required>
```

**Body (only):** `full_name`, `email`, `password`, `tenant_name`, `tenant_slug` (`extra=forbid`).

**Server-only config:**

- `client_self_service_onboarding_enabled` (default `false`)
- `client_onboarding_provider_slug` (required when enabled; fail-closed if empty/missing/inactive)

**Atomic steps (single commit):**

1. Resolve host provider by slug (never from client).
2. Idempotency lookup / conflict on key+payload mismatch.
3. Create app-user (hashed password via canonical `hash_password`).
4. Assert **no** `ProviderStaff`.
5. Create tenant under host provider.
6. `BranchService.ensure_default_branch`.
7. Membership `tenant_owner` for the new user.
8. `enable_modules_ordered(["parties","marketing"], as_trial=False)` — whitelist only.
9. Assert active modules exactly `{parties, marketing}`.
10. Persist idempotency completion + audit/security events (no secrets).
11. Commit; issue tokens.

Any error → `rollback()` of the whole unit. No app-auth session required (public endpoint).

**Idempotent replay:** same key + same fingerprint → 201 with same user/tenant and re-issued tokens.  
**Same key + different payload → 409.**

**Redirect path in API:** `/workspace/{slug}/marketing/guide`  
With console `basename=/console` → browser URL `/console/workspace/{slug}/marketing/guide`.

---

## 5. Auth / role / module invariants

| Invariant | Enforcement |
|---|---|
| Never `provider_owner` | No `ProviderStaff` create; post-assert staff is `None` |
| Client cannot choose provider | Forbidden in schema; server slug only |
| Client cannot choose modules/role | Forbidden in schema; hard whitelist constant |
| Exact modules | Assert enabled list + active set == parties+marketing |
| Password | `hash_password` / existing auth crypto only |
| Bootstrap `/auth/register` | Untouched (still one-shot provider bootstrap) |

---

## 6. Tests (exact counts)

### Targeted onboarding

`python -m pytest tests/test_client_onboarding_d1_d3.py -q` → **19 passed**

Coverage includes: happy path; not provider_owner; tenant_owner membership; default branch; exact modules; injection 422; duplicate email/slug; idempotent replay; same key different payload; duplicate submit different keys; IntegrityError mapping; rollbacks (branch/membership/module enable/missing defs); tenant isolation; login after signup; bootstrap register regression.

### Existing regression

`pytest tests/test_auth.py tests/test_tenants.py tests/test_modules.py -q` → **37 passed**

### Frontend

- `npx tsc --noEmit` → **exit 0**
- `npx vite build` → **GREEN** (`dist/assets/index-BkrwSxRg.js`, 201 modules)
- `npx tsx src/pages/clientSignup.contract.test.ts` → **OK** (route/API/helpers/redirect contract)

**Combined counted automated checks this session:** 19 + 37 + 1 frontend contract + tsc + vite build.

---

## 7. Frontend build results

| Check | Result |
|---|---|
| Typecheck | PASS |
| Production Vite build | PASS |
| Contract test (`/register`, Idempotency-Key, redirect helpers) | PASS |

---

## 8. Known limitations

1. Feature flag defaults **off** — dogfood requires env enable + valid `client_onboarding_provider_slug`.
2. No password reset / email verification (out of scope).
3. Production Basic Auth perimeter unchanged (outer gate remains).
4. Existing production test user/tenant **not** quarantined; real-email dogfood still needs separate HQ cleanup gate.
5. Alembic 0030 not applied to any production/stage DB in this task.
6. True multi-threaded concurrency against shared SQLite TestClient is unsafe; covered via unique constraints + IntegrityError mapping + sequential duplicate-key cases instead of threaded SQLite stress.
7. Open public signup rollout (remove Basic Auth) out of scope.

---

## 9. Git status (worktree)

```text
## feature/generic-client-onboarding-d1-d3
 M backend/app/api/v1/router.py
 M backend/app/core/config.py
 M backend/app/core/enums.py
 M backend/app/core/exception_handlers.py
 M backend/app/core/exceptions.py
 M backend/app/modules/models.py
 M platform-console/src/pages/LoginPage.tsx
 M platform-console/src/routes.tsx
?? backend/alembic/versions/20260801_0030_client_onboarding_idempotency.py
?? backend/app/modules/client_onboarding/
?? backend/tests/test_client_onboarding_d1_d3.py
?? platform-console/src/api/clientOnboarding.ts
?? platform-console/src/pages/ClientSignupPage.tsx
?? platform-console/src/pages/clientSignup.contract.test.ts
?? platform-console/src/pages/clientSignupHelpers.ts
?? docs/ai/reports/2026-08-01-generic-client-self-service-onboarding-d1-d3-implementation-report.md
```

No commit / push / merge performed.

---

## 10. Production / stage / test identities

| Surface | Touched? |
|---|---|
| Production app/DB/nginx | **No** |
| Stage | **No** |
| Existing production test user/tenant | **No** (not deleted, not converted) |
| Deploy | **No** |
| M8 / Connections / Publish | **No** |

Confirmation: implementation confined to worktree `feature/generic-client-onboarding-d1-d3` from `ea045164`.

---

## Final verdict

`READY_FOR_GENERIC_ONBOARDING_CANDIDATE_VALIDATION`

**Next HQ gates (not this task):** candidate env with flag+provider slug; alembic 0030 on candidate DB; optional quarantine of blocking test email; browser dogfood behind existing Basic Auth; then separate deploy approval.
