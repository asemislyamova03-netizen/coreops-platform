# Implementation Plan: Instagram First-Live Manual GitHub Actions Workflow

## Goal

Спланировать безопасный **manual-only** GitHub Actions workflow для первой Instagram live-публикации Flexity content-pack через:

```bash
python scripts/content/publish_instagram_live.py --live
```

Workflow использует repository secrets `INSTAGRAM_USER_ID` и `INSTAGRAM_ACCESS_TOKEN`, выполняет pre-live dry-run gate, публикует через Meta API, коммитит post-live metadata и пушит в `main`.

Этот план **не разрешает**:

- создание workflow-файла;
- запуск workflow;
- вызовы Meta/Instagram API;
- локальный `--live` с ручной вставкой token;
- изменение content-pack, publisher code, Telegram path.

Approval этого plan ≠ approval на первый workflow run.

## Classification

- Project: Flexity
- Category: `universal_module` (content automation CI)
- Risk: **high** — первая внешняя Instagram публикация, privileged secrets, git write to main
- Current branch at planning time: `main`
- Dependencies: существующие `PyYAML`, `requests`; без новых pip-пакетов

## Current State

| Item | Value |
|------|-------|
| Live publisher MVP | `scripts/content/publish_instagram_live.py` (commit `147c2c1`) |
| Approval switch | commit `7384ab320ac07550e3bb67a6e4646aded783ea28` |
| Target pack | `landing/content/content-packs/2026-06-22-ai-tools-need-process/` |
| `instagram.yml` status | `approved` |
| `published_at` / `external_id` | `null` (ещё не опубликовано) |
| Local dry-run | `Would publish: 1`, `Errors: 0` |
| GitHub Secrets (names only) | `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN` |
| Local secrets | **недоступны** — первый `--live` только через GitHub Actions |
| Telegram workflow | `.github/workflows/telegram-publish.yml` — не трогать |
| Readiness plan | `docs/ai/plans/2026-06-22-instagram-first-live-readiness-plan.md` |

## Scope

### Files to create (после approval)

- `.github/workflows/instagram-live-publish.yml`

### Files that may change at runtime (only when workflow runs successfully)

- `landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml` — written by publisher (`published_at`, `external_id`, `status: published`)
- `landing/content/content-packs/2026-06-22-ai-tools-need-process/publish_log.yml` — append Instagram event

### Files not to touch (during implementation)

- `.github/workflows/telegram-publish.yml`
- `scripts/content/publish_telegram.py`
- `scripts/content/publish_instagram.py`
- `scripts/content/publish_instagram_live.py` (unless separate bugfix approval)
- `pack.yml`, `telegram.md`, `instagram.md`, visual assets
- `backend/**`, `landing/www/**`, deploy, nginx
- secrets values, `.env`
- `Flexity.code-workspace`

---

## Workflow Design

### File path (after approval)

```text
.github/workflows/instagram-live-publish.yml
```

### Trigger

```yaml
on:
  workflow_dispatch:
```

**Explicitly forbidden triggers:**

- `schedule` / cron
- `push` / `pull_request`
- `repository_dispatch` without separate approval
- any automatic future runs

Workflow запускается **только** вручную из GitHub Actions UI: *Run workflow*.

### Permissions and concurrency

```yaml
permissions:
  contents: write

concurrency:
  group: instagram-first-live-publish
  cancel-in-progress: false
```

- `contents: write` — для commit/push post-live metadata (как Telegram workflow).
- Concurrency group — один Instagram live job at a time; `cancel-in-progress: false` — не прерывать при ambiguous API state.

Опционально (рекомендация, не обязательно в MVP slice): GitHub Environment `instagram-live` с required reviewers. Если не используется — human gate остаётся на уровне manual `workflow_dispatch` + отдельное approval перед Run.

---

## Job Steps (intended)

Single job: `publish-first-instagram-live` on `ubuntu-latest`.

### Step 1: Checkout

```yaml
- uses: actions/checkout@v4
```

### Step 2: Setup Python

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"
```

Совпадает с Telegram workflow.

### Step 3: Install minimal dependencies

```yaml
- name: Install publisher dependencies
  run: python -m pip install pyyaml requests
```

Достаточно для `publish_instagram_live.py` и импорта `publish_instagram`.  
`python-dateutil` **не** нужен (в отличие от Telegram publisher).

### Step 4: Pre-live dry-run gate

```yaml
- name: Pre-live dry-run gate
  id: dry_run
  run: |
    set -euo pipefail
    OUTPUT="$(python scripts/content/publish_instagram_live.py)"
    printf '%s\n' "$OUTPUT"
    echo "$OUTPUT" | grep -q 'Would publish: 1'
    echo "$OUTPUT" | grep -q 'Errors: 0'
