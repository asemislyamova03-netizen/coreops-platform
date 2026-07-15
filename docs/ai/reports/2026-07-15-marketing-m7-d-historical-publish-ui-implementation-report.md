# Implementation Report — M7-D historical-publish UI clarification

**Date:** 2026-07-15
**Project:** Flexity / `coreops-platform`
**HQ approval:** `APPROVED: implement historical-publish UI clarification`
**Scope:** frontend Pack Detail only; no deployment

## Status

## ✅ IMPLEMENTED LOCALLY — VERIFIED

The Pack Detail UI now distinguishes a verified historical publication record from a generic live-publish interpretation. The Publish tab remains disabled and no backend/API/data behavior changed.

## Frontend changes

### Historical status clarification

`MarketingPackDetailPage` now detects a historical publication only when both conditions hold:

```text
publish_status === "published"
and at least one publish log is historical_record / recorded
```

For that case, the status label is:

```text
Публикация: Опубликовано ранее
```

The metadata area also shows:

```text
Это отметка о прошлой публикации. Flexity не публиковал этот пост автоматически.
```

Normal `published` responses without a recorded historical log keep the existing generic label.

### Log label mapping

The Logs tab now renders:

```text
historical_record → Историческая отметка публикации
```

Unknown actions safely retain their original value instead of being mislabelled.

### Publish tab

The Publish tab is still informational and disabled. For historical records it adds the same “past publication” clarification. It does not expose a live publish, export, Margosya, or queue action.

## Files changed

- `platform-console/src/pages/workspace/marketing/marketingLabels.ts`
- `platform-console/src/pages/workspace/marketing/marketingLabels.test.ts`
- `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailLogsTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailPublishTab.tsx`
- `docs/ai/plans/2026-07-15-marketing-m7-d-historical-publish-ui-followup-plan.md`
- `docs/ai/reports/2026-07-15-marketing-m7-d-historical-publish-ui-implementation-report.md`

No type, CSS, Pack List, backend, API, migration, deployment, or production-data file was changed.

## Validation

| Check | Result |
|---|---|
| `npx tsx src/pages/workspace/marketing/marketingLabels.test.ts` | passed |
| `npm run build` | passed (`tsc` + Vite production build) |
| IDE diagnostics for changed frontend files | no errors |

The focused test verifies:

- `published` plus a recorded `historical_record` resolves to `Опубликовано ранее`;
- `not_started` does not receive the historical marker;
- `historical_record` maps to the required Russian label;
- unknown action fallback is preserved;
- existing disabled-publish text remains.

## Safety confirmation

- Backend/API: not changed.
- Database/API production writes: none.
- Migrations/environment: none.
- Pack List: not changed.
- Pack workflow/approval/publish statuses: not mutated.
- Publish/export/Margosya: not invoked or enabled.
- Deploy/commit/push: not performed.

## Risks / notes

1. The generic marker correctly avoids claiming a specific archive source. Existing Pack Detail log responses do not expose `source`, `evidence_ref`, or `needs_review`.
2. Pack List intentionally remains unchanged. A list-level origin badge needs a separate backend summary contract; adding detail lookups per row would be the wrong first solution.
3. Browser verification still requires a separately approved console deployment. Until then, this is a locally built frontend slice only.

## Next recommended step

Review the local UI diff, then request a separate commit/PR approval. Deploy is a distinct later gate. After a future approved console deploy, manually check:

1. a Wave A pack with historical TG+IG logs;
2. `ai-personal-content-assistant`;
3. `1s-erp-novogo-pokoleniya`;
4. the Publish tab remains disabled.
