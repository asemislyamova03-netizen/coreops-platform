# First-Live Readiness Plan: First Instagram Publish (Flexity)

## Goal

Спланировать первую контролируемую live-публикацию Flexity content-pack через:

```bash
python scripts/content/publish_instagram_live.py --live
```

Этот план **не разрешает**:

- запуск `--live`;
- вызовы Meta/Instagram API;
- изменение статусов content-pack;
- commit или push;
- изменение publisher code, workflow, backend, deploy.

Approval этого readiness plan ≠ approval на первый реальный `--live` run.

## Classification

- Project: Flexity
- Category: `documentation_only`
- Risk: **high** — первая внешняя публикация в Instagram, privileged credentials, необратимый side effect
- Current branch at planning time: `main`
- Live publisher MVP: `scripts/content/publish_instagram_live.py` (commit `147c2c1`)

## Current State

| Item | Value |
|------|-------|
| Target pack | `landing/content/content-packs/2026-06-22-ai-tools-need-process/` |
| `pack.yml` top-level status | `approved` |
| `instagram.yml` status | `draft` |
| `instagram.yml` published_at | `null` |
| `instagram.yml` external_id | `null` |
| `instagram.yml` type | `feed_image` |
| `instagram.yml` publish_at | `2026-06-22T18:00:00+05:00` (timezone-aware, due) |
| Public image URL | `https://www.flexity.asia/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png` |
| Last known media check | HTTP `200`, `Content-Type: image/png` |
| GitHub Secrets (names only) | `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN` |
| Telegram | already published; Telegram files must not change |

`publish_log.yml` currently contains only a Telegram `published` event (`message_id: 4`).

## Scope

### Files that may change (only after separate step approval)

| Step | File | Change |
|------|------|--------|
| Approval switch commit | `landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml` | `status: "draft"` → `status: "approved"` |
| Post-live metadata commit | `landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml` | `published_at`, `external_id`, `status: published` (written by `--live`) |
| Post-live metadata commit | `landing/content/content-packs/2026-06-22-ai-tools-need-process/publish_log.yml` | append Instagram publish event (written by `--live`) |

### Files not to touch

- `pack.yml` in target pack (already `approved`; do not modify)
- `telegram.md`, `publish.telegram` block in `pack.yml`, any Telegram-only files
- `scripts/content/publish_instagram_live.py`
- `scripts/content/publish_instagram.py`
- `scripts/content/publish_telegram.py`
- `.github/workflows/**`
- `backend/**`
- `landing/www/**`, including `/insights`
- nginx, deploy scripts, secrets values, `.env`
- `Flexity.code-workspace`

---

## Step 1: Pre-flight checks

Выполнить **до** approval switch. Только read-only операции; secret **values** не читать и не печатать.

### 1.1 Sync repository

```bash
git pull --ff-only origin main
git status --short
```

Ожидание:

- рабочая копия на `main`;
- нет незакоммиченных изменений в target pack, publisher, workflow;
- `publish_instagram_live.py` присутствует в `main`.

### 1.2 Verify public image URL

```bash
curl -I "https://www.flexity.asia/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png"
```

Ожидание:

- HTTP `200`;
- `Content-Type: image/png` (или другой поддерживаемый image type, подтверждённый Meta dashboard);
- URL доступен без authentication.

Если ответ не `200` или media недоступна — **остановиться**, не переходить к approval switch.

### 1.3 Verify pack metadata (read-only)

Проверить `landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml`:

```yaml
status: "draft"
published_at: null
external_id: null
type: "feed_image"
media:
  image_url: "https://www.flexity.asia/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png"
caption_source: "instagram.md"
```

Проверить `pack.yml`:

```yaml
status: approved
```

Проверить, что `instagram.md` существует и caption не пустой.

### 1.4 Verify GitHub secret names (not values)

```bash
gh secret list
```

Ожидание: в списке присутствуют **имена**:

- `INSTAGRAM_USER_ID`
- `INSTAGRAM_ACCESS_TOKEN`

Не выполнять:

- `gh secret list` с выводом значений (невозможно через gh для values — и не пытаться обходить);
- чтение secrets из `.env`, CI logs, workflow YAML;
- печать token или user id в терминал/чат.

### 1.5 Meta dashboard verification (manual, before live)

