# Implementation Plan: Instagram Token Lifecycle and Rotation

## Goal

Определить безопасный operational process для срока жизни, проверки и ротации `INSTAGRAM_ACCESS_TOKEN`, используемого Flexity Instagram publishing через Facebook Graph.

Этот план не разрешает чтение token value, вызовы Meta/Instagram API, запуск `--live`, изменение workflow/code или ротацию credentials без отдельного operational approval.

## Classification

- Project: Flexity.
- Category: `documentation_only` with `research_only` input.
- Area: Instagram publishing operations and credential lifecycle.
- Risk: high, потому что token даёт право на внешнюю публикацию и его утечка или expiry останавливает канал.
- Current branch at planning time: `main`.

## Current Situation

- `INSTAGRAM_ACCESS_TOKEN` хранится как GitHub Actions repository secret.
- Token values нельзя читать, печатать, логировать, передавать в chat или добавлять в git.
- Текущий token уже успешно использован publisher для `graph.facebook.com`.
- Первая публикация имеет `external_id: 18184343005390956`; metadata зафиксирована commit `edd684e493b2f2a0288df94a840a0e2e49f42ca6`.
- Reusable workflow plan находится в main: `dd79f007eaa117cd2b4b125a351a2b00831367a9`.
- Старый token с префиксом `IGAA...` считается скомпрометированным, не должен использоваться и должен быть revoked/invalidated владельцем Meta assets через официальный интерфейс, если это ещё не подтверждено.
- Наличие GitHub Secret подтверждает только имя secret, но не тип, срок действия, scopes или принадлежность token.

## Research Limitation

Официальные Meta Developers pages вернули HTTP `403` при подготовке плана. Перед любой ротацией владелец Meta assets должен вручную сверить текущие правила в официальных Meta tools/docs.

Нельзя предполагать фиксированный срок жизни по префиксу token или факту одной успешной публикации. Token type, expiry и permissions должны быть подтверждены официальным Meta Access Token Debugger/App Dashboard без передачи token в repo, logs или chat.

## Required Meta Verification

Владелец token должен вручную проверить через официальные Meta инструменты:

- token type: short-lived, long-lived либо другой поддерживаемый тип;
- точную expiry date/time и оставшийся срок;
- app ID и Meta App, которой принадлежит token;
- business portfolio, Facebook Page и Instagram Professional account;
- пользователя/системного субъекта, которому выдан token;
- scopes/permissions, включая актуальное право Instagram content publishing;
- App mode, App Review status и роли пользователя;
- соответствие Instagram User ID целевому Flexity account;
- отсутствие использования старого скомпрометированного `IGAA...` token.

Token debugging/checking выполнять только в официальном Meta Access Token Debugger или Meta App Dashboard. Не использовать сторонние token decoders, online paste tools, screenshots с token value, shell history, repository issues или chat.

Результат проверки фиксировать без token value: тип, expiry timestamp, app/account identifiers в допустимой несекретной форме, дата проверки и ответственный.

## Lifecycle Options

### Option A: Manual replacement before expiry

- Владелец вручную получает новый поддерживаемый token до expiry.
- Обновляется только GitHub Secret `INSTAGRAM_ACCESS_TOKEN`.
- Подходит как immediate fallback и для редких manual publications.
- Риск: человеческий фактор и пропущенный expiry.

### Option B: Long-lived token in GitHub Secrets

- Получить long-lived token только через текущий официальный Meta flow для выбранного app/account type.
- Хранить значение только в GitHub Secret.
- Зафиксировать expiry и rotation owner отдельно от token value.
- Это предпочтительный вариант для ближайших 30 дней, если Meta Debugger подтверждает, что такой token официально поддержан для текущего Page-connected publishing flow.
- Long-lived не означает permanent: expiry/revocation всё равно контролируются.

### Option C: Reminder or non-secret expiry monitoring

- Создать calendar reminder/manual checklist без token value.
- Базовые напоминания: за 14 дней и за 7 дней до подтверждённого expiry, плюс контроль в день ротации.
- Будущая автоматизация может проверять только несекретный status/expiry результат через отдельный approved design.
- Не добавлять token echo, scheduled live publish или credential refresh в reusable publish workflow.

