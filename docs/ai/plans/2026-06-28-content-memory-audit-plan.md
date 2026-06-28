# Flexity Content Memory Audit Plan

## Classification

- Project: Flexity
- Category: documentation_only / content_operations
- Risk: low
- Status: planning only — no implementation approved

## 1. Purpose

**Flexity Content Memory Audit** — будущий **read-only preflight audit**, который запускается **перед** подготовкой ежедневного content-pack и помогает не повторять темы, CTA, tone и рубрики.

Аудит читает repo-based историю контента, сравнивает её с monthly plan и выдаёт **Daily Preflight Report** для human reviewer и Content Strategist / Content Pack Agent. Никаких записей в репозиторий, публикаций или workflow triggers.

## 2. Why it is needed

Flexity публикует контент ежедневно. Без памяти о прошлых постах легко скатиться в одни и те же углы:

| Overused pattern | Why it hurts |
|------------------|--------------|
| **AI + processes** | Каждый второй пост звучит одинаково |
| **AI will not save chaos** | Повтор одного тезиса без нового примера |
| **First processes, then AI** | Устаревший hook при частом использовании |
| **«Напишите РАЗБОР» CTA** | Агрессивный или однообразный призыв |
| Repeated sales tone | Подрывает calm founder voice |
| Same Instagram carousel format 3× подряд | Audience fatigue |

Content Memory Audit дополняет [Content Strategist Agent plan](2026-06-27-content-strategist-agent-plan.md): strategist рекомендует *что* писать; memory audit проверяет *что уже было* и что **избегать сегодня**.

## 3. Source folders to scan

Read-only paths (repo only):

| Path | What to read |
|------|----------------|
| `landing/content/content-packs/**` | `pack.yml`, channel markdown/yml, `publish_log.yml`, optional `visual.yml`, `distribution.yml` |
| `landing/content/articles/**` | Insights source + frontmatter |
| `landing/www/insights/**` | Live generated HTML (public truth) |
| `landing/www/assets/social/**` | Deployed assets by slug |
| `docs/content/**` | Contracts, templates, monthly plan |
| `docs/ai/plans/**` | Strategist plan, channel roadmaps, runbooks |

**Do not read:** backend, `.env`, GitHub Secrets, publisher runtime outside repo, `/mnt/data` paths.

## 4. Data to extract

Per content item (pack and/or article), normalize into a **memory record**:

| Field | Source hints |
|-------|----------------|
| `slug` | folder name `YYYY-MM-DD-slug` |
| `date` | `pack.yml` date or article frontmatter |
| `title` | article `title`, pack `topic`, or derived headline |
| `rubric` | mapped direction from monthly plan (e.g. `practical_business_scenario`) |
| `topic` | `pack.yml` topic or article subject |
| `angle` | derived one-line hook (e.g. «cash gap vs CRM request») |
| `channels` | telegram, instagram, insights, facebook_planned, threads_planned, tiktok_planned |
| `status` | draft / approved / published / failed / skipped |
| `cta` | extracted CTA text or type |
| `keywords` | tokenized theme keywords for repetition detection |
| `publish metadata` | `published_at`, `external_id` per channel |
| `publish_log errors` | failed events, missing external_id |
| `instagram_published` | bool from `publish_log.yml` or `instagram.yml` |
| `telegram_published` | bool from `publish_log.yml` or `pack.yml` |
| `insights_published` | article `status` + HTML exists under `landing/www/insights/` |
| `facebook_threads_tiktok` | `planned_manual` unless future workflow exists |

## 5. Analysis windows

Rolling windows from audit run date (inclusive):

| Window | Use |
|--------|-----|
| **Last 7 days** | Primary guard — daily repetition, CTA fatigue |
| **Last 14 days** | Rubric balance, angle diversity |
| **Last 30 days** | Monthly alignment, claim repetition, channel gaps |

Each window produces counts, top keywords, and warning flags.

## 6. Repetition checks

Fail-soft warnings (human decides); multiple signals increase severity.

| Check | Rule of thumb |
|-------|----------------|
| **Repeated topic** | Same `topic` or ≥70% keyword overlap with post in last 7 days |
| **Repeated angle** | Same `angle` stem in last 3 posts |
| **Repeated CTA** | Same CTA phrase or `cta_type` 3× / 7 days |
| **Repeated rubric** | Same rubric 3 consecutive days |
| **Repeated claim** | Same product/roadmap claim without new evidence 2× / 14 days |
| **Repeated «AI + process» framing** | Primary keyword cluster `{AI, процесс, хаос, сначала процесс}` 3× / 7 days |
| **Repeated sales tone** | Hard sell markers 2× / 7 days |
| **Repeated format** | Same asset pattern (e.g. 9-slide carousel + same title structure) 2× in a row |
| **Repeated channel gap** | Telegram published but Instagram missing 2× without repair note |

