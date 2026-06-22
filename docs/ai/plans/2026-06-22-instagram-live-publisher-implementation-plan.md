# Implementation Plan: Instagram Live Publisher

## Goal

Спланировать реализацию live Instagram publisher для Flexity content-packs: отдельный CLI-скрипт, который при явном `--live` публикует approved `feed_image` посты через Meta Instagram Graph API, записывает результат в `instagram.yml` и `publish_log.yml`, и при этом остаётся fail-closed по умолчанию.

Этот план **не разрешает** реализацию кода, вызовы Meta/Instagram API, создание GitHub workflow, изменение статусов content-pack или первую live-публикацию.

## Classification

- Project: Flexity
- Category: `universal_module` (content automation integration, вне Flexity backend)
- Risk: **high** — внешняя публикация, privileged credentials, необратимый side effect в Instagram
- Current branch at planning time: `main`
- Required plan type: implementation plan
- Dependencies: существующие `PyYAML`, `requests` (уже используется в `publish_telegram.py`); без новых pip-зависимостей

## Current State

Уже готово и не должно ломаться:

- GitHub Secrets names подтверждены: `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN`
- Public image URL работает:
  `https://www.flexity.asia/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png`
- Текущий Instagram pack остаётся draft:
  `landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml`
- Dry-run publisher:
  `scripts/content/publish_instagram.py` — только `--dry-run`, без HTTP и без записи файлов
- Telegram autopublish production-ready:
  `scripts/content/publish_telegram.py` — не трогать
- Meta readiness plan:
  `docs/ai/plans/2026-06-22-instagram-meta-api-readiness-plan.md`

## Scope

### Files to create (после approval)

- `scripts/content/publish_instagram_live.py` — новый live publisher
- `tests/scripts/content/test_publish_instagram_live.py` — unit tests с mocked HTTP only

### Files to modify (после approval)

- `docs/content/instagram-publishing.md` — секция live publisher, first-live approval gate, note про Meta dashboard verification

### Files not to touch

- `scripts/content/publish_instagram.py` — dry-run publisher остаётся без изменений
- `scripts/content/publish_telegram.py`
- `.github/workflows/**` — workflow будет отдельным шагом
- все существующие `landing/content/content-packs/**`, включая статус `instagram.yml`
- `backend/**`
- `landing/www/**`, включая `/insights`
- nginx/systemd configuration
- `deploy/**`
- credentials, secrets, `.env`, `Flexity.code-workspace`
- `docs/content/instagram-api-readiness.md` — только если явно потребуется в отдельном approval

## MVP Contract

Live publisher поддерживает **только**:

| Поле / правило | MVP |
|---|---|
| `instagram.yml type` | `feed_image` only |
| media | только `media.image_url` |
| caption | только через `caption_source: instagram.md` |
| `pack.yml` | top-level `status: approved` обязателен |
| `instagram.yml` | `status: approved` обязателен |

**Future scope (не в этом slice):**

- `reels`
- `carousel`
- другие `caption_source`
- HTTP (не HTTPS) media URL
- автоматический GitHub Actions workflow
- изменение dry-run publisher

## Required Gates (fail-closed)

Пакет публикуется в `--live` только если **все** условия выполнены одновременно.

### Eligibility gates → `SKIP` (exit 0, без API)

| Gate | Причина skip |
|---|---|
| `pack.yml` отсутствует или не читается | логировать `ERROR`, не публиковать |
| top-level `pack.yml status` ≠ `approved` | `SKIP: pack.status is not approved` |
| `instagram.yml` отсутствует | `SKIP` или `ERROR` по аналогии с Telegram |
| `instagram.yml status` ≠ `approved` | `SKIP: status is not approved` |
| `published_at` уже заполнен | `SKIP: already published` |
| `external_id` уже заполнен | `SKIP: already published` |
| `publish_at` в будущем | `SKIP: publish_at is in the future` |
| `publish_at` отсутствует или без timezone | `ERROR`, non-zero exit |

### Validation gates → `ERROR` (exit non-zero, без API)