### Option D: System user/business token

- Рассматривать только если текущая официальная Meta документация прямо поддерживает его для нужного Instagram publishing flow и ownership model Flexity.
- Требуется отдельный research brief, security review и approval.
- Не реализовывать на основании предположения, forum post или устаревшей инструкции.

## Recommendation for the Next 30 Days

Выбрать сочетание **Option B + Option C**, но только после ручной проверки текущего token:

1. Сегодня определить type, expiry, app/account binding и permissions через Meta Access Token Debugger.
2. Если текущий token уже long-lived и действует больше 30 дней, не ротировать его без необходимости; оставить в GitHub Secret и поставить reminders за 14/7 дней до expiry.
3. Если token short-lived, expiry неизвестен или наступает в пределах 30 дней, вручную получить официально поддерживаемый long-lived token и заменить только GitHub Secret.
4. Option A оставить как documented fallback.
5. Option D и автоматический refresh отложить до отдельного research/approval.

Это минимизирует credential churn и не создаёт автоматизацию вокруг плохо подтверждённого token flow.

## Safety Rules

- Never commit token.
- Never print token, token prefix/suffix, token length or hash.
- Never store token in local files, `.env`, notes/notepad, screenshots, clipboard history exports, tickets or chat.
- Update only GitHub Secret `INSTAGRAM_ACCESS_TOKEN` through an approved trusted UI/process.
- Do not pass token as a command-line argument, where it can enter shell history or process listings.
- Do not include token in workflow outputs, artifacts, cache, error payloads or debug logs.
- Do not use `set -x`, `printenv` or environment dumps in credential-aware steps.
- Keep `INSTAGRAM_USER_ID` separate from access token; changing token does not automatically authorize a different account.
- After rotation run content eligibility dry-run first, without `--live` and without attaching Instagram secrets to the dry-run step.
- Dry-run validates content-pack eligibility only; it does not prove that a new token is valid.
- Any live publish after rotation is allowed only through the separately approved reusable workflow and its manual confirmation/count gates.
- Revoke the old token after the replacement is safely installed and ownership/permissions are confirmed; do not retain fallback plaintext copies.

## Operational Runbook

### 1. Prepare rotation

1. Confirm there is no Instagram workflow run in progress.
2. Record non-secret metadata: current check date, expected expiry, Meta App/account and rotation owner.
3. In official Meta tooling, create/obtain the replacement token under the correct app/business/Page/Instagram account.
4. Verify type, expiry and required permissions in official Meta tooling.
5. Do not paste the token anywhere except the Meta flow and GitHub Secret update form.

### 2. Replace `INSTAGRAM_ACCESS_TOKEN`

Preferred method:

1. Open the GitHub repository.
2. Go to **Settings → Secrets and variables → Actions**.
3. Select `INSTAGRAM_ACCESS_TOKEN` and choose **Update**.
4. Paste the replacement value directly into the GitHub secret form.
5. Save it without exposing the value in screenshots or logs.

Do not delete/recreate unrelated Telegram or Instagram secrets. Do not use a CLI command containing token plaintext.

### 3. Verify secret names only

Safe name-only check:

```bash
gh secret list --repo asemislyamova03-netizen/coreops-platform --json name --jq '.[].name'
```

Expected Instagram names:

- `INSTAGRAM_USER_ID`
- `INSTAGRAM_ACCESS_TOKEN`

This confirms presence by name only. It does not validate value, expiry or permissions.

### 4. Run workflow dry-run without live

Before any post-rotation live run:

- run `python scripts/content/publish_instagram_live.py` without `--live`;
- ensure the dry-run step has no Instagram secrets attached;
- require `Errors: 0`;
- review every eligible pack and expected count;
- do not create a metadata commit when `Would publish: 0`.

For local PowerShell verification, explicitly clear the two Instagram variables in the child/process context before dry-run so the current values are not read:

```powershell
$env:INSTAGRAM_USER_ID = ""
$env:INSTAGRAM_ACCESS_TOKEN = ""
python scripts/content/publish_instagram_live.py
```

Dry-run does not test OAuth validity. The first real use of a rotated token requires an approved content-pack and manual reusable workflow dispatch with matching `confirm_live`/`expected_count`.