Перед первым `--live` владелец Meta assets вручную подтверждает в App Dashboard:

- Instagram Professional account связан с Facebook Page;
- token scope и permissions достаточны для content publishing;
- Graph API version в publisher (`v21.0` constant) совместима с App;
- token не expired.

Этот checklist не выполняется в рамках создания данного plan-файла.

### 1.6 Baseline dry-run (current draft state)

```bash
python scripts/content/publish_instagram_live.py
```

Ожидание **сейчас** (пока `instagram.yml` = `draft`):

```text
SKIP 2026-06-22-ai-tools-need-process: status is not approved
Done. Would publish: 0. Errors: 0
```

- API не вызывается;
- файлы не изменяются.

---

## Step 2: Approval switch

Только после успешных pre-flight checks и **отдельного human approval** на смену статуса.

### Единственное разрешённое изменение metadata

Файл:

`landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml`

Изменить:

```yaml
status: "approved"
```

Оставить без изменений:

- `published_at: null`
- `external_id: null`
- `type`, `publish_at`, `media`, `caption_source`
- все Telegram-related files
- `pack.yml`

---

## Step 3: Dry-run after approval switch

После локального изменения `instagram.yml` (до commit):

```bash
python scripts/content/publish_instagram_live.py
```

Ожидание:

```text
WOULD_PUBLISH pack=2026-06-22-ai-tools-need-process type=feed_image ... would_publish=true
Done. Would publish: 1. Errors: 0
```

Проверки:

- `Would publish: 1` (ровно один pack);
- exit code `0`;
- API **не** вызывается;
- `instagram.yml`, `publish_log.yml`, `pack.yml` **не** изменяются dry-run'ом;
- secrets **не** требуются в default dry-run mode.

Если `Would publish: 0` или есть `Errors` — **не commitить** approval switch; исправить metadata или gates.

---

## Step 4: Commit approval switch

Только после успешного dry-run из Step 3.

```bash
git add landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml
git commit -m "Approve first Instagram live publish"
git push origin main
```

Commit содержит **только** `instagram.yml`.

Не добавлять в commit:

- `pack.yml`
- `telegram.md`
- `publish_log.yml`
- publisher code
- workflow

---

## Step 5: Live run

Только после:

1. approval switch закоммичен и запушен;
2. **отдельного явного approval** пользователя на первый Meta API publish;
3. Meta dashboard verification (Step 1.5);
4. secrets доступны в локальном env **или** в controlled CI environment (workflow пока не используется — предпочтительно локальный run с env vars, без печати values).

Команда:

```bash
python scripts/content/publish_instagram_live.py --live
```

Ожидаемое поведение publisher:

1. Preflight: `INSTAGRAM_USER_ID` и `INSTAGRAM_ACCESS_TOKEN` present → иначе fail closed;
2. Pack passes all gates (`pack.yml` approved, `instagram.yml` approved, due `publish_at`, not yet published);
3. MVP validation: `feed_image`, HTTPS `image_url`, `caption_source: instagram.md`;
4. Meta API:
   - `POST /{INSTAGRAM_USER_ID}/media` → `creation_id`;
   - `POST /{INSTAGRAM_USER_ID}/media_publish` → `external_id`;
5. Write only:
   - `instagram.yml`: `published_at`, `external_id`, `status: published`;
   - `publish_log.yml`: append Instagram event.

Ожидаемый stdout (пример):

```text
PUBLISHED 2026-06-22-ai-tools-need-process: external_id=<instagram_media_id>
Done. Published: 1. Errors: 0
```

**Не запускать `--live`** в рамках подготовки или approval этого readiness plan.

---

## Step 6: Post-live checks

Сразу после успешного `--live` (read-only + dry-run):

### 6.1 Verify `instagram.yml`

```yaml
status: "published"
published_at: "<timezone-aware ISO timestamp>"
external_id: "<instagram_media_id>"
```

`published_at` и `external_id` must not remain `null`.

### 6.2 Verify `publish_log.yml`

Должно появиться новое событие:

```yaml
- at: "<iso datetime>"
  channel: instagram
  status: published
  external_id: "<instagram_media_id>"
```

Существующее Telegram событие must remain unchanged.

### 6.3 Repeat dry-run (idempotency)

