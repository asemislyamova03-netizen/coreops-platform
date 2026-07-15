# Implementation Plan — M7-D historical publication state UI clarification

**Status:** implemented locally — verification pending
**Project:** Flexity / `coreops-platform`
**Category:** universal Marketing module, frontend-only follow-up
**Risk:** low

## Goal

Make it clear in Pack Detail that `publish_status=published` can mean a verified **past** publication recorded through M7-D, not a new automatic publication by Flexity.

## Scope

### Planned frontend files

1. `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx`
   - derive a read-only `hasHistoricalPublication` flag from `publish_status` and `publish_logs`;
   - show a neutral Russian “Опубликовано ранее” marker and explanatory copy in the detail metadata.

2. `platform-console/src/pages/workspace/marketing/packDetail/PackDetailPublishTab.tsx`
   - accept the derived boolean;
   - retain the disabled Publish state;
   - show the historical-publication note only when applicable.

3. `platform-console/src/pages/workspace/marketing/packDetail/PackDetailLogsTab.tsx`
   - render a Russian human-facing label for `historical_record`;
   - retain raw log data and keep the tab read-only.

4. `platform-console/src/pages/workspace/marketing/marketingLabels.ts`
   - add minimal shared labels for the historical marker and action.

5. Focused frontend test file(s) adjacent to the existing Marketing tests
   - test the predicate and labels for a historical record;
   - test that `not_started` packs do not receive the marker.

### Explicitly not planned

- `backend/**`
- migrations/Alembic
- API contracts
- `platform-console/src/pages/workspace/marketing/MarketingPacksPage.tsx`
- publish/export/Margosya implementation or enablement
- log mutation/cleanup
- workflow or approval changes
- List-level badge or dashboard counting

## Existing data contract

The implementation uses existing `MarketingPackDetail` fields:

```text
publish_status
publish_logs[].action
publish_logs[].status
```

The required predicate is:

```text
publish_status === "published"
&& publish_logs.some(log =>
  log.action === "historical_record" && log.status === "recorded"
)
```

No backend change is needed for this generic message. Do not display “Margosya archive” as a factual source label: the current detail contract does not expose the historical log source/evidence metadata.

## UI copy

Primary marker:

```text
Опубликовано ранее
```

Explanatory copy:

```text
Историческая отметка: публикация подтверждена ранее.
Flexity не публиковал этот пост автоматически.
```

Log action label:

```text
Историческая публикация
```

## Acceptance criteria

1. A Wave A pack with two recorded `historical_record` logs shows the marker and explanatory copy.
2. Its workflow and approval labels still render independently as `Готов к согласованию` and `Черновик`.
3. `ai-personal-content-assistant` and `1s-erp-novogo-pokoleniya` remain visually unmarked while `publish_status=not_started`.
4. Publish tab remains disabled; no control calls an outbound publish/export/Margosya API.
5. Logs tab shows a human-readable historical action label.
6. Existing Pack List stays unchanged.
7. Focused tests and frontend build/type check pass.

## Verification plan

1. Run focused tests for the new predicate/labels.
2. Run the relevant frontend type/build check.
3. Inspect diff: only the approved frontend files and tests.
4. Manual browser smoke after a separately approved console deploy:
   - one historically marked Wave A pack;
   - `ai-personal-content-assistant`;
   - `1s-erp-novogo-pokoleniya`;
   - Publish tab remains disabled.

## Risks

- Treating every `published` status as historical would be wrong; the marker must require recorded `historical_record` logs.
- Hardcoding “Margosya” would be inaccurate for future imports from other sources.
- A list-level marker without a backend summary would either be incomplete or create avoidable per-row detail requests.

## Rollback

Frontend-only: revert the small UI slice and redeploy the prior console bundle through a separately approved operational procedure. No database data or backend rollback is involved.

## Approval required

Implementation approval received:

```text
APPROVED: implement M7-D historical publication UI clarification
Scope:
- frontend Pack Detail only
- exact files listed in this plan
- no backend/API/migration/publish enablement
```

## Implementation record

- [x] Added historical-publication predicate and RU action/status labels.
- [x] Clarified the Pack Detail publication status and added the no-auto-publish note.
- [x] Kept the Publish tab disabled and added the contextual historical note.
- [x] Replaced the raw `historical_record` action in Logs with a human-readable label.
- [x] Added focused label/predicate coverage.
- [x] Ran focused frontend test and production-equivalent frontend build.
- [x] Reviewed path-scoped diff; no deploy, commit, or push is part of this plan.
