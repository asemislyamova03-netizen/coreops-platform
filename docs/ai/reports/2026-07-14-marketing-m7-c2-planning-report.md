# Planning Report — Marketing M7-C2 Preflight UI

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Status:** PLANNING COMPLETE — code not started  
**Category:** documentation_only  
**HQ decision:** Option **A** — C2 FE first, then **joint C1+C2 deploy**

---

## Context verified

| Item | Value |
|------|--------|
| M7-C1 PR | [#100](https://github.com/asemislyamova03-netizen/coreops-platform/pull/100) **MERGED** |
| Merge commit | `fcfa4a7` |
| Head | `47e2731` — `marketing: add preflight v2 backend rules` |
| Production | still M7-B; C1 **not** deployed |
| Migration | none for C1/C2 |
| Publish/Margosya | remain disabled |

Docs created (uncommitted):

1. `docs/ai/plans/2026-07-14-marketing-m7-c2-preflight-ui-plan.md`  
2. `docs/ai/plans/2026-07-14-marketing-m7-c2-implementation-plan.md`  
3. this report

---

## Current state review (read-only)

### Frontend

- Preflight tab shows raw codes under English «Errors / Warnings / Checks».
- Report only in React state after button click — ignores stored report.
- Types = M6 `MarketingPreflightResponse`; pack detail type lacks `preflight_report_json`.
- No `marketingPreflight.ts` yet (labels only in `marketingLabels.ts` for statuses).
- Approval already allows warnings (`preflight_status === "passed"`).

### Backend (merged C1, not prod)

- Additive v2 on `PreflightResponse` + JSON store.
- `blockers` ≡ `errors`; `checklist` ≡ `checks`.
- Rich: `topic_context_summary`, `channel_checks`, `media_checks`.
- Real warning codes: `insight_missing`, `source_ref_missing`, `cta_missing_for_funnel`, `notes_missing`, `topic_planned_date_missing` (not `missing_*` aliases).

---

## Answers to required questions

### Is backend change needed for C2?

**No.** Consume C1 fields. Any rule tweak = separate CR.

### Is migration needed?

**No.**

### Which frontend files will change?

```text
platform-console/src/types/marketing.ts
platform-console/src/pages/workspace/marketing/marketingPreflight.ts          # NEW
platform-console/src/pages/workspace/marketing/marketingPreflight.test.ts     # NEW
platform-console/src/pages/workspace/marketing/packDetail/PackDetailPreflightTab.tsx
platform-console/src/index.css
```

Optional microcopy: Approval tab / Pack Detail note near soft-completeness.

### What labels/messages should be used?

RU map in product plan — key ones:

| Code | RU |
|------|-----|
| `topic_missing` | У пака нет связанной темы |
| `topic_not_approved` | Тема ещё не утверждена |
| `context_triple_missing` | Не заполнены аудитория, боль и CTA |
| `all_texts_too_short` | Тексты слишком короткие для проверки |
| `insight_missing` | Не заполнен инсайт |
| `source_ref_missing` | Нет источника или референса |
| `cta_missing_for_funnel` | Для этого этапа воронки лучше указать CTA |
| `media_missing` | Нет медиа-плана или медиа-метаданных |

Unknown → `Неизвестная проверка: <code>`.

### How to handle old reports?

Normalize helper: fallback `errors`/`checks`; hide v2 panels if absent; optional fields in TS.

### Tests required?

Yes — `marketingPreflight.test.ts` (labels, summary tones, M6/v2 normalize, unknown, empty).  
`npm run build`. No backend pytest for C2.

### Should C1+C2 deploy together?

**Yes (recommended).** Avoid production FE showing raw C1 English messages, and avoid C2-only against M6 backend losing value (safe but incomplete).

### Smoke pack?

`7ab244ef-0cd2-4da0-8f08-c8140aa39fbc` (topic `a25333a3-ad1b-4539-956f-40298cfa5499`) after joint deploy.

### Risks / blockers

| Item | Level |
|------|-------|
| Planning blockers | **none** |
| Code/deploy name mismatch | use real C1 codes |
| Accidental solo FE deploy | document joint deploy |
| Checklist verbosity | label + graceful unknown |

---

## Recommended UI sections

1. Summary banner (исправить / предупреждения / пройдено / не запускался)  
2. Что нужно исправить (blockers)  
3. На что обратить внимание (warnings)  
4. Чеклист качества  
5. Контекст темы (проверка)  
6. Каналы  
7. Медиа  

---

## Label / message strategy

Central RU maps in `marketingPreflight.ts`; prefer map over EN backend message; append channel/length when useful.

---

## Compatibility plan

Support M6 + M7-C1; hydrate `preflight_report_json`; unknown codes safe; empty report safe.

---

## Tests plan

Unit helper tests + console build; post-deploy smoke listed above.

---

## Deploy recommendation

**Joint C1 backend + C2 console** after C2 merge. No migration. No auto-deploy on merge.

---

## What was not touched

- production code  
- commits / push  
- deploy / migrations / env / DB  
- publish / Margosya / M7-C1 rules  

---

## Next recommended step

HQ **approve M7-C2 implementation plan** → implement FE helpers + Preflight tab → tests/build → package/PR → then joint C1+C2 deploy planning.
