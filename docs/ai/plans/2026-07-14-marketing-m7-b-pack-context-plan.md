# Product / UX Plan — Marketing M7-B Pack context

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Category:** documentation_only → future `universal_module` (marketing)  
**Status:** waiting for HQ approval on code  
**Depends on:** M7-A live in production (`0c1dbe6`)

---

## 1. Problem

Pack detail already has tabs for texts / media / preflight / approval / publish / logs, but the writing surface lacks strategic topic context.

Today the only topic signal on pack detail is:

> Тема → `pack.topic?.title`

Асем cannot answer while writing:

- what this content is about strategically;
- which rubric / angle;
- who / pain / insight / source / CTA / funnel / notes.

That context already lives on the topic after M7-A. Pack detail simply does not surface it.

---

## 2. Product rule

- Marketing Cabinet remains the **source of truth** for content preparation.
- Margosya is **not** SoT.
- Publish / export / Margosya stay disabled and out of scope for M7-B.

---

## 3. Goal

Make pack detail usable for real content work by showing the source topic’s editorial context and a short writing brief.

M7-B answers on one screen:

| Question | Field |
|----------|--------|
| What is this about? | title + angle + rubric |
| Who is it for? | audience |
| What pain? | pain |
| What insight? | insight |
| What source? | source_ref |
| What should the reader do? | CTA |
| Funnel position? | funnel_stage |
| Priority / when? | priority, planned_date |
| Writing notes? | notes |

---

## 4. Target UX blocks

### 4.1 Topic context block (primary)

Place **above** tabs (near existing pack meta), Russian labels.

| Field | Label (RU) |
|-------|------------|
| title | Тема |
| rubric | Рубрика |
| angle | Угол / angle |
| audience | Аудитория |
| pain | Боль / проблема |
| insight | Инсайт |
| source_ref | Источник / опора |
| cta | CTA |
| funnel_stage | Этап воронки |
| priority | Приоритет |
| planned_date | План. дата темы |
| notes | Заметки |

**Empty state:** missing field → «—» or muted «не заполнено».  
**Link:** «Открыть тему» / «Заполнить тему» → Topics page / edit that topic (`topic_id`). Simple navigation only — no inline topic editor in M7-B.

Collapsible if long (default open).

### 4.2 Writing brief block (display-only)

Derived, no AI:

| Brief line | Source |
|------------|--------|
| Кому пишем | audience |
| Какая боль | pain |
| Главная мысль | insight (+ angle if useful) |
| На что опираемся | source_ref |
| Что должен сделать читатель | cta |
| Тон / угол подачи | angle + rubric (+ funnel label) |

If a source field is empty, that brief line shows empty/muted — do not invent copy.

### 4.3 Completeness indicators (soft)

Checklist / chips (display only; **not** preflight enforcement — that is M7-C):

- audience filled  
- pain filled  
- insight **or** source_ref filled  
- CTA filled  
- at least one channel text non-empty  
- media present (optional for pass — show warning-style chip)

Overall: «Контекст темы: полный / частичный / слабый».

### 4.4 Preserve existing UX

- Pack status meta (status / preflight / approval / publish / planned_date pack) stays.  
- All current tabs stay.  
- Publish tab remains disabled honesty.  
- No AI generation.  
- No topic edit modal on pack page.

---

## 5. User flow (Асем)

1. Open approved/taken pack.  
2. Read Topic context + Writing brief.  
3. If thin → «Заполнить тему» → Topics edit (M7-A form) → return to pack.  
4. Write channel texts with brief visible.  
5. Continue preflight/approval as today.  
6. Publish still later gate.

---

## 6. Out of scope (product)

- Editing topic fields inside pack detail (except link)  
- Preflight v2 enforcement (M7-C)  
- AI generation  
- Publish / export / Margosya  
- Binary upload, analytics, CRM attribution  
- Migrations  

---

## 7. Success criteria

- Pack detail shows full M7-A editorial context when topic has it.  
- Empty metadata does not break the page.  
- Writer can jump to topic edit.  
- Soft completeness visible without blocking workflow.  
- No publish surface change.