Output: `repetition_warnings[]` with `severity`, `evidence_slugs[]`, `suggestion`.

## 7. Monthly plan alignment

Compare recent + planned content against:

[docs/content/2026-06-flexity-monthly-content-plan.md](../../content/2026-06-flexity-monthly-content-plan.md)

Checks:

- Is today's calendar slot filled or still draft?
- Which weekly topics from the 4-week calendar are **done** vs **missing**?
- Which approved directions are **underrepresented** in last 7 days?
- Does recommended today topic match the calendar, or is strategist overriding with justification?

Output section: `monthly_plan_alignment` with `scheduled_topic`, `status`, `gap_notes`.

## 8. Output format: Daily preflight report

Markdown or YAML report emitted to stdout / artifact only (no repo write).

```markdown
# Flexity Content Memory Audit — YYYY-MM-DD

## Recent content summary (7 / 14 / 30 days)
- counts by rubric
- channels published vs planned

## Repeated topics detected
- ...

## CTA repetition warning
- ...

## Rubrics overused
- ...

## Rubrics missing (vs monthly plan)
- ...

## Channels missing
- e.g. insights not published for last 2 depth posts

## Recommended theme for today
- from monthly plan + gap analysis

## Themes to avoid today
- ...

## Suggested CTA type
- no_cta | engagement_question | soft_demo_process_review | article_link | build_in_public_note

## /insights needed?
- yes / no / optional — with reason

## Format recommendation
- Instagram/Facebook/Threads: short hook + visual
- Telegram: long narrative
- TikTok: script idea only (planned channel)
```

## 9. Safety boundaries

- **Read-only only** — no file writes, no git commits
- **No auto-edit** of packs, articles, or assets
- **No auto-publish** — no Telegram, Instagram, insights, Meta, TikTok
- **No workflow runs** — do not trigger GitHub Actions
- **No API calls** to external platforms
- **No token access** — no Meta, Telegram bot, or secrets
- **No secrets** read or stored
- **No changing content-packs** — audit output is advisory

Human approves all content before draft → approved → publish.

## 10. Future implementation phases

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 1** | This documentation-only plan | current |
| **Phase 2** | Local read-only script — scan repo, print report | requires approval |
| **Phase 3** | Manual GitHub Actions job — report artifact on `workflow_dispatch` only | requires approval |
| **Phase 4** | Integration into daily content brief (input to Strategist / Pack Agent) | requires approval |
| **Phase 5** | Content Strategist Agent command / Cursor skill | requires approval |
| **Phase 6** | Mobile approval flow — view report + trigger existing safe workflows | requires approval |

## 11. Example report

```markdown
# Flexity Content Memory Audit — 2026-06-30

## Recent content summary
- **Last 7 days:** 2 build in public, 1 lifestyle, 1 weekly news, 2 practical business scenarios, 1 founder story
- **Last 14 days:** AI+process keyword cluster appeared 4 times — over threshold
- **Channels:** Telegram 6/7, Instagram 4/7, /insights 1/7

## Repeated topics detected
- «Сначала процесс, потом AI» — slugs: 2026-06-22-ai-tools-need-process, 2026-06-25-process-before-ai (similar framing)

## CTA repetition warning
- «Напишите РАЗБОР» — 2 times in last 7 days. Suggest softer CTA today.

## Rubrics overused
- product_progress (3× in 7 days)

## Rubrics missing
- audience / poll (none in last 14 days; monthly plan expects Sunday poll soon)

## Channels missing
- /insights not published for 2026-06-28 pack (Telegram + Instagram only)

## Recommended theme for today
- **Practical business scenario:** client asks for CRM, but real issue may be cash gap (Week 1 Monday per monthly plan)

## Themes to avoid today
- AI + process framing
- «AI не спасёт хаос» angle
- Hard «РАЗБОР» CTA

## Suggested CTA type
- `engagement_question` — «Где у вас сейчас разрыв: учёт, договор или оплата?»

## /insights needed?
- **Recommended yes** — scenario has enough depth for article; link from Telegram

## Format recommendation
- **Telegram:** long scenario narrative (800–1200 words)
- **Instagram:** 5–7 slide carousel — one scenario, one diagram hook
- **Facebook / Threads:** short cross-post + link (planned manual)
- **TikTok:** optional 45s script — «клиент просит CRM, а проблема в кассе» (planned only)
```

## Related documentation

- [Content Strategist Agent plan](2026-06-27-content-strategist-agent-plan.md)
- [Monthly content plan](../../content/2026-06-flexity-monthly-content-plan.md)
- [Content Factory](../../content/content-factory.md)

## Approval status

This document is **documentation only**. It does not approve scripts, workflows, API integration, or automated publishing.

## Checks

```bash
git diff --check
git status --short
```
