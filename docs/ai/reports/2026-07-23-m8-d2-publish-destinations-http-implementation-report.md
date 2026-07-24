# Report: M8-D2 MarketingPublishDestination HTTP API

**Date:** 2026-07-23
**Worktree:** `.worktrees/marketing-m8b-http-clean`
**Branch:** `feature/marketing-m8b-http-clean-main`
**Baseline HEAD (start):** `333364750e7bae8bf2edad3549f2560b3b04071b`
**Category:** `universal_module` (Marketing)
**Slice:** D2 — HTTP API + RBAC + redaction + structural validate
**Status:** implemented + provider-staff RBAC evidence (checkpoint pending HQ)

## Goal

Add tenant-scoped Publish Destination HTTP API under `/marketing/publish-destinations`, mirroring M8-B publishing-connections RBAC and redaction. No adapters, dry-run, execute, migrations, or frontend.

## Classification

| Field | Value |
|---|---|
| Project | Flexity |
| Layer | universal_module |
| Risk | medium (multi-tenant HTTP; secrets adjacency) |

## Endpoint / RBAC matrix

Base prefix: `/api/v1/marketing` + `Depends(require_module("marketing"))`

| Method | Path | RBAC |
|---|---|---|
| GET | `/publish-destinations` | MEMBER+ |
| GET | `/publish-destinations/{id}` | MEMBER+ |
| POST | `/publish-destinations` | OWNER/ADMIN (+ provider staff via `require_marketing_destination_admin`) |
| PATCH | `/publish-destinations/{id}` | OWNER/ADMIN (+ staff) |
| POST | `/publish-destinations/{id}/disable` | OWNER/ADMIN (+ staff) |
| POST | `/publish-destinations/{id}/enable` | OWNER/ADMIN (+ staff) |
| POST | `/publish-destinations/{id}/validate` | OWNER/ADMIN (+ staff) |
| POST | `/publish-destinations/{id}/archive` | OWNER/ADMIN (+ staff) |
| DELETE | — | **not registered** (soft archive only) |

Optional nested `GET /publishing-connections/{id}/destinations` **not** added (would conflict with M8-B guard that nested destinations stay absent).

## Functional decisions (D2)

| Topic | Behavior |
|---|---|
| Cross-tenant | Missing / other-tenant connection or destination → **404** |
| Validate | Structural only; no provider calls. Capability-enabled → `unavailable` + `provider_adapter_unavailable`. TikTok → `unavailable` + `capability_disabled`. Never invents `valid`. |
| TikTok | Create defaults `disabled`; enable / VALID fail-closed |
| Redaction | `PublishDestinationView` has no secret fields; responses audited in tests |
| Metadata keys | Forbidden-key check uses casefold + separator strip + camelCase split |
| Display name | max 255; control characters rejected |
| Identity lock | Still enforced by domain; HTTP validate does not set VALID; lock tested via domain then PATCH API |

## Files changed

| Path | Change |
|---|---|
| `backend/app/modules/marketing/routes.py` | Destination list/get/create/patch/lifecycle/validate routes |
| `backend/app/modules/marketing/schemas.py` | `PublishDestinationCreate` / `PublishDestinationUpdate` |
| `backend/app/modules/marketing/deps.py` | `require_marketing_destination_admin` alias + `get_publish_destination_service` |
| `backend/app/modules/marketing/repository.py` | display_name validator; list filters; `structural_validate_publish_destination` |
| `backend/app/modules/marketing/service/publish_destination_validation.py` | Stronger key normalization + display_name rules |
| `backend/app/modules/marketing/service/publish_destinations.py` | **NEW** HTTP orchestration service |
| `backend/tests/test_marketing_publish_destinations_api.py` | **NEW** API tests (+ same-company staff mutate; foreign staff denied) |
| `backend/tests/test_marketing_publishing_connections_api.py` | Drop obsolete “no `/publish-destinations`” assertion (nested guards kept) |
| `docs/ai/plans/2026-07-23-m8-d-destinations-publish-contract-plan.md` | D2 status note |
| `docs/ai/reports/2026-07-23-m8-d2-publish-destinations-http-implementation-report.md` | This report |

## Intentionally not touched

- Migrations / alembic / models table constraints (0026 remains head)
- Adapters / dry-run / execute / frontend
- Nested connection destinations route
- Dirty Flexity root
- Commit / push / deploy

## Allow-list note

`test_marketing_publishing_connections_api.py` required a **minimal** edit: D1-era guard asserted top-level `/publish-destinations` must 404; D2 HQ route table requires that path. Nested `/publishing-connections/{id}/destinations|publish|dry-run` guards remain.

## Checks (session)

| Check | Result |
|---|---|
| `pytest` destinations API + model + publishing connections (HTTP + service) | **64 passed** (pre staff evidence) |
| Provider-staff HTTP evidence | same-company staff PATCH ok; foreign staff 403 (no access / MEMBER cannot mutate) |
| `git diff --check` (changed paths) | clean |
| Alembic heads | single head `0026_mkt_publish_destinations` |
| Migration files changed | **none** |
| Production code for staff evidence | **unchanged** (test-only remediation) |

## Next safe step

**D3** (separate HQ approval): dry-run contract HTTP + persistence — still no Telegram adapter / execute.

## Stop confirmation

D2 HTTP + staff RBAC evidence complete in worktree. **No push. No migrations. No adapters. No dry-run/execute.**
