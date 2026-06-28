# Flexity Monthly Content Plan — June 2026

**Author:** Asem Islyamova  
**Period:** 4 weeks (June 2026 editorial cycle)  
**Status:** approved content directions and calendar — documentation only  
**Related:** [Content Factory](content-factory.md), [Content Strategist Agent plan](../ai/plans/2026-06-27-content-strategist-agent-plan.md)

This document records the approved monthly content plan and publishing channels roadmap. It does not authorize implementation, workflows, or live publishing on new channels.

## 1. Approved content directions

Flexity/Asem content mix for the month balances product, founder voice, and practical business value.

| Direction | Description | Typical format |
|-----------|-------------|----------------|
| **Author column by Asem** | Founder-led essays and reflections | Telegram long post, /insights article, Instagram carousel |
| **Practical business scenarios** | Real operational problems (CRM, contracts, cash, users) | Scenario post + soft process CTA |
| **Vibe coding / AI project ideas** | Ideas built with AI assistance; honest build logs | Build-in-public note, Wednesday slot |
| **Weekly news and conclusions** | AI / CRM / ERP / SaaS digest with founder takeaway | Friday news slot |
| **Build in public / development reports** | What shipped in Flexity repo or Content Factory | Thursday product narrative |
| **Audience work / polls / reposts / analytics** | Polls, answer analysis, engagement | Sunday slot |
| **Creative AI use** | Non-obvious AI workflows (menu, patterns, life tools) | Saturday creative slot |
| **Personal life / stories / human layer** | Human context without oversharing | Woven into Sunday/Saturday |
| **Flexity product vision** | Superstructure, modules, honest roadmap | Thursday + selective Mondays |

**Tone rules (all directions):**

- calm, practical, founder-led
- not hype, not aggressive selling
- honest about not-yet-implemented features
- use wording such as «развиваем», «закладываем», «можно настроить» for roadmap items

## 2. Four-week calendar

Publishing rhythm: **Sunday → Saturday** editorial week. Each row is one content-pack day (`YYYY-MM-DD-slug`).

### Week 1

| Day | Topic | Primary direction |
|-----|-------|-----------------|
| **Sunday** | Неделя, в которой контент стал системой | Author column / audience |
| **Monday** | Клиент просит CRM, а реальная проблема может быть в кассовом разрыве | Practical business scenario |
| **Tuesday** | Работа без договора и проблемы оплаты/контроля | Practical business scenario |
| **Wednesday** | Content Strategist Agent как идея vibe coding | Vibe coding / AI project idea |
| **Thursday** | Почему рождается надстройка Flexity | Flexity product vision |
| **Friday** | Еженедельные новости AI / CRM / ERP / SaaS | Weekly news |
| **Saturday** | Легче ли делегировать ИИ, чем человеку? | Creative AI use / human layer |

### Week 2

| Day | Topic | Primary direction |
|-----|-------|-----------------|
| **Sunday** | Опрос: какую задачу вы бы первой отдали ИИ? | Audience / poll |
| **Monday** | Почему программист и бизнес не понимают друг друга | Practical business scenario |
| **Tuesday** | Почему внедрение Битрикс не сработало | Practical business scenario |
| **Wednesday** | Генератор паттернов одежды/обуви на основе 3D-модели человека | Vibe coding / AI project idea |
| **Thursday** | От учёта cash-flow к медицинской ERP | Build in public / product vision |
| **Friday** | Еженедельные новости AI-агентов и бизнес-приложений | Weekly news |
| **Saturday** | Генератор меню по содержимому холодильника | Creative AI use |

### Week 3

| Day | Topic | Primary direction |
|-----|-------|-----------------|
| **Sunday** | Разбор ответов аудитории | Audience / analytics |
| **Monday** | От чего зависит стоимость разработки ПО | Practical business scenario |
| **Tuesday** | Сначала учётная политика, потом разработка | Practical business scenario |
| **Wednesday** | База антропометрических параметров за всю жизнь | Vibe coding / AI project idea |
| **Thursday** | Есть ли или должен ли быть аналог 1С? | Flexity product vision |
| **Friday** | Еженедельные новости SaaS / подписок / AI | Weekly news |
| **Saturday** | Vibe coder работает даже вдали от ноутбука | Creative AI use / personal |

### Week 4

| Day | Topic | Primary direction |
|-----|-------|-----------------|
| **Sunday** | Опрос: что раздражает в CRM? | Audience / poll |
| **Monday** | Нужен ли всегда ИИ, если достаточно алгоритма? | Practical business scenario |
| **Tuesday** | Пользователи есть в системе, но никто не работает | Practical business scenario |
| **Wednesday** | Приложение профориентации для детей | Vibe coding / AI project idea |
| **Thursday** | Владелец бизнеса как начальник AI-сотрудников | Flexity product vision |
| **Friday** | Еженедельные новости AI в госсекторе / документах / операциях | Weekly news |
| **Saturday** | ИИ в госсекторе из личного опыта | Personal / creative AI |

## 3. Channel matrix

For each content-pack, plan coverage across channels. **Operational** channels can be published after approval and deploy. **Planned** channels are documented intent only until separate implementation is approved.

### Channel status (honest)

| Channel | Status | Notes |
|---------|--------|-------|
| **Telegram** | operational | `pack.yml`, `telegram.md`, `publish_log.yml`, workflow |
| **Instagram** | operational | `feed_image` / carousel assets; Meta Graph token required |
| **/insights** | operational | `landing/content/articles/*.md` → static HTML |
| **Facebook** | planned | No API/workflow in repo yet |
| **Threads** | planned | No API/workflow in repo yet |
| **TikTok / Reels** | planned | Script/video-first; manual until API/workflow approved |
| **WhatsApp Business** | inbound / messaging | Primary use: leads and conversations, **not** social feed autoposting |

