# Re-review — M7-D historical-publish API

**Date:** 2026-07-15
**Scope:** path-scoped re-review after rollup blocker fix
**Recommendation:** **APPROVE COMMIT**

## Scope

Reviewed implementation paths:

- `backend/app/modules/marketing/schemas.py`
- `backend/app/modules/marketing/repository.py`
- `backend/app/modules/marketing/service/historical_publish.py`
- `backend/app/modules/marketing/routes.py`
- `backend/tests/test_marketing_historical_publish.py`
- M7-D implementation plan and reports.

The staged area is empty. The repository has unrelated dirty WIP, but no unrelated files are required for this API slice. No frontend, migration, deploy script, environment, or secret file belongs to the slice.

## Blocker fix

The service writes `needs_review` into each historical audit log's `metadata_json`, then excludes logs whose value is true from confirmed channel coverage:

```text
historical_record + recorded + needs_review is not true
```

Therefore a Telegram historical log marked `needs_review=true` remains visible as audit evidence but cannot combine with a later confirmed Instagram record to set `publish_status=published`. The focused test covers this scenario and passes.

Confirmed Telegram plus confirmed Instagram still produces `published`.

## API safety and correctness

- The endpoint remains tenant-scoped through the existing `TenantContext` and `require_module("marketing")`.
- Tenant-scoped pack lookup returns `404` for missing and cross-tenant packs.
- Unknown channels are schema-rejected with `422`.
- `pack.status=publishing` returns `409` before a log is created or `publish_status` is changed.
- The service writes only historical audit logs and `pack.publish_status`.
- It does not mutate pack workflow `status`, approval status, or approval/preflight data.
- No external publisher, Margosya, queue/enqueue, or export call/import exists.
- `queue_item_id` is set to `None`.
- No direct SQL hack or migration is required.

## Rollup and idempotency

- Default targets are Telegram plus Instagram.
- Telegram-only, Instagram-only, and insights-site-only remain `partial`.
- Existing confirmed historical logs are included in rollup.
- Evidence-reference idempotency is covered.
- The no-evidence fallback is covered with a fixed `published_at` date and does not duplicate logs.
- `partially_published` is not used; only existing `MarketingPublishStatus` enum values are assigned.

## Validation

```text
python -m py_compile app/modules/marketing/schemas.py app/modules/marketing/repository.py app/modules/marketing/service/historical_publish.py
# passed

python -m pytest tests/test_marketing_historical_publish.py -q
# 12 passed

python -m pytest tests/test_marketing_preflight_approval.py tests/test_marketing_packs.py -q
# 36 passed
```

Tests report the repository's existing SQLite cleanup warning for the `branches`/`tenants` foreign-key cycle.

## Non-blocking risk

Idempotency is application-level. Concurrent identical requests can still race because there is no database unique constraint. Adding such a constraint would need a separately approved migration and is out of scope for this v1 slice.

## Result

The prior blocker is resolved and the path-scoped slice is suitable for a later **path-scoped commit only**. Deploy, Wave A historical marking, and migrations remain separate decisions requiring separate HQ approval.