| Gate | Поведение |
|---|---|
| `type` ≠ `feed_image` | `ERROR`, non-zero |
| `media.image_url` отсутствует или пустой | `ERROR` |
| `media.image_url` не начинается с `https://` | `ERROR` |
| `caption_source` отсутствует | `ERROR` |
| `caption_source` выходит за пределы pack directory | `ERROR` |
| caption file не существует или пустой | `ERROR` |
| `INSTAGRAM_USER_ID` отсутствует в env | `ERROR`, fail closed до scan packs |
| `INSTAGRAM_ACCESS_TOKEN` отсутствует в env | `ERROR`, fail closed до scan packs |

### Republish protection

- Если `published_at` уже есть — **никогда** не вызывать API и не перезаписывать поля.
- Если `external_id` уже есть — то же самое.
- При API/network ошибке **не** заполнять `published_at`, **не** заполнять `external_id`, **не** менять `status` на `published`.

## Meta API Flow (design only)

> Перед первым live run обязательно сверить exact permissions, Graph API version и endpoint parameters с текущим Meta App Dashboard и официальной документацией Meta. Этот план фиксирует intended flow, но не утверждает конкретную API version.

### Intended two-step publish (feed image)

```text
1. Create media container
   POST /{INSTAGRAM_USER_ID}/media
   body/params:
     - image_url = instagram.yml media.image_url
     - caption   = text from instagram.md
     - access_token (from env only; never logged)

   success response:
     { "id": "<creation_id>" }

2. Publish media container
   POST /{INSTAGRAM_USER_ID}/media_publish
   body/params:
     - creation_id = <creation_id>
     - access_token (from env only; never logged)

   success response:
     { "id": "<published_media_id>" }
```

### Optional container readiness step

Если актуальная Meta documentation требует polling container status перед `media_publish`, добавить read-only status check между шагами 1 и 2. Для single-image feed post это может быть необязательно — решение принимается только после сверки с dashboard/docs **до** первого live run.

### Post-success writes (только после подтверждённого API success)

Атомарно, в порядке:

1. `instagram.yml`:
   - `published_at` = текущее timezone-aware ISO datetime (UTC preferred, как в Telegram publisher)
   - `external_id` = `<published_media_id>` из API response
   - `status` = `"published"`
2. `publish_log.yml`:
   - append event:
     ```yaml
     - at: "<iso datetime>"
       channel: instagram
       status: published
       external_id: "<published_media_id>"
     ```

### Post-failure behavior

- При ошибке create/publish:
  - append `publish_log.yml` event со `status: error` и безопасным `error` message (без token, без full response body с credentials)
  - **не** менять `published_at`, `external_id`, `status`
- При ambiguous timeout/network error:
  - не считать publish успешным
  - не делать blind retry create в том же run без отдельного idempotency research

### Base URL and version

- Использовать Graph API base URL, version — константа в скрипте (например `v21.0`), но значение **не утверждается** этим планом.
- Перед первым live run владелец Meta assets проверяет supported version в App Dashboard.

## CLI Contract

Новый скрипт: `scripts/content/publish_instagram_live.py`

### Default mode: dry-run (без флагов)

```bash
python scripts/content/publish_instagram_live.py
```

Поведение dry-run:

- сканирует `landing/content/content-packs/*/instagram.yml`
- читает соответствующий `pack.yml` для top-level status gate
- читает caption из `instagram.md` через `caption_source`
- проверяет все MVP gates и validation rules
- печатает `WOULD_PUBLISH` / `SKIP` / `ERROR` по аналогии с dry-run Instagram/Telegram publishers
- **не** читает secrets для preview eligibility (или читает только факт presence без значений — предпочтительно: в dry-run secrets не требуются для `WOULD_PUBLISH`, но отсутствие secrets в `--live` — hard fail)
- **не** вызывает Meta API
- **не** пишет `instagram.yml`, `publish_log.yml`, `pack.yml` или любые другие файлы

Рекомендуемый dry-run output для eligible pack:

```text
WOULD_PUBLISH pack=<slug> type=feed_image caption_length=<n> image_url=<https://...> publish_at=<iso> would_publish=true
```

### Live mode: только с явным флагом

```bash
python scripts/content/publish_instagram_live.py --live
```

Поведение `--live`:

- требует `INSTAGRAM_USER_ID` и `INSTAGRAM_ACCESS_TOKEN` в env
- при отсутствии любого secret — immediate fail closed, non-zero exit
- вызывает Meta API только для packs, прошедших все gates
- может писать **только**:
  - `<pack>/instagram.yml`
  - `<pack>/publish_log.yml`
