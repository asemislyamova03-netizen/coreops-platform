# Review — M7-D historical-publish API

**Date:** 2026-07-15
**Scope:** path-scoped review only
**Recommendation:** **REQUEST CHANGES**

## Scope check

Implementation files reviewed:

- `backend/app/modules/marketing/schemas.py`
- `backend/app/modules/marketing/repository.py`
- `backend/app/modules/marketing/service/historical_publish.py`
- `backend/app/modules/marketing/routes.py`
- `backend/tests/test_marketing_historical_publish.py`
- `docs/ai/plans/2026-07-14-marketing-m7-d-historical-publish-implementation-plan.md`
- `docs/ai/reports/2026-07-14-marketing-m7-d-historical-publish-api-implementation-report.md`

The repository has substantial unrelated dirty WIP, but the reviewed implementation itself is limited to the approved Marketing paths. The staged area is empty.

## API correctness

- Route matches the existing Marketing router convention:
  `POST /api/v1/marketing/packs/{pack_id}/record-historical-publish`.
- It uses `require_module("marketing")`, `TenantContext`, and the existing DB dependency.
- Pack lookup is tenant-scoped; missing and cross-tenant packs resolve as `404`.
- `Literal` request channel validation returns `422` for an unknown channel.
- `historical_record` is valid without a migration because `MarketingPublishLog.action` is a string field.
- `MarketingPublishStatus` already defines `not_started`, `partial`, `published`, and `failed`; `partially_published` is not used.

## Publish safety

- No external publisher, queue/enqueue, export, or Margosya call/import is present in the service.
- `queue_item_id` is explicitly `None`.
- The service does not call approval/preflight services.
- It does not mutate `pack.status` or `approval_status`; it only assigns `publish_status`.
- No migration or production write was run in this review.

## Rollup and idempotency

Correct:

- Default target set is Telegram + Instagram.
- Both channels produce `published`; incomplete default target coverage produces `partial`.
- Historical log rows from previous requests are included in the channel rollup.
- Idempotency lookup scopes by tenant, pack, channel, `historical_record`, source, and evidence reference; the no-evidence fallback uses the publication date.

### Required change

`needs_review` is evaluated only from the current request. It is stored in each historical log's `metadata_json`, but `_rollup_publish_status()` does not inspect prior historical log metadata.

Reproduction:

1. Record Telegram with `needs_review=true` → `partial`.
2. Later record Instagram with `needs_review=false`.
3. Both default targets are present, so the current code returns `published`.

This violates the approved rollup rule that content requiring review remains `partial`, and it conflicts with the requirement to include prior historical records in rollup. The follow-up implementation must preserve a partial status whenever any included historical record has `metadata_json["needs_review"] == true`, unless a separately designed review-clearance flow exists.

## Test coverage

Passed:

```text
python -m py_compile app/modules/marketing/schemas.py app/modules/marketing/repository.py app/modules/marketing/service/historical_publish.py
# passed

python -m pytest tests/test_marketing_historical_publish.py -q
# 8 passed

python -m pytest tests/test_marketing_preflight_approval.py tests/test_marketing_packs.py -q
# 36 passed
```

The tests emit the repository's existing SQLite cleanup warning for the `branches`/`tenants` foreign-key cycle.

Missing focused coverage to add with the required fix:

- a prior `needs_review=true` log plus later missing target channel remains `partial`;
- Instagram-only is `partial`;
- no-evidence date fallback is idempotent;
- `pack.status=publishing` returns `409`.

## Review result

Do not commit this API slice yet. Request a small approved fix limited to the Marketing service and focused tests, then repeat this review.

## Not touched

- Deploy, migration, staging, commit, push.
- Production API and SQL.
- Frontend.
- Wave A.
- Pack approval/workflow implementation.
- Publisher/export/Margosya integrations.
