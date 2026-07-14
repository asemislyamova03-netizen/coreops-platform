# Product / UX Plan — Marketing M7-C2 Preflight UI

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Category:** documentation_only → future `universal_module` (marketing frontend)  
**Status:** waiting for HQ approval on code  
**Risk:** low–medium (FE only; no migrate; must stay compatible with M6 report until C1+C2 deploy)

**Related:**
- M7-C1 merged: PR [#100](https://github.com/asemislyamova03-netizen/coreops-platform/pull/100) → `fcfa4a7` (`47e2731`) — **not deployed**
- Product Preflight v2: `docs/ai/plans/2026-07-14-marketing-m7-c-preflight-v2-plan.md`
- Implementation C2: `docs/ai/plans/2026-07-14-marketing-m7-c2-implementation-plan.md`
- Planning report: `docs/ai/reports/2026-07-14-marketing-m7-c2-planning-report.md`
- Parent M7: `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md`

**Decision (HQ):** Option **A** — implement M7-C2 first, then deploy **C1+C2 together** so users never see raw v2 codes in production.

---

## Goal

Сделать результаты Preflight v2 на вкладке Pack Detail → Preflight **читаемыми и полезными**:

- blockers отдельно от warnings;
- checklist;
- topic context summary;
- channel checks;
- media checks;
- понятный статус («можно утверждать» / «нужно исправить» / «есть предупреждения»);
- warnings не выглядят как blockers;
- publish остаётся выключенным.

---

## Current FE state (read-only)

| Item | Today |
|------|--------|
| Tab | `packDetail/PackDetailPreflightTab.tsx` |
| Report source | только `lastReport` из `POST …/preflight` в сессии; **не** читает `pack.preflight_report_json` |
| Display | English headings Errors/Warnings/Checks; **raw `issue.code`** + EN `message` from backend |
| Types | `MarketingPreflightResponse` = M6 shape (`errors`/`warnings`/`checks`); **нет** v2 fields |
| Pack detail type | **нет** `preflight_report_json` (backend C1 уже отдаёт поле) |
| Labels | `marketingLabels.ts` — статусы pack/preflight, **нет** map кодов issues |
| Soft completeness (M7-B) | на overview Pack Detail, display-only — **не** смешивать с preflight enforce |
| Approval | `canApprove = preflight_status === "passed"` — уже OK для warnings |
| CSS | minimal `.marketing-preflight-report` / `.marketing-issue-list` |

---

## Backend report contract (M7-C1, merged)

Live `POST /marketing/packs/{id}/preflight` (after C1 deploy) and stored `preflight_report_json`:

| Field | Role |
|-------|------|
| `version` | `"m7-c1"` |
| `passed` | `true` iff no blockers |
| `status` | `passed` \| `warning` \| `failed` |
| `errors` / `blockers` | same list (blockers alias) |
| `warnings` | non-blocking |
| `checks` / `checklist` | same list |
| `topic_context_summary` | dict or null |
| `channel_checks` | `[{channel, present, length, short_warn, below_blocker_threshold}]` |
| `media_checks` | `{count, missing}` |
| `channel_eligibility` | M6 |
| pack statuses | unchanged semantics |

Production until joint deploy still returns **M6** response (no `version` / `blockers` / summaries).

---

## UX principles

1. **Severity visual split:** blockers = error emphasis; warnings = muted/attention; never identical styling.  
2. **Prefer RU labels over EN backend messages** for known codes; keep optional detail (channel, length) from payload.  
3. **Warnings ≠ fail:** banner and copy must say approve is still allowed when only warnings.  
4. **Graceful degradation:** M6 reports, missing report, unknown codes.  
5. **No publish:** do not add publish CTAs; keep disabled messaging elsewhere.  
6. **Soft completeness (M7-B) stays separate** on overview; Preflight tab shows enforcement outcome.

---

## Recommended UI sections (Preflight tab)

Order top → bottom:

### 0. Sticky actions + statuses (existing, polish)

- Button «Запустить preflight»
- Human labels for `preflight_status` / pack status / approval (reuse `marketingLabels`)
- `preflight_at` if present

### 1. Summary banner

| Condition | Banner title | Tone |
|-----------|--------------|------|
| blockers / errors length > 0 **or** `status=failed` / `preflight_status=failed` | **Нужно исправить перед утверждением** | error |
| no blockers, warnings > 0 **or** `status=warning` | **Можно утверждать, но есть предупреждения** | warn / info |
| clean pass | **Проверка пройдена** | success |
| no report yet (`not_run` / empty) | **Preflight ещё не запускался** | muted |

Subline examples:
- fail: «Исправьте пункты ниже и запустите проверку снова.»
- warn: «Предупреждения не блокируют согласование.»
- pass: «Можно перейти на вкладку Согласование.»

User-facing short names from HQ brief map to banner:
- «Нужно исправить» / «Есть предупреждения» / «Можно утверждать» (clean + optional warn sub).

### 2. Blockers — `Что нужно исправить`

- List only blockers (`blockers` if present, else `errors`).
- Show RU title; optional muted code; channel if any.
- Empty → hide section (or short «Блокирующих замечаний нет»).

### 3. Warnings — `На что обратить внимание`

- Distinct style from blockers (no red “error” list identity).
- Explicit note: «Не блокируют утверждение.»
- Empty → hide.

### 4. Checklist — `Чеклист качества`

- Prefer `checklist`, fallback `checks`.
- Pass / warn / fail presentation:
  - `passed=true` → ок;
  - `passed=false` + code is also in blockers → fail;
  - `passed=false` otherwise → warn-style (many M7 checks use false for soft misses).
- RU labels for known check codes where practical; unknown → graceful.

### 5. Topic context summary — `Контекст темы (проверка)`

- Render when `topic_context_summary` present.
- Compact flags: audience / pain / insight / source_ref / cta / notes / planned_date (`has_*`).
- Do not duplicate full M7-B brief editing; link hint «смотрите блок на карточке пака» optional.

### 6. Channel checks — `Каналы`

- Table/list from `channel_checks` (social: telegram / instagram / threads).
- Columns: канал, есть текст, длина, статус (ок / короткий / пустой).
- If missing (M6): derive light view from `checks` with `*_text_present` / eligibility — optional v1.1; v1 may show «Нет детализации каналов (старый отчёт)» .

### 7. Media checks — `Медиа`

- From `media_checks`: count + missing flag.
- Align messaging with `media_missing` warning.
- M6 fallback: count from pack media or omit section.

---

## Message mapping (RU)

Primary map lives in new helper (see impl plan). Prefer **product RU** over English backend `message`.

### Blockers

| Code | RU |
|------|-----|
| `topic_missing` | У пака нет связанной темы |
| `topic_not_approved` | Тема ещё не утверждена |
| `no_publishable_text` | Нет текста ни в одном канале |
| `context_triple_missing` | Не заполнены аудитория, боль и CTA |
| `all_texts_too_short` | Тексты слишком короткие для проверки |
| `pack_metadata_incomplete` | Не заполнены название, slug или дата пака |
| `channel_text_missing` | Нет строки текста для канала |
| `media_invalid_mime` | Недопустимый тип медиа-файла |

### Warnings

| Code | RU |
|------|-----|
| `insight_missing` | Не заполнен инсайт |
| `source_ref_missing` | Нет источника или референса |
| `cta_missing_for_funnel` | Для этого этапа воронки лучше указать CTA |
| `media_missing` | Нет медиа-плана или медиа-метаданных |
| `channel_text_short` | Текст канала слишком короткий |
| `notes_missing` | Не заполнены заметки темы |
| `topic_planned_date_missing` | У темы не указана плановая дата |
| `telegram_text_too_long` | Текст Telegram длиннее лимита |
| `insights_text_empty` | Insights пустой (допустимо) |
| `media_not_1080` | Медиа не 1080×1080 |

**Note:** backend codes use `cta_missing_for_funnel` / `insight_missing` / `source_ref_missing` / `notes_missing` / `topic_planned_date_missing` — **not** `missing_*` prefixes from earlier briefs. Map the real codes.

### Unknown / fallback

`Неизвестная проверка: <code>` (+ show backend `message` if present).

### Channel / check helpers

Reuse `marketingChannelLabel` for channel names.

---

## Compatibility

| Scenario | Behavior |
|----------|----------|
| M7-C1 v2 report | Full sections |
| Old M6 report (prod until deploy) | Banner from errors/warnings/status; list Errors→blockers, Warnings; Checks; hide or soft-hide v2-only panels |
| Empty / missing report | Banner «ещё не запускался»; no fake blockers |
| Unknown code | fallback label |
| Optional fields missing | treat as M6 |

**Hydration:** on load, if `pack.preflight_report_json` non-empty, show as last report (normalize dict → UI model). After run, use live response.

---

## Approval / publish UX (non-goals for C2 depth)

- Approval tab: keep gate on `preflight_status === "passed"`; optional one-line note that warnings OK (tiny copy only if cheap).
- Publish tab: no enablement.

---

## Out of scope

- Backend rule changes  
- Migration / env / deploy in this gate  
- Publish / export / Margosya  
- AI scoring / auto-generation / analytics / CRM  
- Binary upload / smoke cleanup  
- Redesign of whole Pack Detail beyond Preflight tab (+ minimal CSS)

---

## Success criteria

1. Асем видит RU blockers/warnings, not raw English-first presentation.  
2. Warnings visually ≠ blockers; copy says approve allowed.  
3. Checklist + channel/media sections useful on rich smoke pack.  
4. M6 report still readable if FE ever loaded against older API.  
5. Joint deploy C1+C2 recommended; FE alone against M6 still safe.
