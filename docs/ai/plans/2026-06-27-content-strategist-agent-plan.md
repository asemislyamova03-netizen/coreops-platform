# Flexity Content Strategist Agent Plan

## Classification

- Project: Flexity
- Category: documentation_only / content operations planning
- Risk: low
- Status: planning only — no implementation approved

## 1. Purpose

**Flexity Content Strategist Agent** — будущий read-only AI-агент, который анализирует историю контента в репозитории и работает как marketing/content strategist: помогает планировать сбалансированный контент, не публикует и не меняет файлы автоматически.

Агент читает уже существующие content-packs, статьи, assets, publish logs и planning docs, затем выдаёт:

- weekly content plan;
- daily topic recommendation;
- daily content brief для отдельного **Content Pack Agent**;
- warnings по повторениям, tone drift и недостоверным claims.

Publishing остаётся human-approved.

## 2. Why this agent is needed

Текущий процесс Flexity Content Factory:

```text
idea → draft → content-pack → visual asset → /insights article → Telegram → Instagram → publish metadata
```

Проблема: при ежедневной публикации контент быстро становится однотипным — одни и те же углы (AI, процесс, founder story), перегруз одного channel или повтор одной темы 3–4 дня подряд.

Strategist Agent закрывает planning-слой, которого сейчас нет:

- видит **всю** repo-based историю, а не только последний draft;
- считает баланс тем за 7 / 14 / 30 дней;
- отслеживает channel coverage и publish failures;
- предлагает следующую тему с учётом пробелов;
- готовит brief, но не пишет финальный publish-ready pack без отдельного агента и human review.

## 3. Source folders it reads

Read-only источники (repo only, no `/mnt/data`, no secrets):

| Path | Purpose |
|------|---------|
| `landing/content/content-packs/**` | Daily packs: `pack.yml`, `telegram.md`, `instagram.yml`, `instagram.md`, `publish_log.yml`, optional `visual.yml`, `distribution.yml` |
| `landing/content/articles/**` | Insights source markdown + frontmatter |
| `landing/www/insights/**` | Generated public HTML (what is live on site) |
| `landing/www/assets/social/**` | Deployed/generated social assets by slug |
| `docs/content/**` | Channel contracts, templates, tone rules |
| `docs/ai/plans/**` | Approved plans, runbooks, channel roadmap (e.g. TikTok planned) |

Агент **не читает**: backend, `.env`, GitHub Secrets, publisher runtime logs вне repo, production DB.

## 4. Metadata it should extract

### Per content-pack (`landing/content/content-packs/YYYY-MM-DD-slug/`)

From `pack.yml`:

- `date`, `topic`, `slug`, top-level `status`
- `publish.telegram.*` — enabled, status, publish_at, published_at, external_id
- optional `publish.instagram.*` if present in pack-level metadata

From channel files:

- `instagram.yml` — type, status, publish_at, published_at, external_id
- `telegram.md`, `instagram.md` — caption/body length, CTA hints (read-only analysis)

From `publish_log.yml`:

- `events[]` — channel, status (`published`, `failed`, `skipped`), timestamp, external_id, error message if logged

From `visual.yml` (if present):

- asset generation intent, output paths

From `distribution.yml` (if present):

- cross-channel intent

### Per insights article (`landing/content/articles/*.md`)

Frontmatter:

- `title`, `date`, `category`, `slug`, `status`, `description`, `source`, `cta`, `image`

Body (analysis only):

- theme tags, claims about product readiness, founder vs news vs scenario tone

### Derived fields (computed by agent)

- `content_theme` — one of weekly balance categories (see §5)
- `channels_published[]` — telegram, instagram, insights, planned tiktok
- `channels_missing[]` — approved but not published
- `days_since_similar_topic`
- `tone_flags[]` — hype, aggressive sell, unfinished feature claimed as ready
- `cta_type` — see §9

## 5. Weekly content balance model

Target mix for a **7-day rolling window** (guideline, not hard quota):

| Theme | Target share | Description |
|-------|--------------|-------------|
| `news_digest` | 1–2 / week | AI/industry/news digest, calm professional |
| `founder_story` | 1–2 / week | Personal founder-led narrative |
| `build_in_public` | 1 / week | What we built, learned, shipped in repo |
| `product_progress` | 1 / week | Flexity capability progress — honest, not hype |
| `practical_business_scenario` | 1–2 / week | CRM/process/automation scenario for service business |
| `lifestyle_systems_thinking` | 0–1 / week | Time, systems, life + work balance |
| `weekly_recap` | 0–1 / week | End-of-week summary across channels |
| `soft_cta_engagement` | 1 / week | Question, soft demo invite, article link — not hard sell |

Rules:

