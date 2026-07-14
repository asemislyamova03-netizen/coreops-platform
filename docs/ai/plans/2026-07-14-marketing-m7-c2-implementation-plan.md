# Implementation Plan — Marketing M7-C2 Preflight UI

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Category:** `universal_module` (marketing frontend)  
**Risk:** low–medium  
**Status:** APPROVED and implemented (local; await commit/PR)  
**Baseline:** M7-C1 **merged** (`fcfa4a7` / `47e2731`), **not deployed**; prod still M7-B; alembic **0015**

**Related:**
- Product/UX: `docs/ai/plans/2026-07-14-marketing-m7-c2-preflight-ui-plan.md`
- Planning report: `docs/ai/reports/2026-07-14-marketing-m7-c2-planning-report.md`
- C1 backend PR: [#100](https://github.com/asemislyamova03-netizen/coreops-platform/pull/100)

---

## Goal

Frontend-only: человекочитаемый Preflight v2 UX на Pack Detail, совместимый с M6 reports, без backend/migration/publish.

---

## Task Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | universal_module (marketing) |
| Risk | low–medium |
| Migration | **none** |
| Backend change | **none** (consume C1 additive fields) |
| Forbidden | backend rules, alembic, env, deploy, publish/Margosya, CRM/inbound, smoke cleanup, force-push |

---

## Files to modify

```text
platform-console/src/types/marketing.ts
platform-console/src/pages/workspace/marketing/marketingPreflight.ts          # NEW
platform-console/src/pages/workspace/marketing/marketingPreflight.test.ts     # NEW
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx
platform-console/src/index.css
```

Optional tiny polish (only if needed for copy consistency):

```text
platform-console/src/pages/workspace/marketing/packDetail/PackDetailApprovalTab.tsx
platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx   # note near soft-completeness only
```

**Do not use alternate names unless files already exist** — today there is **no** `marketingPreflight.ts`; create it. Keep maps out of `marketingLabels.ts` (statuses stay there; issue/check maps → `marketingPreflight.ts`).

## Files not to touch

```text
backend/**                          # no C2 backend
backend/alembic/**
.env / secrets / credentials
platform-console/dist/**
node_modules/**
any CRM / inbound / landing / booking
PackDetailPublishTab publish enablement
smoke DB cleanup scripts
```

---

## Steps

### 1. Extend types (`types/marketing.ts`)

Additive only:

- `MarketingPackDetail.preflight_report_json?: Record<string, unknown>` (or typed partial).
- Extend `MarketingPreflightResponse` with optional:
  - `version?: string`
  - `passed?: boolean`
  - `blockers?: MarketingPreflightIssue[]`
  - `checklist?: MarketingPreflightCheck[]`
  - `topic_context_summary?: MarketingPreflightTopicContextSummary | null`
  - `channel_checks?: MarketingPreflightChannelCheck[]`
  - `media_checks?: MarketingPreflightMediaChecks`
- Add small interfaces for summary / channel_checks / media_checks matching C1:
  - channel: `{ channel, present, length, short_warn, below_blocker_threshold }`
  - media: `{ count, missing }`
  - topic summary: fields from `topic_context_summary_from_topic` (+ `has_*` flags)

Keep required M6 fields (`errors`, `warnings`, `checks`, …) so old responses type-check.

### 2. Helper module (`marketingPreflight.ts`)

Pure functions (unit-testable):

| Function | Responsibility |
|----------|----------------|
| `normalizePreflightReport(input)` | Accept API response **or** `preflight_report_json`; unify blockers←`blockers\|\|errors`, checklist←`checklist\|\|checks` |
| `resolvePreflightSummaryTone(report)` | `failed` \| `warning` \| `passed` \| `empty` |
| `preflightSummaryTitle(tone)` / subtitle | RU banner copy |
| `preflightIssueLabel(code)` | RU map + unknown fallback |
| `preflightCheckLabel(code)` | RU for common check codes + fallback |
| `getBlockers(report)` / `getWarnings(report)` | accessors |

Unknown: `Неизвестная проверка: ${code}`.

### 3. Rewrite Preflight tab UI

`PackDetailPreflightTab.tsx`:

1. Initial report = normalize(`pack.preflight_report_json`) if non-empty.  
2. On mutation success → set live response.  
3. Render sections per UX plan (banner → blockers → warnings → checklist → topic summary → channels → media).  
4. Use existing `Alert` variants for severity.  
5. Do not change API client signature (`runMarketingPreflight` already returns typed body).

### 4. CSS

Minimal additions in `index.css`:

- `.marketing-preflight-banner--failed|warning|passed|empty`
- distinguish `.marketing-issue-list--blockers` vs `--warnings`
- compact rows for channel/media checks

No new design system / no card explosion — reuse panel patterns.

### 5. Tests

`marketingPreflight.test.ts` (tsx/assert style like other marketing helpers):

- label mapping for key blocker/warning codes;
- summary: blockers → failed; warnings only → warning; clean → passed; missing → empty;
- unknown code fallback;
- normalize M6 report (no version) still works;
- normalize v2 report prefers `blockers`/`checklist` when present.

### 6. Build

```bash
cd platform-console
npm run build
```

Backend pytest: **not required** unless a backend file accidentally changes (should not).

### 7. Package / PR (after approval)

- Commit only allow-listed FE + docs for C2.  
- Do **not** include dirty WIP.  
- Deploy is **not** this step — wait for C1+C2 joint deploy gate.

---

## Tests / checks

| Check | Command / criterion |
|-------|---------------------|
| Unit | `npx tsx src/pages/workspace/marketing/marketingPreflight.test.ts` (or project’s existing node:test style) |
| Build | `npm run build` in `platform-console` |
| Manual (post joint deploy) | rich pack `7ab244ef-0cd2-4da0-8f08-c8140aa39fbc` — run preflight, RU UI, approve with warnings, publish still disabled |

---

## Deploy note (post-C2 — separate HQ)

**Do not deploy C2 alone** unless C1 backend is deployed in the same window.

Recommended joint deploy:

1. Backend allow-list C1: `preflight_rules.py`, `approval.py`, `schemas.py`, `packs.py`  
2. Console dist with C2  
3. **No** Alembic  
4. Smoke pack above: readable blockers/warnings/checklist; approve w/ warnings; publish disabled  

---

## Risks

| Risk | Mitigation |
|------|------------|
| FE ahead of backend if mis-deployed | optional fields + M6 fallback |
| Mismatch of brief code names (`missing_*`) | map **actual** backend codes |
| Checklist noise (many check codes) | group/label top codes; fallback for rest |
| Session-only report today | hydrate from `preflight_report_json` |
| Scope creep into M7-B UI | touch overview only for microcopy if needed |

## Rollback

Revert console dist to previous M7-B build; backend C1 independently revertible via prior backups. No DB downgrade.

---

## Approval

**Status:** HQ approved — implementation done locally (2026-07-14)

### Implementation checklist

- [x] types: additive Preflight v2 + `preflight_report_json`
- [x] `marketingPreflight.ts` normalize + RU labels + summary tone
- [x] `marketingPreflight.test.ts`
- [x] `PackDetailPreflightTab.tsx` sections (banner / blockers / warnings / checklist / topic / channels / media)
- [x] CSS severity styling
- [x] Approval / completeness microcopy
- [x] FE tests + `npm run build` GREEN
- [ ] commit / PR (await separate HQ approval)
- [ ] joint C1+C2 deploy (later)

Next: package/PR when HQ asks, then joint C1+C2 deploy planning — not auto.