- **не** пишет `pack.yml`, `instagram.md`, dry-run files, workflow artifacts

Дополнительно рекомендуется (но не обязательно в MVP, если усложняет scope):

- `--pack <slug>` — ограничить run одним pack для controlled first publish

Если `--pack` не входит в MVP, первая live-публикация выполняется при единственном eligible pack после manual status approval.

### Relationship to existing dry-run script

| Script | Purpose |
|---|---|
| `publish_instagram.py --dry-run` | read-only validator/preview для feed/carousel/reels schema |
| `publish_instagram_live.py` (default) | live-oriented dry-run с pack.yml gate и HTTPS-only MVP rules |
| `publish_instagram_live.py --live` | actual Meta API publish |

Существующий `publish_instagram.py` **не менять**. Допустимо в live script импортировать read-only helpers из `publish_instagram.py` (`load_yaml`, `parse_publish_at`, `read_caption`) без модификации исходного файла.

## Secrets Safety

| Rule | Requirement |
|---|---|
| Source | только `os.environ` / injected `environ` mapping в tests |
| Names | `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN` only |
| Missing secret | fail closed, non-zero exit, generic message `ERROR: INSTAGRAM_ACCESS_TOKEN is not set` |
| Logging | never print token value |
| Files | never write token to `instagram.yml`, `publish_log.yml`, stdout, stderr |
| API errors | sanitize error messages; strip query params and auth headers from diagnostics |
| Tests | use fake env values like `test-token-abc`; assert token absent from stdout/stderr/log files |

## Implementation Steps (after approval)

1. **Skeleton CLI**
   - `argparse` with default dry-run and `--live` flag
   - scan `landing/content/content-packs/*/instagram.yml`
   - no HTTP yet

2. **Shared validation layer**
   - `should_publish(pack.yml, instagram.yml, now)` → `(allowed, reason)`
   - `validate_feed_image_mvp(instagram.yml, pack_dir)` → image_url, caption
   - HTTPS-only check for `media.image_url` (stricter than dry-run script)
   - reject non-`feed_image` types with `ERROR`

3. **Dry-run runner**
   - print `SKIP` / `WOULD_PUBLISH` / `ERROR`
   - zero file writes
   - exit `1` if any `ERROR`, else `0`

4. **Meta API client (isolated functions)**
   - `create_media_container(user_id, token, image_url, caption) -> creation_id`
   - `publish_media_container(user_id, token, creation_id) -> external_id`
   - use `requests` with timeout (30s, как Telegram)
   - raise `RuntimeError` with sanitized message on HTTP/JSON/business errors
   - never include token in exception text

5. **Atomic YAML writes**
   - reuse temp-file + `os.replace` pattern from `publish_telegram.py`
   - `append_log(pack_dir, event)` for `publish_log.yml`
   - write success fields only after both API steps succeed

6. **Live runner**
   - secrets preflight before pack loop
   - per-pack try/except with error log append
   - print `PUBLISHED <slug>: external_id=<id>` without token

7. **Tests**
   - new file `tests/scripts/content/test_publish_instagram_live.py`
   - temp content-packs dir, no network
   - `unittest.mock.patch` on `requests.post` or client functions

8. **Documentation**
   - update `docs/content/instagram-publishing.md`:
     - live script usage
     - dry-run default vs `--live`
     - required gates recap
     - first live publish requires **separate explicit approval**
     - note: verify permissions and Graph API version in Meta dashboard before first live run
     - workflow intentionally deferred

9. **QA verification (manual, no API in CI plan step)**
   - `python -m unittest discover -s tests/scripts/content -p 'test_publish_instagram_live.py' -v`
   - `python -m compileall scripts/content/publish_instagram_live.py tests/scripts/content/test_publish_instagram_live.py`
   - `python scripts/content/publish_instagram_live.py` against repo — must not write files
   - `git diff --check` and forbidden-scope review

## Tests / Checks

Все тесты — **mocked HTTP only**, без реальных Meta API calls.