```bash
python scripts/content/publish_instagram_live.py
```

Ожидание:

```text
SKIP 2026-06-22-ai-tools-need-process: already published
Done. Would publish: 0. Errors: 0
```

### 6.4 Visual verification (manual, read-only)

- Открыть Instagram profile целевого account;
- Подтвердить, что post виден публично;
- Сверить image и caption с `instagram.md`;
- **Не** публиковать вручную через Instagram app как workaround.

---

## Step 7: Commit post-live metadata

Только после успешных post-live checks.

```bash
git add landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml
git add landing/content/content-packs/2026-06-22-ai-tools-need-process/publish_log.yml
git commit -m "Record first Instagram publish"
git push origin main
```

Commit содержит **только**:

- `instagram.yml`
- `publish_log.yml`

Не включать publisher code, workflow, Telegram files, `pack.yml`.

---

## Rollback / Failure Rules

| Scenario | Action |
|----------|--------|
| Create container failed | `instagram.yml` unchanged (`published_at`/`external_id` null, `status` remains `approved`); error event in `publish_log.yml` possible; **не** retry blindly |
| Publish container failed | same — no success fields in `instagram.yml` |
| Ambiguous API response (timeout, partial success) | **не** помечать `published`; stop and analyze before retry |
| Published in Instagram but local write failed | **остановиться**; не запускать повторный `--live` без анализа; risk of duplicate post |
| Wrong post published | удаление в Instagram — отдельная ручная операция с отдельным approval; metadata rollback не удаляет external post |
| Token leak suspected | revoke/rotate in Meta; update GitHub secret; не коммитить credentials |
| Approval switch committed but live aborted | можно revert `instagram.yml` to `draft` только если API publish **не** произошёл |

Publisher behavior (already implemented):

- fail closed on missing secrets;
- skip if `published_at` or `external_id` already set;
- sanitize errors — token never in logs/output.

---

## Forbidden (this plan and until explicit live approval)

- Запуск `python scripts/content/publish_instagram_live.py --live`
- Вызовы Meta/Instagram API
- Изменение `instagram.yml` status в рамках создания этого plan
- Изменение Telegram files (`telegram.md`, `pack.yml` telegram block, Telegram publish_log entries)
- Изменение `pack.yml`
- Изменение publisher code (`publish_instagram_live.py`, `publish_instagram.py`, `publish_telegram.py`)
- Создание или изменение GitHub workflow
- Изменение `backend/**`, `landing/www/**`, deploy, nginx
- Чтение или печать secret values
- Deploy

---

## Execution Timeline (summary)

```text
[Pre-flight]  git pull, curl -I, read metadata, gh secret list (names), baseline dry-run
      ↓
[Approval]    instagram.yml: draft → approved (local only)
      ↓
[Dry-run]     Would publish: 1, no API, no file writes
      ↓
[Commit 1]    only instagram.yml — "Approve first Instagram live publish"
      ↓
[Gate]        separate explicit approval for --live
      ↓
[Live run]    python scripts/content/publish_instagram_live.py --live
      ↓
[Post-check]  instagram.yml, publish_log.yml, dry-run Would publish: 0, visual check
      ↓
[Commit 2]    instagram.yml + publish_log.yml — "Record first Instagram publish"
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Publishing while still draft | explicit approval switch step + dry-run gate |
| Duplicate post on retry | idempotency gates; no blind retry after ambiguous API |
| Token exposure | never print/read values; publisher sanitizes errors |
| Meta cannot fetch image | curl -I pre-flight; re-check before live |
| Wrong Graph API version / permissions | Meta dashboard verification before live |
| Local metadata out of sync with Instagram | stop if published externally but local write failed |
| Accidental Telegram changes | forbidden files list; commit scope limited |
| `--live` run without separate approval | explicit gate between Commit 1 and Step 5 |

---

## Approval

Status: **waiting for approval**

После approval этого readiness plan разрешено:

- выполнять Steps 1–4 (pre-flight, approval switch, dry-run, commit switch) — каждый с отдельным подтверждением по мере выполнения

После approval этого readiness plan **не разрешено** без отдельного шага:

- Step 5 live run (`--live`)
- Step 7 post-live commit (до успешного live)

Создание этого plan-файла не является approval на `--live`.
