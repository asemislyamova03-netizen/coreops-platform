# M6-FE2 — Marketing Pack Detail editor UI (local only)

**Date:** 2026-07-10  
**Slice:** M6-FE2  
**Branch context:** Marketing Cabinet / ContentOps Cabinet  
**Scope:** platform-console frontend only  

## Summary

Pack detail стал минимально рабочим: редактирование текстов по каналам, metadata media, запуск preflight, approve/reject с обновлением pack detail после каждого действия. Publish tab остаётся disabled (кнопка вкладки недоступна).

**Prerequisite:** M6-FE1 shell — `docs/ai/reports/2026-07-10-marketing-cabinet-m6-fe1-route-nav-shell-report.md`

## HQ approval scope

| Allowed | Done |
|---------|------|
| Text edit per channel | ✅ |
| Media metadata form/list | ✅ |
| Preflight action | ✅ |
| Approve/reject actions | ✅ |
| Reload pack detail after actions | ✅ |
| Publish disabled | ✅ |
| Backend changes | ❌ not touched |
| File upload / object storage | ❌ not implemented |
| Margosya / git export | ❌ not touched |

## API client methods added

`platform-console/src/api/marketing.ts`:

| Method | HTTP |
|--------|------|
| `updateMarketingPackText(packId, channel, payload)` | `PUT /marketing/packs/{id}/texts/{channel}` |
| `listMarketingPackMedia(packId)` | `GET /marketing/packs/{id}/media` |
| `addMarketingPackMedia(packId, payload)` | `POST /marketing/packs/{id}/media` |
| `updateMarketingMedia(assetId, payload)` | `PATCH /marketing/media/{assetId}` |
| `deleteMarketingMedia(assetId)` | `DELETE /marketing/media/{assetId}` (soft archive) |
| `runMarketingPreflight(packId)` | `POST /marketing/packs/{id}/preflight` |
| `approveMarketingPack(packId, note?)` | `POST /marketing/packs/{id}/approve` |
| `rejectMarketingPack(packId, reason?)` | `POST /marketing/packs/{id}/reject` |

Types extended in `src/types/marketing.ts`: channels, text/media payloads, `MarketingPreflightResponse`.

## Tab behaviors

### Texts
- 4 канала: telegram, instagram, threads, insights
- Textarea + «Сохранить» per channel
- Показ version, char_count, status после save
- Saved/error state per channel
- `invalidateQueries(["marketing-pack", packId])` после save → обновление статусов pack (approval reset от backend)

### Media
- Info: «Файл пока не загружается, сохраняется только metadata.»
- Form: file_name, mime_type, storage_provider, storage_key, preview_url, width, height
- List active assets из pack detail
- «Архивировать» → DELETE metadata (soft archive)
- `updateMarketingMedia` добавлен в client для следующих слайсов (edit inline не в scope FE2 UI)

### Preflight
- Показ preflight_status, pack status, approval_status, preflight_at
- Кнопка «Запустить preflight»
- Отчёт: errors, warnings, checks из `PreflightResponse`
- Reload pack detail после run

### Approval
- Показ approval_status, approved_at
- Approve enabled только при `preflight_status === "passed"`
- Reject с optional reason
- 409 `preflight_not_passed` → friendly message через `formatMarketingApiError`
- Reload pack detail после approve/reject

### Publish
- Tab button **disabled** (как в FE1)
- Content component готов с текстом gate + disabled button (недоступен через UI пока tab disabled)

### Logs
- Read-only список `publish_logs` из pack detail

## Files changed

### Created
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailTextsTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailMediaTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailApprovalTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailPublishTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailLogsTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/marketingErrors.ts`

### Modified
- `platform-console/src/api/marketing.ts`
- `platform-console/src/types/marketing.ts`
- `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx`
- `platform-console/src/index.css`

## Files intentionally not touched

- `backend/**`
- Margosya / content-bank
- Marketing dashboard, topics list, packs list pages (FE1)
- Deploy / GHA / migrations
- CRM, Booking, Clinic, Trailers

## Build / tests

```bash
cd platform-console && npm run build
```

- **Result:** ✅ pass (`tsc && vite build`)
- Frontend test script: not configured

## Manual local smoke (recommended)

1. Marketing → Packs → open pack detail
2. Texts: edit Telegram → Save → verify version/char_count
3. Media: add metadata row → list updates
4. Preflight: run → see report or errors
5. If passed: Approve
6. Edit text again → verify status reset (preflight/approval)
7. Confirm Publish tab button disabled

## Backend touched

**No.**

## Deploy needed

**No** — local-only slice.

## Risks

1. Publish tab content exists but tab nav disabled — intentional per FE1/M6 decision.
2. `updateMarketingMedia` in client without UI yet — dead code until FE3 edit flow.
3. Preflight report not persisted in pack detail API schema — UI keeps last run in component state only until page reload.
4. Reject/approve errors besides 409 shown as raw API messages if unmapped.
5. No optimistic updates — UI waits for refetch after mutations.

## Next recommended step

**M6-FE3** (or next approved slice):

1. Enable Publish tab read-only preview when BE6 ready; still no publish button until gate
2. Inline media edit via `updateMarketingMedia`
3. Topics → take topic → navigate to new pack
4. Pack list filters (pending approval)
5. Optional: persist preflight report in pack detail if backend exposes `preflight_report_json`

Parallel backend: **M6-BE6** publish logs + git export.

---

## HQ summary

1. **Status:** ✅ Complete (M6-FE2 local only)
2. **Files changed:** 11 files (7 created, 4 modified)
3. **API client methods added:** 8 (see table above)
4. **Texts tab behavior:** per-channel textarea + save + version/char_count + reload
5. **Media tab behavior:** metadata-only add/list/archive, no file upload
6. **Preflight tab behavior:** run button + errors/warnings/checks report + reload
7. **Approval tab behavior:** approve (after preflight passed) + reject with optional reason + 409 handling
8. **Publish tab disabled:** yes — tab button disabled, no active publish
9. **Build/tests:** `npm run build` ✅
10. **Backend touched:** No
11. **Deploy needed:** No
12. **What was not touched:** backend, Margosya, publish/git export, file storage, other workspace sections
13. **Risks:** preflight report session-only, publish tab inaccessible, no media inline edit UI
14. **Next recommended step:** M6-FE3 topics→pack flow + media edit; or M6-BE6 publish/git export