| Test case | Expected |
|---|---|
| approved pack + approved instagram + due schedule + valid HTTPS image + caption | `--live` with mocked API → `PUBLISHED`, writes `published_at`, `external_id`, `status: published`, log event |
| draft `instagram.yml` | `SKIP`, no API calls |
| draft top-level `pack.yml` | `SKIP`, no API calls |
| already published (`published_at` set) | `SKIP`, no API calls |
| already published (`external_id` set) | `SKIP`, no API calls |
| missing `INSTAGRAM_ACCESS_TOKEN` in `--live` | fail closed, non-zero, no API |
| missing `INSTAGRAM_USER_ID` in `--live` | fail closed, non-zero, no API |
| `media.image_url` = `http://...` | `ERROR`, no API |
| `media.image_url` missing | `ERROR`, no API |
| API error on create container | no `published_at`/`external_id` update; error log event; non-zero exit |
| API error on publish step | no success fields; error log event; non-zero exit |
| successful publish | `published_at`, `external_id`, `publish_log` written; `instagram.md` and `pack.yml` unchanged |
| token in env | never appears in stdout, stderr, or written YAML files |
| default dry-run | no HTTP, no file writes |
| `type: carousel` / `type: reels` | `ERROR` in MVP |

Дополнительные compile/diff checks — см. Implementation Steps §9.

## First Live Publication Gate

Approval **этого** implementation plan ≠ approval на первую реальную публикацию.

Перед первым `--live` run с реальными secrets:

1. Code review и test green по этому плану.
2. Meta dashboard verification: permissions, App Review status, Graph API version, token scope/expiry.
3. Human review caption, image URL и целевого Instagram account.
4. Dry-run:
   - `python scripts/content/publish_instagram.py --dry-run`
   - `python scripts/content/publish_instagram_live.py`
   — ожидаемый результат после future approval статусов: ровно один eligible pack.
5. **Отдельное явное approval** пользователя на первый Meta API publish.
6. Controlled run, желательно с одним pack.
7. Post-check: public post, `external_id`, `publish_log.yml`.

Текущий pack `2026-06-22-ai-tools-need-process` остаётся `draft` до отдельного content approval.

## GitHub Actions (deferred)

- **Не создавать workflow** в этом slice.
- Будущий workflow — отдельный implementation plan после local/manual verification live publisher.
- Workflow должен быть:
  - manually triggered (`workflow_dispatch`)
  - protected environment with `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN`
  - concurrency guard (один publish job at a time)
  - отдельным от Telegram workflow

## Risks

| Risk | Mitigation |
|---|---|
| Token leak via logs/output | fail-closed secret handling; redacted errors; tests assert no token in output |
| Duplicate post on retry after timeout | do not mark published on ambiguous response; manual recovery playbook |
| Wrong account / wrong Page linkage | preflight Meta dashboard verification; separate first-live approval |
| Meta cannot fetch public image URL | known-good URL already verified; re-check before first live |
| API version / permission drift | dashboard verification gate before first live run |
| Publishing draft content | dual gate: `pack.yml` + `instagram.yml` must be `approved` |
| Scope creep into carousel/reels | MVP explicitly rejects non-`feed_image` |
| Accidental change to Telegram path | forbidden files list; separate script and tests |
| Two dry-run scripts diverge | document responsibilities; optional import of read-only helpers only |

## Rollback

**До реализации:** удалить только этот plan-файл.

**После реализации, до первого live run:** revert/delete только:

- `scripts/content/publish_instagram_live.py`
- `tests/scripts/content/test_publish_instagram_live.py`
- live section в `docs/content/instagram-publishing.md`

**После успешной live publish:** локальный rollback metadata **не удаляет** Instagram post. Удаление внешней публикации — отдельная ручная операция с отдельным approval.

**При credential incident:** revoke/rotate token в Meta, обновить GitHub secret; не коммитить credentials.

## Approval

Status: **waiting for approval**

После approval разрешено:

- создать `scripts/content/publish_instagram_live.py`
- создать `tests/scripts/content/test_publish_instagram_live.py`
- обновить `docs/content/instagram-publishing.md`

После approval **не разрешено** без отдельного шага:

- первый реальный `--live` publish
- GitHub workflow
- изменение статусов content-pack
- изменение `publish_instagram.py`, Telegram publisher/workflow
- вызовы Meta API в CI или локально вне controlled first-live gate