### 5. Complete rotation

1. Confirm the new secret name is present in GitHub.
2. Confirm the approved dry-run has `Errors: 0`.
3. Run live only when an approved post exists and the reusable workflow itself has been approved and installed.
4. After confirmed successful use, revoke the superseded token in Meta.
5. Update only non-secret rotation metadata and next reminder dates.

## Incident Handling

### OAuth error 190

- Stop; do not retry live publication automatically.
- Treat token as invalid, expired, revoked or otherwise unusable until Meta confirms the cause.
- Check token status/type/expiry in official Meta tooling.
- Check whether password/security changes, logout, role removal or business/app changes invalidated it.
- Obtain a replacement through the approved Meta flow and update only the GitHub Secret.
- Run dry-run again, then require a new manual approval for live publication.
- If API outcome was ambiguous, verify whether the post exists before any retry.

### Permission errors

- Stop; do not repeatedly regenerate tokens.
- Verify required current content-publishing permissions in official Meta docs/dashboard.
- Verify App Review/live mode, user role, Page access, Instagram account connection and Instagram User ID.
- Confirm token belongs to the expected app/business/Page/account combination.
- Rotate only after the configuration issue is understood.

### Token expiry or imminent expiry

- Pause live workflow dispatches until replacement is installed.
- Obtain and validate the replacement token through official Meta tooling.
- Update only `INSTAGRAM_ACCESS_TOKEN` in GitHub Secrets.
- Run no-secret dry-run and follow the controlled first live use after rotation.
- Revoke old token after successful cutover; never keep plaintext backup copies.

### Suspected compromise

- Revoke the affected token immediately through Meta.
- Disable/avoid Instagram live workflow runs until replacement is installed.
- Review GitHub Actions logs and repository history for exposure without printing the token.
- Rotate the credential and document the incident without recording secret material.
- The old `IGAA...` token must remain revoked and unused.

## Checks and Acceptance Criteria

- Current token type and expiry have been manually confirmed in official Meta tooling.
- Correct app/business/Page/Instagram account binding is documented without secret values.
- Required publishing permissions are confirmed against current official Meta docs.
- Rotation owner and reminder dates are assigned.
- GitHub contains expected secret names without values being read or printed.
- Replacement procedure updates only `INSTAGRAM_ACCESS_TOKEN`.
- Dry-run uses no `--live`, no API calls and no Instagram secret environment.
- Error 190, permission failure, expiry and compromise runbooks are understood.
- No code, workflow or content-pack change is required to adopt the manual 30-day process.

## Documentation Updates Later

After this plan is approved, separate documentation-only changes should:

- add a link from `docs/content/instagram-publishing.md` to this lifecycle plan;
- mention token expiry/revocation risk in reusable workflow documentation;
- link the rotation runbook without duplicating or embedding credentials;
- identify the human rotation owner and non-secret reminder schedule in an approved operations location.

Do not mix these documentation changes with workflow implementation unless separately approved.

## Risks

- Unknown current token type or expiry.
- Token belongs to the wrong Meta App, user, business, Page or Instagram account.
- Required permissions or App Review status change over time.
- Long-lived token is incorrectly treated as permanent.
- Human reminder is missed.
- Rotation breaks publishing because account binding differs.
- Old token remains active after replacement.
- Token leaks through shell history, screenshots, notes, logs or support chat.
- OAuth error occurs after an ambiguous publication result, creating duplicate-post risk.

## Rollback

- Secret rotation rollback must not restore an old compromised or revoked token.
- If a new token is invalid and the previous token is still valid and not compromised, restoring it requires separate explicit approval and official Meta status verification.
- Prefer issuing a corrected replacement over retaining plaintext fallback copies.
- Documentation rollback is deletion/revert of this plan only; it does not modify GitHub Secrets.

## Explicitly Forbidden Now

- No code changes.
- No workflow changes or runs.
- No `--live` execution.
- No Meta or Instagram API calls.
- No secret reads, prints or value checks.
- No content-pack changes.
- No backend, nginx, deploy or Telegram changes.

## Approval

Status: waiting for explicit approval to adopt the manual 30-day lifecycle process and later documentation links.

This plan does not authorize token rotation, live publication, workflow implementation or API access.
