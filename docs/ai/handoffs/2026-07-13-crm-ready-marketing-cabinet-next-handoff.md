# Session Handoff: 2026-07-13 — Core CRM close → Marketing Cabinet

## Branch

**Direction switch (HQ):**  
Core CRM intake **READY / LIVE** · E8-C **closed** · Tenant automation **HOLD** · **Next = Marketing Cabinet**

## Goal of last CRM arc

Довести intake Flexity Sales до рабочего контура: сайт → лид → обработка → accepted / client mark. Без auto-tenant.

## Status (locked)

| Area | Status |
|------|--------|
| Public inbound `/demo` | **LIVE** |
| Match-before-create + rate limit | **LIVE** |
| CRM Board/List + LeadDetailModal | **LIVE** |
| E7 «Данные заявки» | **LIVE** |
| E4 history | **LIVE** |
| E8-B stage help accepted/converted | **LIVE** |
| E8-C «Сделать клиентом» | **LIVE / closed** |
| SOP | `docs/FLEXITY_LEAD_PROCESSING_WORKFLOW.md` |
| E8-D `converted_tenant_id` | **HOLD** |
| E8-E «Создать клиентский контур» | **HOLD** |
| Tenant automation | **HOLD** |

## Key CRM reports

- E5-E launch: `docs/ai/reports/2026-07-13-core-crm-e5-e-public-inbound-controlled-launch-report.md`
- E7-B deploy: `docs/ai/reports/2026-07-13-core-crm-e7-b-lead-application-data-view-deploy-report.md`
- E8-B deploy: `docs/ai/reports/2026-07-13-core-crm-e8-b-stage-help-text-deploy-report.md`
- E8-C deploy: `docs/ai/reports/2026-07-13-core-crm-e8-c-mark-party-as-client-deploy-report.md`
- E8 plan: `docs/ai/plans/2026-07-13-core-crm-e8-accepted-lead-to-client-tenant-plan.md`

## Marketing Cabinet — resume point

**Last local slices (2026-07-10):**

| Slice | Status | Report |
|-------|--------|--------|
| M6-BE1–BE5 | local complete (preflight/approve) | `…-m6-be5-preflight-approval-report.md` |
| M6-FE1 shell | local | `…-m6-fe1-route-nav-shell-report.md` |
| M6-FE2 pack detail editor | local (publish tab disabled) | `…-m6-fe2-pack-detail-editor-report.md` |

**Plan:** `docs/ai/plans/2026-07-09-marketing-cabinet-mvp-implementation-plan.md`  
**TZ:** `docs/ai/plans/2026-07-03-marketing-content-cabinet-product-tz.md`

Likely next FE after FE2 (confirm with HQ before code): **M6-FE3 Topics** / **M6-FE4 Packs list** / publish UI only after BE publish gate — **не** Margosya rewrite.

## Decisions

1. CRM intake closed as ready for Асем daily use.  
2. Tenant / convert automation stays HOLD until separate HQ.  
3. Active product branch = **Marketing Cabinet** inside Flexity (Margosya = thin client later).

## Risks

- Marketing Cabinet code may still be **local-only** (not fully deployed) — verify live state before next slice.  
- Dirty local Flexity tree mixes CRM + marketing + other work — deploy only with explicit HQ scope.  
- Do not reopen CRM tenant automation while on Marketing branch.

## Next safe step

1. HQ: confirm Marketing Cabinet live vs local gap (deployed or not).  
2. Pick one small Marketing slice (e.g. M6-FE3 Topics or FE4 Packs list) with research/plan + approval.  
3. Forbidden until approved: Margosya rewrite, CRM tenant auto, Booking/Clinic/Trailers.

## Forbidden next actions (without HQ)

- E8-D / E8-E / auto-tenant  
- Marketing production deploy without gate  
- Migrations / env without approval  
- Mixing CRM and Marketing in one deploy