```

Поведение:

- dry-run **не** требует secrets (publisher design);
- если `Would publish` ≠ `1` или `Errors` ≠ `0` — step fails, `--live` **не** запускается;
- stdout печатается как есть (без secrets).

### Step 5: Verify secrets present (names only, no echo)

```yaml
- name: Verify Instagram secrets are configured
  env:
    INSTAGRAM_USER_ID: ${{ secrets.INSTAGRAM_USER_ID }}
    INSTAGRAM_ACCESS_TOKEN: ${{ secrets.INSTAGRAM_ACCESS_TOKEN }}
  run: |
    set -euo pipefail
    if [ -z "${INSTAGRAM_USER_ID}" ]; then
      echo "ERROR: INSTAGRAM_USER_ID secret is empty"
      exit 1
    fi
    if [ -z "${INSTAGRAM_ACCESS_TOKEN}" ]; then
      echo "ERROR: INSTAGRAM_ACCESS_TOKEN secret is empty"
      exit 1
    fi
    echo "Instagram secrets present (values not printed)"
```

**Never:**

- `echo "$INSTAGRAM_ACCESS_TOKEN"`
- `echo "$INSTAGRAM_USER_ID"` (optional: можно проверять только non-empty без печати)
- log env dump (`env`, `printenv` без фильтра)

### Step 6: Live publish

```yaml
- name: Publish first Instagram post
  id: live_publish
  env:
    INSTAGRAM_USER_ID: ${{ secrets.INSTAGRAM_USER_ID }}
    INSTAGRAM_ACCESS_TOKEN: ${{ secrets.INSTAGRAM_ACCESS_TOKEN }}
  run: |
    set -euo pipefail
    python scripts/content/publish_instagram_live.py --live
```

Ожидаемый stdout (пример):

```text
PUBLISHED 2026-06-22-ai-tools-need-process: external_id=<id>
Done. Published: 1. Errors: 0
```

Publisher уже sanitizes API errors. Workflow **не** добавляет retry (`retry-on`, `continue-on-error` для live step).

### Step 7: Verify git diff scope

```yaml
- name: Verify only expected metadata files changed
  run: |
    set -euo pipefail
    mapfile -t CHANGED < <(git diff --name-only)
    if [ "${#CHANGED[@]}" -eq 0 ]; then
      echo "ERROR: no files changed after live publish"
      exit 1
    fi
    ALLOWED=(
      "landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml"
      "landing/content/content-packs/2026-06-22-ai-tools-need-process/publish_log.yml"
    )
    for file in "${CHANGED[@]}"; do
      match=false
      for allowed in "${ALLOWED[@]}"; do
        if [ "$file" = "$allowed" ]; then
          match=true
          break
        fi
      done
      if [ "$match" = false ]; then
        echo "ERROR: unexpected changed file: $file"
        exit 1
      fi
    done
    echo "Changed files are within allowed scope"
```

### Step 8: Commit and push post-live metadata

```yaml
- name: Commit first Instagram publish metadata
  if: success()
  run: |
    set -euo pipefail
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git add \
      "landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml" \
      "landing/content/content-packs/2026-06-22-ai-tools-need-process/publish_log.yml"
    git commit -m "Record first Instagram publish"
    git push