- No more than **2 consecutive days** with the same `content_theme`.
- No more than **3 posts / 14 days** with the same primary keyword cluster (e.g. «AI + хаос + процесс»).
- At least **1** `practical_business_scenario` or `product_progress` per week to anchor Flexity ERP value.
- `founder_story` and `lifestyle_systems_thinking` combined ≤ 40% of weekly posts.

Channel balance (7-day):

- Telegram: target daily or near-daily when packs exist
- Instagram: ≥ 3/week when visual assets available
- `/insights`: ≥ 1/week for depth pieces tied to packs or standalone
- TikTok/Reels: planning only until channel operational

## 6. Daily recommendation logic

Daily run (recommended morning, read-only):

1. **Ingest** all packs/articles with `date` in last 30 days + any `draft`/`approved` future packs.
2. **Classify** each item into `content_theme` and channels.
3. **Score gaps** vs weekly balance model for last 7 days.
4. **Penalize repetition** — topics/angles used in last 3 days get lower priority.
5. **Check publish_log** — if yesterday Telegram published but Instagram failed, recommend follow-up or repair, not a brand-new unrelated topic.
6. **Pick primary theme** for today from highest-gap category that passes repetition guard.
7. **Pick angle** — specific hook unlike last 2 posts in same theme.
8. **Assign channels** — minimum viable set (e.g. Telegram + Instagram feed; insights if depth ≥ 800 words planned).
9. **Suggest CTA type** — see §9.
10. **Emit daily brief** for Content Pack Agent (§9) — no file writes.

If human already created today's draft pack, agent compares brief vs draft and flags drift or improvement suggestions only.

## 7. Repetition detection

Signals (any 2+ trigger a warning):

- Same `slug` stem or `topic` field similarity ≥ 0.7 (normalized text)
- Same primary keyword set in 3 posts / 7 days
- Same narrative arc (problem → AI → process → Flexity) repeated without new evidence or example
- Same Instagram visual template + title pattern 2× in a row
- Same `/insights` category 3× / 14 days without variety

Output:

- `repetition_warning` with referenced slugs and dates
- `suggested_differentiation` — what angle to change (audience, example, channel, format)

## 8. Tone and claims safety

Flexity tone (must match [Content Factory](../../content/content-factory.md) and insights rules):

- calm, practical, founder-led
- not hype, not guru, not aggressive selling
- honest about roadmap — use «развиваем», «закладываем», «можно настроить», not «уже работает у всех»

Claims safety checks:

- Compare post text against known **non-ready** capabilities (from `docs/ai/plans/**`, CHANGE_REQUESTS, channel docs):
  - TikTok live publishing
  - public inbound leads live intake (when disabled)
  - tenant customization layer
  - unfinished kindergarten/commercial modules marketed as GA
- Flag phrases: «полностью автоматически», «из коробки для всех», «уже в production у клиентов» without source pack evidence
- Flag missing disclaimers when describing future channels (TikTok, CRM lead loop)

Output: `claims_warning[]` with severity `info` | `review_required` | `block_suggestion`.

Agent **suggests** edits; human decides before approval.

## 9. Output formats

### A. Weekly content plan (markdown report)

```markdown
# Flexity Weekly Content Plan — YYYY-MM-DD

## Last 7 days summary
- themes used: ...
- channel coverage: ...
- repetition warnings: ...
- publish failures: ...

## Recommended 7-day schedule
| Day | Theme | Topic hook | Channels | CTA type |
|-----|-------|------------|----------|----------|

## Gaps to fill
- ...

## Do not repeat
- ...
```

### B. Daily content brief (for Content Pack Agent)

```yaml
brief_date: "YYYY-MM-DD"
recommended_slug: "YYYY-MM-DD-topic-slug"
content_theme: "practical_business_scenario"
topic_hook: "..."
audience: "service business owner / founder"
channels:
  telegram: required
  instagram: required
  insights: optional
  tiktok: planned_only
tone:
  - calm
  - practical
  - founder_led
avoid:
  - hype
  - fake_ready_features
key_points:
  - "..."
claims_to_verify:
  - "..."
cta_type: "soft_demo_process_review"
reference_slugs:
  - "2026-06-22-ai-tools-need-process"
repetition_warnings: []
publish_log_notes: []
```

### C. CTA type vocabulary

| `cta_type` | When to use |
|------------|-------------|
| `no_cta` | Pure value / story; no ask |
| `engagement_question` | Ask one honest question |
| `soft_demo_process_review` | Invite to process review / demo page — no pressure |
| `article_link` | Point to `/insights/{slug}` |
| `build_in_public_note` | «Мы сейчас строим X в Flexity, вот что уже есть» |

## 10. Example weekly plan