### Per-pack channel matrix template

Use in each `landing/content/content-packs/YYYY-MM-DD-slug/` planning notes or future `distribution.yml`:

| Channel | Week 1 Sun (example) | Operational? | Action when planned |
|---------|------------------------|--------------|---------------------|
| Instagram | Carousel or feed — «контент стал системой» | yes | Approve `instagram.yml` + assets |
| Telegram | Long founder post + link to /insights | yes | Approve `pack.yml` + `telegram.md` |
| Facebook | Cross-post caption (manual) | planned | Manual or future publisher |
| Threads | Short hook + link | planned | Manual or future publisher |
| TikTok / Reels | 30–60s talking head or text-on-screen script | planned | `tiktok_script.md` only; no auto-publish |
| /insights | Full article when depth warrants | yes | `status: approved` → `generate_insights.py` |

**Rules:**

- Do not claim Facebook, Threads, or TikTok are automated in Flexity Content Factory today.
- TikTok remains **planned/manual** until account, format spec, and implementation plan are approved.
- WhatsApp: point to demo/inbound (`/demo/`, WhatsApp link) — not a scheduled publish channel in this matrix.

## 4. Today content pack summary

**Approved Sunday topic (Week 1):**

**Title:** Неделя, в которой контент стал системой

**Short summary:**  
Личная founder-колонка о том, как разрозненные посты превратились в повторяемую ContentOps-систему: content-pack, approval, Telegram, Instagram, /insights и планирование через strategist layer. Честно — без обещания, что всё уже полностью автоматизировано.

**Suggested slug:** `2026-06-28-content-became-system` (adjust date to actual publish Sunday)

**Primary channels:**

- Telegram — основной narrative
- Instagram — carousel (9 slides) or feed preview
- /insights — recommended full article
- Facebook / Threads — planned manual cross-post caption
- TikTok — optional script idea only (planned channel)

**CTA type:** `soft_demo_process_review` — приглашение посмотреть, как устроен процесс, без давления.

**Example CTA copy:**  
«Если вам тоже знакомо ощущение, что контент съедает неделю — начните с одного повторяемого процесса. Напишите, что у вас сейчас болит сильнее: идеи, публикация или учёт заявок.»

**UTM campaign (approved):**

```text
utm_campaign=content_as_system_2026_06_28
```

Suggested full tracking for links to `/demo/` or `/insights/`:

```text
?utm_source=instagram&utm_medium=social&utm_campaign=content_as_system_2026_06_28&utm_content=week1-sunday
```

## 5. Mobile publishing roadmap

Goal: approve and publish content from mobile without compromising safety (human approval, fail-closed publishers).

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 1** | GitHub Actions `workflow_dispatch` trigger from mobile browser (GitHub app) | planned |
| **Phase 2** | Approved content-pack picker input (slug selector, dry-run summary in job log) | planned |
| **Phase 3** | Simple internal mobile publisher page (read-only pack list + trigger link to Actions) | planned |
| **Phase 4** | Publish logs and rollback/status view (read `publish_log.yml` state, no auto-rollback) | planned |

**Boundaries (now):**

- No implementation in this document.
- No new secrets or workflows without separate approved plan.
- Publishing remains human-approved; mobile only triggers existing safe workflows.

## 6. Instagram token health roadmap

Instagram live publishing depends on valid Meta Graph credentials. Future operational hygiene:

| Capability | Description |
|------------|-------------|
| Safe token diagnostics | Script or workflow step that checks token validity **without printing token** |
| Expiry / permission checks | Detect expired or insufficient scopes before publish job |
| User / Page / IG account linkage | Verify Professional account ↔ Facebook Page ↔ token type match |
| Pre-expiry warnings | Notify operator N days before token expiry (e.g. log summary, GitHub issue, or manual checklist) |
| Token refresh / update-secret runbook | Separate doc: rotate secret in GitHub Actions, re-run dry-run, then live |

**Boundaries (now):**

- No secrets changes in this task.
- No code or workflow changes in this task.
- Reference existing diagnosis: [Instagram token endpoint mismatch plan](../ai/plans/2026-06-22-instagram-token-endpoint-mismatch-diagnosis.md), [token lifecycle plan](../ai/plans/2026-06-23-instagram-token-lifecycle-plan.md).

**Safety rules for future implementation:**

- Never log token values or full Authorization headers.
- Dry-run must pass before live workflow.
- Token type must match endpoint (`graph.facebook.com` vs Instagram Login token).

## 7. Explicit out of scope (this document)

- No code, scripts, or workflows
- No publishing to any channel
- No changes to `content-packs/**`, assets, or `publish_log.yml`
- No backend, platform-console, deploy, nginx, or secrets
- No enabling Facebook, Threads, or TikTok automation

## 8. Related documentation

- [Content Factory](content-factory.md)
- [Content Strategist Agent plan](../ai/plans/2026-06-27-content-strategist-agent-plan.md)
- [TikTok content-pack template](templates/tiktok-content-pack-template.md)
- [Insights publishing](insights-publishing.md)
- [Public inbound leads runbook](../ai/plans/2026-06-24-public-inbound-leads-runbook.md) — demo/lead intake; separate from social autopost

## Checks

```bash
git diff --check
git status --short
```