```

Commit message фиксирован: `Record first Instagram publish`.

**Не** использовать broad glob (`landing/content/content-packs/**`) — только два explicit paths.

---

## Environment Variables

| Variable | Source | Rules |
|----------|--------|-------|
| `INSTAGRAM_USER_ID` | `${{ secrets.INSTAGRAM_USER_ID }}` | required for `--live`; never echo |
| `INSTAGRAM_ACCESS_TOKEN` | `${{ secrets.INSTAGRAM_ACCESS_TOKEN }}` | required for `--live`; never echo |

Secrets читаются только в live step и verify step. Dry-run step **не** передаёт secrets в env (не требуется).

---

## Safety Rules

| Rule | Implementation |
|------|----------------|
| Dry-run gate | fail if not `Would publish: 1` and `Errors: 0` |
| Empty secrets | explicit verify step before `--live` |
| No token in logs | no echo; rely on publisher sanitization; no `set -x` with secrets in env |
| Unexpected file changes | allowlist check before commit |
| No API retry | single `--live` invocation; job fails on non-zero exit |
| Ambiguous API response | publisher does not mark published; workflow fails; **no** workflow-level retry |
| No schedule | `workflow_dispatch` only |
| No automatic future runs | manual trigger only; document cleanup after first live |
| Telegram isolation | separate workflow file; no shared job with Telegram |
| Idempotency | second run should dry-run `Would publish: 0` (already published) — workflow should fail dry-run gate |

### Failure behavior

| Failure point | Expected outcome |
|---------------|------------------|
| Dry-run gate fails | job stops; no API; no commit |
| Secrets empty | job stops; no API |
| Create container fails | publisher logs error; no `published_at`; workflow fails; optional error in `publish_log.yml` |
| Publish fails | same; no success metadata |
| Unexpected git diff | job fails before commit |
| Commit/push fails | post may exist in Instagram; **stop** and analyze manually (readiness plan rule) |

---

## Forbidden

- Изменение `.github/workflows/telegram-publish.yml`
- Изменение Telegram publisher
- Изменение `backend/**`, nginx, deploy
- Изменение content-pack вручную в workflow (только publisher writes)
- Recurring / scheduled Instagram workflow
- `workflow_dispatch` с default auto-run on push
- Локальный `--live` через Cursor/PowerShell с paste token
- Чтение/печать secret values в plan, logs, artifacts
- Создание workflow в рамках этого plan document step

---

## Implementation Steps (after approval)

1. Создать `.github/workflows/instagram-live-publish.yml` по спецификации выше.
2. Review YAML: triggers, permissions, concurrency, no secret echo.
3. **Не** запускать workflow автоматически.
4. Human pre-run checklist:
   - `main` contains approval switch `7384ab3`;
   - secrets names exist (`gh secret list`);
   - public image URL still HTTP 200;
   - Meta dashboard permissions/API version verified.
5. Отдельное **explicit approval** на первый *Run workflow*.
6. Запустить workflow manually в GitHub Actions UI.
7. Post-run verification (read-only):
   - `instagram.yml`: `status: published`, `published_at`, `external_id` set;
   - `publish_log.yml`: Instagram event appended;
   - commit `Record first Instagram publish` on `main`;
   - visual check Instagram profile (manual, read-only).

---

## After First Live

Workflow после первой успешной публикации:

| Option | When |
|--------|------|
| Оставить manual-only | workflow остаётся `workflow_dispatch`; dry-run gate предотвратит повтор (`Would publish: 0`) |
| Disable / rename | cleanup commit: e.g. rename to `instagram-live-publish-archived.yml` or add `if: false` guard |
| Remove | отдельный cleanup commit после подтверждения, что metadata записана |

**Future automation** (schedule, multi-pack, environment protection) — **отдельный** implementation plan и approval. Не расширять этот workflow без нового plan.

---

## Tests / Checks (before first workflow run)

После создания workflow YAML (не в этом plan step):

- YAML lint / manual review triggers (`workflow_dispatch` only)
- Confirm no `echo` of secrets in any step
- Confirm dry-run step has no `INSTAGRAM_*` env
- Confirm commit paths are explicit (two files only)
- Confirm `telegram-publish.yml` unchanged in same PR/commit
- Local dry-run on `main` still shows `Would publish: 1` until first live succeeds

Workflow itself is the first real API test — no separate CI Meta API call before run.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Token leak in Actions logs | no echo; publisher sanitizes errors; no `set -x` |
| Duplicate Instagram post | dry-run idempotency gate; publisher skip if `published_at` set |
| Published externally but commit failed | documented stop rule; manual recovery |
| Wrong file committed | allowlist git diff check |
| Accidental schedule added later | forbidden in plan; review on any workflow change |
| Telegram workflow regression | separate file; forbidden touch list |
| Graph API version drift | Meta dashboard check before first run |
| Workflow run while pack not eligible | dry-run gate fails closed |
| Over-broad `git add` | explicit two-file paths only |

---

## Rollback

**До создания workflow:** удалить только этот plan-файл.

**После создания workflow, до first run:** revert/delete `.github/workflows/instagram-live-publish.yml`.

**После successful live:** удаление workflow не откатывает Instagram post. Metadata rollback — отдельная ручная операция.

**При credential incident:** revoke token in Meta; rotate GitHub secret; не коммитить values.

---

## Approval

Status: **waiting for approval**

После approval разрешено:

- создать `.github/workflows/instagram-live-publish.yml`

После approval **не разрешено** без отдельного шага:

- первый *Run workflow* в GitHub Actions
- локальный `--live`
- изменение Telegram workflow/publisher
- recurring automation

Создание этого plan-файла ≠ approval на workflow run.
