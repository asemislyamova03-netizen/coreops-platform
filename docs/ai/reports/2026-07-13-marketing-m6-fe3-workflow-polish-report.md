# M6-FE3 — Marketing Cabinet workflow polish (local only)

**Date:** 2026-07-13  
**Slice:** M6-FE3  
**Branch context:** Marketing Cabinet / ContentOps Cabinet  
**Scope:** `platform-console` frontend only  

**Plan:** `docs/ai/plans/2026-07-13-marketing-m6-fe3-workflow-polish-plan.md`

## Summary

Marketing Cabinet daily workflow стал usable без publish:

```text
Topics → создать → утвердить → взять в работу → Pack detail
→ тексты → media metadata → preflight → approval
→ Publish tab честно disabled
```

## HQ approval scope

| Allowed | Done |
|---------|------|
| Topics create / approve / take / archive | ✅ |
| Packs list filters + topic column | ✅ |
| Pack detail next-action | ✅ |
| Media metadata edit | ✅ |
| Publish honesty (no fake CTA) | ✅ |
| API client for existing BE endpoints | ✅ |
| Helpers + unit tests + build | ✅ |
| Backend / migrations / deploy / env | ❌ not touched |
| Publish/export / Margosya / binary upload | ❌ not implemented |

## API client additions

`platform-console/src/api/marketing.ts`:

| Method | HTTP |
|--------|------|
| `createMarketingTopic` | `POST /marketing/topics` |
| `updateMarketingTopic` | `PATCH /marketing/topics/{id}` |
| `takeMarketingTopic` | `POST /marketing/topics/{id}/take` |
| `archiveMarketingTopic` | `POST /marketing/topics/{id}/archive` |
| `markMarketingTopicUsed` | `POST /marketing/topics/{id}/mark-used` |

Types added in `src/types/marketing.ts`: create/update/take payloads, `MarketingTakeTopicPackResponse`.

`listMarketingPacks` no longer sends unsupported `search`; optional `planned_date` aligned with BE.

## Topics workflow behavior

- Quick create form (title + rubric) → draft topic.  
- Status badges with RU labels.  
- «Утвердить» for `draft` → `PATCH status=approved`.  
- «Взять в работу» only when `approved` → take → navigate to `/marketing/packs/{packId}`.  
- Hint when not approved: «Взять можно после approval темы».  
- «В архив» via existing archive endpoint.  
- Empty state: «Тем пока нет. Создайте первую тему.»

## Packs list behavior

- Columns: title (link), topic, status, approval, preflight, updated_at, «Открыть».  
- Client-side filters: status / approval_status / preflight_status.  
- Empty: no packs at all vs no packs matching filters.  
- Removed outdated «FE1 только просмотр» subtitle.

## Pack detail next-action

Helper `resolveMarketingNextAction` + UI block «Следующее действие» with tab jump.

| State | Message |
|-------|---------|
| no texts | Заполните тексты для каналов. |
| texts, no active media | Добавьте медиа или укажите, что медиа не требуется. (+ soft note: media optional for preflight) |
| preflight failed | Исправьте ошибки preflight. |
| preflight not passed | Запустите preflight. |
| ready / pending | Можно отправить на approval. |
| approved | Пак готов + publish disabled message |
| rejected | Исправьте замечания и снова запустите preflight. |

Header statuses use RU labels. Publish tab is **viewable** (read-only honesty).

## Media edit behavior

- Add metadata (incl. public_url, alt_text).  
- Inline edit via `updateMarketingMedia`.  
- Archive unchanged.  
- Banner: binary upload not available; metadata/link only.

## Publish disabled behavior

- Fake «Опубликовать (disabled)» button removed.  
- Copy from `MARKETING_PUBLISH_DISABLED_MESSAGE`: публикация выключена; Cabinet = source of truth; export/Margosya later.

## Helpers / tests

| File | Role |
|------|------|
| `marketingLabels.ts` | RU labels + publish disabled constant |
| `marketingNextAction.ts` | next-action resolver |
| `marketingLabels.test.ts` | status/channel/publish constant |
| `marketingNextAction.test.ts` | empty texts / media / failed / approve / approved / rejected |

```bash
npx tsx src/pages/workspace/marketing/marketingLabels.test.ts
npx tsx src/pages/workspace/marketing/marketingNextAction.test.ts
npm run build
```

## Files changed

### Created
- `platform-console/src/pages/workspace/marketing/marketingLabels.ts`
- `platform-console/src/pages/workspace/marketing/marketingLabels.test.ts`
- `platform-console/src/pages/workspace/marketing/marketingNextAction.ts`
- `platform-console/src/pages/workspace/marketing/marketingNextAction.test.ts`
- `docs/ai/reports/2026-07-13-marketing-m6-fe3-workflow-polish-report.md`

### Modified
- `platform-console/src/api/marketing.ts`
- `platform-console/src/types/marketing.ts`
- `platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx`
- `platform-console/src/pages/workspace/marketing/MarketingPacksPage.tsx`
- `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx`
- `platform-console/src/pages/workspace/marketing/MarketingDashboardPage.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailMediaTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/PackDetailPublishTab.tsx`
- `platform-console/src/pages/workspace/marketing/packDetail/marketingErrors.ts`
- `platform-console/src/index.css`

## Files intentionally not touched

- `backend/**`
- migrations / alembic  
- `.env` / deploy / GHA  
- Margosya / content-bank  
- CRM / public inbound / tenants  
- Booking / Clinic / Trailers  

## Build / tests

| Check | Result |
|-------|--------|
| `marketingLabels.test.ts` | ✅ ok |
| `marketingNextAction.test.ts` | ✅ ok |
| `npm run build` (`tsc && vite build`) | ✅ |

## Backend touched

**No.**

## Migration created/run

**No.**

## Env / deploy touched

**No.**

## Risks

1. Take requires topic `approved` — UI exposes approve step; draft take still blocked by BE.  
2. Pack filters are client-side (limit 200).  
3. Next-action «add media» is advisory; media not required by BE preflight.  
4. Marketing module may still be local-only on server — smoke only where module enabled.  
5. Publish tab is readable now — must not be mistaken for live publish (copy is explicit).

## Next recommended step

1. Local manual smoke (topics → take → pack → texts → media edit → preflight → approve → publish honesty).  
2. HQ: decide Marketing Cabinet **deploy gate** (separate approval).  
3. Parallel backend track when ready: **M6-BE6** publish logs + git export (still no auto live publish without gate).  
4. Do not start Margosya rewrite.

---

## HQ summary

1. **Status:** ✅ Complete (M6-FE3 local only)  
2. **Files changed:** 14 (4 new helpers/tests + report; 10 modified FE files)  
3. **Backend touched:** No  
4. **Migration created/run:** No  
5. **Env/deploy touched:** No  
6. **API client additions:** create/update/take/archive/mark-used topic + TakeTopic types  
7. **Topics workflow:** create → approve → take→navigate; archive; empty state  
8. **Packs list:** topic col, client filters, open detail, updated subtitle  
9. **Pack detail next-action:** helper + UI block with tab jump  
10. **Media edit:** inline metadata edit via existing PATCH  
11. **Publish disabled:** honesty message, no fake publish button; tab viewable  
12. **Helpers/tests:** labels + next-action; both tsx tests ✅  
13. **Build/tests:** helper tests ✅; `npm run build` ✅  
14. **Not touched:** backend, migrations, env, deploy, Margosya, CRM, publish/export  
15. **Risks:** take gate, client filters, local-only module, advisory media step  
16. **Next:** local smoke → HQ deploy gate or M6-BE6 plan  
