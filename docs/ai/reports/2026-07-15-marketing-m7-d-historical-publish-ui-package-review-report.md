# Package Review Report — M7-D historical-publish UI clarification

**Date:** 2026-07-15
**Gate:** `APPROVED: historical-publish UI package review`
**Review mode:** local diff and frontend validation only

## Review status

## ✅ APPROVE COMMIT

The reviewed slice is a small frontend-only clarification. It meets the approved UX goal, contains no backend or operational scope drift, and passed the focused test plus production frontend build.

## Git and dirty-tree review

- Branch: `feature/marketing-m6-package`.
- The repository has substantial pre-existing unrelated WIP across backend, console, scripts, docs, and local artifacts.
- The staged area is **empty**.
- Only the following path-scoped files belong to this package:

```text
platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx
platform-console/src/pages/workspace/marketing/marketingLabels.ts
platform-console/src/pages/workspace/marketing/marketingLabels.test.ts
platform-console/src/pages/workspace/marketing/packDetail/PackDetailLogsTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPublishTab.tsx
docs/ai/plans/2026-07-15-marketing-m7-d-historical-publish-ui-followup-plan.md
docs/ai/reports/2026-07-15-marketing-m7-d-historical-publish-ui-implementation-report.md
docs/ai/reports/2026-07-15-marketing-m7-d-historical-publish-ui-package-review-report.md
```

No other dirty file is part of this review or may be staged for a later package commit.

## Scope review

| Check | Result |
|---|---|
| Frontend Pack Detail / labels / focused test only | pass |
| Pack List changed | no |
| Backend/API routes or schemas changed | no |
| Alembic/migration/env/secrets changed | no |
| Production scripts or Wave A artifacts changed | no |
| Publish/export/Margosya implementation added | no |
| Approval/workflow UI behavior changed | no |
| Dependencies added | no |

## UI behavior review

### Historical state discrimination

The historical marker is emitted only when:

```text
publish_status === "published"
and a log is historical_record / recorded
```

This avoids incorrectly classifying an ordinary future live `published` state as historical.

### User-facing copy

- Pack Detail label: `Опубликовано ранее`.
- Detail note: `Это отметка о прошлой публикации. Flexity не публиковал этот пост автоматически.`
- Logs action mapping: `historical_record → Историческая отметка публикации`.
- Unknown log action: safe raw fallback, so new backend action values are not falsely translated.

### Publish controls

The existing Publish tab remains informational and disabled. The change adds only a contextual historical note; it adds no live publish, export, Margosya, queue, approval, or workflow action.

## Tests and build

| Command | Result |
|---|---|
| `npx tsx src/pages/workspace/marketing/marketingLabels.test.ts` | pass |
| `npm run build` | pass (`tsc` + Vite production build) |
| Changed-file IDE diagnostics | no errors |

## Risks / non-blocking notes

1. Browser verification is still pending a separate console deployment gate; this review validates the local production build only.
2. The UI intentionally does not state a specific historical source such as Margosya, because the current detail contract does not expose log source/evidence metadata.
3. A Pack List historical marker remains deferred. It requires a separate backend summary contract; the reviewed slice correctly avoids per-row detail fetches.
4. The path-scoped commit must explicitly add only the files listed in this report because the working tree contains unrelated WIP.

## Recommendation

**APPROVE COMMIT**

The future commit must be path-scoped to this package only. Commit does not authorize a push, console deploy, browser smoke, production data write, or any publish/Margosya operation.

## What was not touched

- backend, API, migrations, environment, and production data;
- Pack List and unrelated console WIP;
- publish/export/Margosya, approval, workflow, and Wave A state;
- deploy, commit, and push.

## Next recommended step

Request a separate explicit approval for a path-scoped local commit of only the reviewed package files. Keep deploy and live browser smoke as independent later gates.
