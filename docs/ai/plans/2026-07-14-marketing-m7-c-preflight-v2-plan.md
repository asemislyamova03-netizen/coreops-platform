# Product Plan — Marketing M7-C Preflight v2

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Category:** documentation_only → future `universal_module` (marketing)  
**Status:** waiting for HQ approval on code  
**Production baseline:** M6 + M7-A + M7-B live; publish/Margosya disabled; alembic **0015**

**Related:**
- Parent M7: `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md`
- Implementation: `docs/ai/plans/2026-07-14-marketing-m7-c-implementation-plan.md`
- Planning report: `docs/ai/reports/2026-07-14-marketing-m7-c-planning-report.md`

---

## Goal

Сделать preflight полезным для качества контента: не только «есть ли текст», но и достаточно ли стратегического контекста, чтобы утверждать pack ответственно — **без** включения publish/export/Margosya.

---

## Product principle (strictness)

**Warning-heavy, blocker-light.**

| Rule class | Effect |
|------------|--------|
| **Blocker (error)** | `preflight` → `failed` / pack `preflight_failed`; approve **blocked** |
| **Warning** | `preflight` overall `warning` but `preflight_status=passed` + pack `ready_for_approval`; approve **allowed** |
| Soft completeness (M7-B) | stays display-only on Pack Detail; **not** the same as preflight enforce |

Асем должна уметь утверждать pack с warnings, если blockers пустые.

---

## Current M6 behavior (keep unless upgraded below)

Already in `approval.py`:

**Existing blockers:**
- pack metadata incomplete (title / slug / planned_date pack);
- missing text row for a default channel;
- no non-empty channel text at all;
- linked topic not approved;
- invalid media mime.

**Existing warnings:**
- telegram > 4096 chars;
- empty insights text (allowed);
- no linked topic (**today warning — M7-C upgrades to blocker**);
- media not 1080×1080.

**Approval gate (unchanged):**
- requires `preflight_status == passed` (warnings do not fail this);
- pack status must be `ready_for_approval`.

**Storage (unchanged):**
- report in `preflight_report_json` (JSON) — **no migration**.

---

## M7-C rule set (recommended)

### A. Blockers (new + upgraded)

| Code | Rule | Why |
|------|------|-----|
| `topic_missing` | Pack has **no** `topic_id` | Without topic there is no strategic context (upgrade from soft warning) |
| `no_publishable_text` | Keep M6: all target channels empty | Must have something to approve |
| `channel_text_missing` / pack metadata / topic_not_approved / media_invalid_mime | Keep M6 | Stability |
| `context_triple_missing` | Topic linked but **audience AND pain AND CTA** all empty | Too empty to approve responsibly; any one filled → not this blocker |
| `all_texts_too_short` | Every **non-empty** social channel text length &lt; **20** chars (telegram / instagram / threads; insights excluded) | Blocks only obvious stubs |

**Not blockers in M7-C:**
- missing insight alone;
- missing source_ref alone;
- missing media alone;
- missing notes / topic planned_date;
- short text on **some** channels only;
- “generic” phrasing alone.

### B. Warnings (new + kept)

| Code | Rule |
|------|------|
| `insight_missing` | Topic linked, insight empty |
| `source_ref_missing` | Topic linked, `source_ref` empty *(v1: always warn; “почему нет источника” via filled `notes` is optional soft suppress later — not required for first ship)* |
| `cta_missing_for_funnel` | `funnel_stage` in `{diagnosis, consultation, product_education, objection_handling}` and CTA empty |
| `media_missing` | No non-archived media metadata rows |
| `channel_text_short` | Per social channel: text present but length &lt; **40** chars |
| `notes_missing` | Topic notes empty |
| `topic_planned_date_missing` | Topic editorial `planned_date` empty (pack `planned_date` still M6 blocker) |
| Keep M6 | telegram too long; insights empty; media not 1080×1080 |

### C. Optional soft warning (v1.1 / same gate if cheap)

| Code | Rule |
|------|------|
| `text_looks_placeholder` | Non-empty text matches obvious stubs (`lorem`, `test`, `asdf`, `xxx`, `TODO`) — **warning only**, never blocker |

Skip AI quality scoring.

---

## Pass / fail outcomes

```text
if any blocker (errors):
  status = failed
  preflight_status = failed
  pack.status = preflight_failed
else:
  status = warning if warnings else passed
  preflight_status = passed
  pack.status = ready_for_approval
```

Approve remains: **passed preflight required; warnings OK.**

---

## Report shape (product view)

Preflight report v2 (still stored in `preflight_report_json`) should be readable as:

1. **Verdict:** Можно утверждать / Нужно исправить  
2. **Blockers** (red)  
3. **Warnings** (amber)  
4. **Checklist** with RU labels  
5. **Topic context summary** (audience / pain / insight / source_ref / cta / funnel)  
6. **Channel checks** (present / short / empty)  
7. **Media checks** (count / mime issues)

---

## Operator UX (Pack Detail → Preflight tab)

| Element | Behavior |
|---------|----------|
| Headline | «Можно утверждать» if no blockers; «Нужно исправить» if blockers |
| Subline | «Есть предупреждения — утверждение всё ещё возможно» when warning+passed |
| Blockers list | RU messages + codes; link to Texts / Topic (list) / Media |
| Warnings list | RU messages; same links |
| Checklist | ✓/✗ human labels (not raw code-only) |
| Approve tab | unchanged gate (`preflight_status=passed`); optional note that warnings exist |
| Publish | remains disabled / honesty unchanged |

Links:
- Texts → Texts tab  
- Media → Media tab  
- Topic context → Topics list (deep edit not available yet — same M7-B limit)

---

## Smoke intent (after implement)

Use rich pack `7ab244ef-0cd2-4da0-8f08-c8140aa39fbc` (topic `a25333a3-…`).

Expect after texts present:
- likely **passed** or **warning** (not failed) if Channel texts filled enough;
- approval still possible;
- publish still disabled;
- avoid new rows if possible.

---

## Out of scope

- publish / export / Margosya  
- AI generation / AI scoring  
- binary upload  
- analytics / CRM attribution  
- migrations  
- smoke cleanup  
- hard enforcement of M7-B soft completeness chrome  
- automatic rewrite of channel text  

---

## Success criteria (product)

1. Empty/air packs fail with clear blockers.  
2. Strategic gaps (insight/source/CTA/media) surface as warnings without locking Асем.  
3. Approval workflow identical in spirit to M6: preflight passed required; warnings do not block.  
4. Publish remains off.  
5. No DB migration.
