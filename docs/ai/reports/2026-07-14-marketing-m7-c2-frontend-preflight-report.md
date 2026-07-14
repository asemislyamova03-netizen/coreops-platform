# Report — Marketing M7-C2 Frontend Preflight UI

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Status:** IMPLEMENTATION COMPLETE (local; not committed; not deployed)  
**Category:** universal_module (marketing frontend)

**Related:**
- Product/UX: `docs/ai/plans/2026-07-14-marketing-m7-c2-preflight-ui-plan.md`
- Implementation: `docs/ai/plans/2026-07-14-marketing-m7-c2-implementation-plan.md`
- M7-C1 (merged, not deployed): PR #100 → `fcfa4a7` / `47e2731`

---

## Goal

Читаемый Preflight v2 UX на Pack Detail: blockers / warnings / checklist / topic / channels / media, с совместимостью M6.

---

## What changed

### Helpers / normalization

Новый `marketingPreflight.ts`:

- `normalizePreflightReport` — API response **или** `preflight_report_json`
- aliases: `blockers` ← `blockers || errors`, `checklist` ← `checklist || checks`
- string/object issue arrays
- `resolvePreflightSummaryTone` → `empty | failed | warning | passed`
- RU labels for known blocker/warning/check codes + unknown fallback

### UI sections (`PackDetailPreflightTab`)

1. Summary banner (RU)
2. Что нужно исправить
3. На что обратить внимание (+ «не блокируют»)
4. Чеклист качества
5. Контекст темы
6. Каналы
7. Медиа

Hydration: last report from `pack.preflight_report_json` if present; live run overrides.

### Types

Additive v2 fields on `MarketingPreflightResponse`; `preflight_report_json` on pack detail.

### Microcopy

- Completeness note clarifies hard checks are on Preflight tab.
- Approval tab notes warnings do not block approve.

---

## Compatibility

| Shape | Supported |
|-------|-----------|
| M6 (`errors`/`warnings`/`checks`) | yes |
| M7-C1 v2 (+ summaries) | yes |
| Missing / empty report | banner «ещё не запускалась» |
| Unknown codes | `Неизвестная проверка: <code>` |

---

## Checks run

```text
npx tsx src/pages/workspace/marketing/marketingPreflight.test.ts   → passed
npx tsx src/pages/workspace/marketing/marketingPackContext.test.ts → ok
npx tsx src/pages/workspace/marketing/marketingTaxonomy.test.ts    → ok
npx tsx src/pages/workspace/marketing/marketingLabels.test.ts      → ok
npm run build                                                      → GREEN
```

Build artifacts (local, not deployed):

- `dist/assets/index-CgVHM5HT.js`
- `dist/assets/index-Cn_Q_hGN.css`

---

## Files changed

```text
platform-console/src/types/marketing.ts
platform-console/src/pages/workspace/marketing/marketingPreflight.ts          # NEW
platform-console/src/pages/workspace/marketing/marketingPreflight.test.ts     # NEW
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx
platform-console/src/pages/workspace/marketing/packDetail/PackDetailApprovalTab.tsx
platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx
platform-console/src/index.css
docs/ai/plans/2026-07-14-marketing-m7-c2-implementation-plan.md
docs/ai/reports/2026-07-14-marketing-m7-c2-frontend-preflight-report.md       # this file
```

(Planning docs from prior gate may still be untracked.)

---

## Explicitly not done

- backend / rules / migration  
- commit / push / deploy  
- publish / Margosya / M7-D  
- production / server / DB  

---

## Risks

1. Full v2 panels appear only after joint C1+C2 deploy (M6 backend still OK with fallback UI).  
2. Checklist can be long — labels + unknown fallback.  
3. Local `dist/` rebuilt — do not treat as production until allow-list deploy.

---

## Next recommended step

HQ approve **commit + PR** for M7-C2 (FE only) → merge → then **joint C1+C2 deploy** planning (no auto-deploy).