```markdown
# Flexity Weekly Content Plan — 2026-06-30

## Last 7 days summary
- themes: founder_story×2, news_digest×1, product_progress×1, practical_business_scenario×1
- channels: Telegram 5/7, Instagram 3/7, insights 1/7
- repetition: «AI + процесс» angle 3× — warning
- publish_log: instagram failed once on 2026-06-28 pack — repair before new carousel

## Recommended 7-day schedule
| Day | Theme | Topic hook | Channels | CTA |
|-----|-------|------------|----------|-----|
| Mon | news_digest | 3 AI signals for service SMB this week | TG, IG | article_link |
| Tue | practical_business_scenario | Lead → contract without Excel chaos | TG, IG, insights | soft_demo |
| Wed | build_in_public | What we shipped in Content Factory this week | TG | build_in_public_note |
| Thu | founder_story | Morning planning with AI — what changed | TG, IG carousel | engagement_question |
| Fri | product_progress | Public demo form deployed, intake still disabled — honest update | TG, insights | no_cta |
| Sat | lifestyle_systems_thinking | Less time in socials, more in clients | IG | no_cta |
| Sun | weekly_recap | Week in Flexity content + one lesson | TG | article_link |
```

## 11. Example daily brief

```yaml
brief_date: "2026-06-30"
recommended_slug: "2026-06-30-lead-to-contract-without-excel"
content_theme: "practical_business_scenario"
topic_hook: "Как выглядит путь от заявки до договора без Excel и потерянных сообщений"
audience: "owner of consulting / service business, 5–30 people"
channels:
  telegram: required
  instagram: required
  insights: recommended
  tiktok: planned_only
tone:
  - calm
  - practical
  - founder_led
avoid:
  - claiming full CRM automation is live for all tenants
  - aggressive demo push
key_points:
  - "Problem: leads live in messengers and spreadsheets"
  - "Process: one work item, one party, one document draft"
  - "Flexity direction: universal modules, not another chat tool"
claims_to_verify:
  - "Do not say public inbound leads intake is live unless PUBLIC_LEADS_ENABLED=true in runbook"
cta_type: "soft_demo_process_review"
reference_slugs:
  - "2026-06-22-ai-tools-need-process"
  - "2026-06-24-ai-personal-content-assistant"
repetition_warnings:
  - "Avoid third 'AI chaos' post in 7 days — use concrete contract scenario instead"
publish_log_notes: []
```

## 12. Boundaries: what it must not do

- **Must not publish** to Telegram, Instagram, insights, TikTok, or any external API.
- **Must not modify** content-packs, articles, assets, workflows, or publisher scripts automatically.
- **Must not commit** to git without explicit human approval.
- **Must not read or store** secrets, tokens, `.env`, or GitHub Actions credentials.
- **Must not trigger** GitHub Actions, deploy, nginx, or rsync.
- **Must not overwrite** human drafts — only recommend and brief.
- **Must not** mark content `approved` or `published`.
- **Must not** generate video/audio for TikTok without separate approved plan.
- Output is **recommendations, plans, and briefs only**; Content Pack Agent + human own execution.

## 13. Future implementation phases

### Phase 1 — Documentation only (this plan)

Document agent role, inputs, outputs, boundaries. No code.

### Phase 2 — Read-only analyzer script (optional, separate approval)

- Parse content-packs and articles from repo paths
- Emit JSON/markdown report locally
- No writes, no API calls

### Phase 3 — Strategist Agent prompt + skill

- Cursor skill or agent definition with fixed read paths and output templates
- Human invokes manually before daily content session

### Phase 4 — Weekly scheduled report (optional)

- GitHub Action or local cron that generates report artifact only (no publish)
- Requires separate approval; must not touch publisher workflows

### Phase 5 — Integration with Content Pack Agent

- Strategist brief → input contract for Content Pack Agent
- Human approves brief before pack creation

### Phase 6 — Claims registry (optional)

- Maintain `docs/content/claims-registry.yml` of allowed/disallowed product statements
- Strategist cross-checks against registry automatically

## Approval status

This document is **documentation only**. It does not approve implementation, new scripts, workflow changes, backend changes, or any automated publishing.

## Related docs

- [Content Factory](../../content/content-factory.md)
- [Insights Publishing](../../content/insights-publishing.md)
- [Telegram content-pack template](../../content/templates/telegram-content-pack-template.md)
- [Instagram content-pack template](../../content/templates/instagram-content-pack-template.md)
- [TikTok content-pack template](../../content/templates/tiktok-content-pack-template.md) (planned)
- [Media library content assets plan](2026-06-24-media-library-content-assets-plan.md)

## Checks

```bash
git diff --check
git status --short
```
