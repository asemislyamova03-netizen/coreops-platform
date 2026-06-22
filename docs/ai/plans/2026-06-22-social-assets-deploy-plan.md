# Implementation Plan: Social Assets Deploy

## Goal

Сделать один Instagram feed asset публично доступным по URL:

`https://www.flexity.asia/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png`

Источник в репозитории:

`landing/www/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png`

Целевой путь на сервере:

`/var/www/flexity-landing/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png`

Этот документ является только диагностикой и планом. Он не разрешает deploy или подключение к серверу.

## Classification

- Task class: `documentation_only` / deploy planning.
- Project: Flexity public landing.
- Runtime impact после отдельного approval: только статический PNG в уже настроенном document root.

## Current State

- `landing/README.md` указывает mapping `landing/www/` → `/var/www/flexity-landing/` и содержит команду полной выкладки landing через `tar | ssh`.
- `deploy/console-and-landing.md` подтверждает, что `www.flexity.asia` является статическим landing, его nginx root — `/var/www/flexity-landing`, а общий deploy описан через `rsync` всего `landing/www/`.
- `deploy/flexity-asia-nginx.md` отделяет landing от CoreOps API и направляет к `deploy/console-and-landing.md`.
- Отдельного deploy script для landing или social assets в репозитории нет.
- `deploy/update.sh` для этой задачи не подходит: он выполняет `git pull`, backend pre-deploy checks, restart `coreops.service` и health checks FastAPI на порту 8005. Social asset является статическим файлом и не требует этих действий.
- Полная команда из `landing/README.md` удаляет и заново создаёт весь `/var/www/flexity-landing`; для одного asset её использовать нельзя.
- Общая команда `rsync --delete landing/www/ ...` из deploy-документации также слишком широкая для этой задачи.

## Scope

### Files to modify now

- `docs/ai/plans/2026-06-22-social-assets-deploy-plan.md`

### Future deploy scope, only after separate approval

- Local source: `landing/www/assets/social/2026-06-22-ai-tools-need-process/`
- Remote destination: `/var/www/flexity-landing/assets/social/2026-06-22-ai-tools-need-process/`
- Expected transferred file: `instagram-feed.png` only.

### Forbidden zones

- `backend/**`, FastAPI and CoreOps services.
- `platform-console/**`.
- nginx configuration and reload/restart.
- systemd.
- `/insights` and other landing files.
- Telegram workflow and Telegram publisher.
- Instagram publisher and live Instagram/Meta API.
- deploy scripts, credentials and secrets.

## Implementation Steps

All server commands below are proposals for a later approved deploy. Do not run them during planning.

1. Confirm the local source is tracked on the intended commit and is a valid `1080x1080` PNG.
2. Confirm the deployment operator and SSH target from the approved production runbook. Do not put credentials in commands or documentation.
3. Ensure the exact remote directory exists, without changing nginx:

   ```bash
   ssh flexity 'mkdir -p /var/www/flexity-landing/assets/social/2026-06-22-ai-tools-need-process'
   ```

4. Preview the exact transfer. Do not use `--delete`:

   ```bash
   rsync -avnc --checksum --itemize-changes \
     landing/www/assets/social/2026-06-22-ai-tools-need-process/ \
     flexity:/var/www/flexity-landing/assets/social/2026-06-22-ai-tools-need-process/
   ```

5. Proceed only if the dry-run lists `instagram-feed.png` and no other file. Obtain separate explicit deploy approval.
6. After approval, execute the same scoped transfer without `-n`:

   ```bash
   rsync -avc --checksum --itemize-changes \
     landing/www/assets/social/2026-06-22-ai-tools-need-process/ \
     flexity:/var/www/flexity-landing/assets/social/2026-06-22-ai-tools-need-process/
   ```

7. Do not run `deploy/update.sh`, restart CoreOps, reload nginx, run migrations, rebuild the landing, or deploy other directories.

## Checks

### Pre-deploy

- Local file exists at the exact source path.
- PNG dimensions are `1080x1080` and format is PNG.
- Git commit containing the asset is known.
- `rsync --dry-run` reports only the expected asset.
- Transfer command contains neither `--delete` nor a broader source such as `landing/www/`.

### Post-deploy

Run from a machine with public network access:

```bash
curl -I https://www.flexity.asia/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png
```

Expected result:

- HTTP `200`.
- `Content-Type: image/png`.
- No redirect to login, admin or API routes.

Optionally download the public response to a temporary file and compare its SHA-256 with the repository PNG. This check must not overwrite repository files.

## Risks

- A broad source path or `--delete` could modify unrelated landing files.
- An incorrect remote root would publish the file at the wrong URL or overwrite unrelated content.
- Existing remote file with the same name could be overwritten.
- File permissions could produce HTTP `403` even when the path is correct.
- CDN or browser caching could temporarily return an older object.
- Running `deploy/update.sh` would create unrelated backend/service impact.

Mitigation: exact pack directory, dry-run first, no `--delete`, checksum comparison, and separate approval immediately before live transfer.

## Rollback

If the asset is wrong and no previous file existed, remove only this exact remote PNG after separate rollback approval:

`/var/www/flexity-landing/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png`

If an older file existed, restore its saved copy to the same exact path. Do not roll back or replace the full landing tree, and do not change nginx or backend services.

## Approval

- Plan creation: approved by the current request.
- SSH, directory creation, rsync, public post-deploy check and rollback: not executed.
- Live deploy requires a separate explicit approval after review of this plan and the `rsync --dry-run` command.
