# Implementation Plan: Instagram Meta API Readiness

## Goal

Подготовить безопасный путь к будущей live-публикации Instagram feed posts из Flexity content-packs через Meta Instagram API.

Этот план не разрешает реализацию live publisher, вызовы Meta/Instagram API, создание live workflow или изменение статусов content-pack.

## Classification

- Project: Flexity.
- Category: `documentation_only` with `research_only` input.
- Architecture area: content automation integration, отдельно от Flexity backend/CoreOps.
- Risk: medium/high for future implementation because publication is externally visible and uses privileged credentials.
- Current branch at planning time: `main`.

## Current State

- Instagram dry-run publisher существует в `scripts/content/publish_instagram.py` и не выполняет HTTP/API requests или запись в content-packs.
- Live publishing не реализован.
- Feed image публично доступен по адресу:

  `https://www.flexity.asia/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png`

- Последняя проверка media URL: HTTP `200`, `Content-Type: image/png`, `Content-Length: 34985`.
- `landing/content/content-packs/2026-06-22-ai-tools-need-process/instagram.yml` остаётся в состоянии `status: "draft"`, `published_at: null`, `external_id: null`.
- Существующие Telegram publisher и workflow не должны читать Instagram metadata или credentials.

## Research Limitation

Официальные страницы Meta Developers вернули HTTP `403` при подготовке плана. Поэтому перед реализацией необходимо повторно проверить в актуальной официальной документации и Meta App Dashboard:

- выбранный authentication flow;
- точные permission names и необходимость App Review;
- поддерживаемую Graph API version;
- token type, срок действия, refresh/exchange procedure;
- media format, size, aspect ratio и publishing limits;
- container status polling и error model.

Для первой реализации планируется Page-connected flow через Instagram Professional account и Facebook Page. Нельзя смешивать его с другим Instagram Login flow без отдельного решения.

## One-Time Meta Setup

До реализации live publisher владелец Meta assets должен вручную:

1. Перевести целевой Instagram account в Professional account, если это ещё не сделано.
2. Связать Instagram Professional account с Facebook Page.
3. Убедиться, что пользователь Meta, от имени которого выпускается token, имеет право создавать контент на connected Page и управлять связанным Instagram account.
4. Создать Meta Developer App в подходящем business portfolio/account.
5. Подключить к App требуемый Instagram API product/use case для content publishing.
6. Настроить App roles, development/live mode и App Review, если он требуется выбранным permissions и типом пользователей.
7. Получить и проверить Instagram User ID целевого Professional account.
8. Получить access token с актуальными правами на чтение связанного account/Page и публикацию Instagram content.
9. Зафиксировать владельца token, срок действия, процедуру rotation/revocation и ответственного за восстановление доступа.

Точные permissions нельзя считать утверждёнными этим планом. Перед implementation plan их нужно выписать из текущей официальной документации Meta; ожидаемая capability включает Instagram basic/account access и content publishing permission.

## GitHub Secrets

Минимально ожидаются:

- `INSTAGRAM_USER_ID`: ID целевого Instagram Professional account.
- `INSTAGRAM_ACCESS_TOKEN`: access token с правом публикации для связанного account/Page.

В зависимости от утверждённого token lifecycle могут понадобиться:

- `META_APP_ID`: идентификатор Meta App.
- `META_APP_SECRET`: secret Meta App, только если runtime действительно выполняет server-side token exchange/refresh.

Правила хранения:

- добавлять значения только через GitHub repository/environment secrets;
- не хранить токены в git, content-packs, workflow YAML, logs, artifacts или документации;
- ограничить secrets отдельным protected environment для Instagram live publishing;
- запретить вывод credentials, request headers и полных API responses, содержащих token;
- `META_APP_SECRET` не добавлять, пока утверждённая реализация не докажет его необходимость.

## Future Publish Flow

Live flow будет отдельной реализацией после нового approval:

1. Найти content-pack с `pack.yml`, `instagram.yml` и `instagram.md`.
2. Проверить top-level `pack.yml status: "approved"`.
3. Проверить `instagram.yml status: "approved"`, due `publish_at`, `published_at: null` и `external_id: null`.
4. Прочитать caption из `instagram.md` через безопасный `caption_source` внутри pack.
5. Проверить тип публикации и соответствующий media contract.
6. Проверить, что `media.image_url` является публичным HTTPS URL и возвращает допустимый image response.
7. Создать media container для Instagram User ID, передав `image_url` и caption.
8. Дождаться готовности container, если это требуется текущим Meta flow.
9. Опубликовать media container.
10. Только после подтверждённого успешного publish атомарно записать:
    - `instagram.yml published_at`;
    - `instagram.yml external_id` с опубликованным Instagram media ID;
    - `instagram.yml status: "published"`;
    - channel-specific event `status: published` в `publish_log.yml`.
11. Никогда не повторять публикацию, если `published_at` уже заполнен или зафиксирован успешный external ID.

Retry после неоднозначной API/network ошибки должен сначала проверять состояние ранее созданного container/publication, а не безусловно создавать новый post.

## Safety Gates

Live publication разрешена только при одновременном выполнении всех условий:

- top-level `pack.yml status` равен `approved`;
- `instagram.yml status` равен `approved`;
- `publish_at` timezone-aware и уже наступил;
- `published_at` равен `null`;
- `external_id` равен `null`;
- `caption_source` находится внутри pack и caption не пустой;
- для `feed_image` указан абсолютный `https://` URL в `media.image_url`;
- media URL публично доступен Meta без login, cookies и private network access;
- media response и format проходят утверждённую validation;
- обязательные secrets присутствуют, но не выводятся;
- execution mode явно live и защищён отдельным human approval/environment gate;
- dry-run mode никогда не создаёт container и не публикует media.

Fail closed:

- нет любого обязательного статуса или поля: не публиковать;
- secrets отсутствуют или invalid: не публиковать;
- media URL не HTTPS, недоступен или возвращает неподходящий Content-Type: не публиковать;
- container не готов или API result неоднозначен: не заполнять `published_at`, не повторять публикацию автоматически;
- уже заполнен `published_at` или `external_id`: не публиковать повторно.

## Proposed Implementation Scope

Точный implementation plan будет создан отдельно после завершения Meta setup и повторной проверки официальной документации. Ожидаемый минимальный scope:

- отдельный Instagram live publisher или изолированный live mode в Instagram publisher;
- unit tests для eligibility, media validation, API response handling и idempotency;
- mock/fake HTTP tests без реальных Meta calls;
- отдельный manually triggered workflow с protected environment и concurrency guard;
- документация credential rotation и controlled first publish.

Live workflow нельзя объединять с Telegram workflow.

## Files Not to Touch Now

- `landing/content/content-packs/**`, включая `instagram.yml` текущего pack.
- `scripts/content/publish_instagram.py`.
- `scripts/content/publish_telegram.py`.
- `.github/workflows/**`.
- `backend/**`, FastAPI и CoreOps.
- `landing/www/**`, `/insights`, nginx и deploy scripts.
- любые credential, secret или local environment files.

## Checks Before Implementation Approval

- Instagram account подтверждён как Professional.
- Connected Facebook Page подтверждена.
- Meta user/token owner имеет content creation access к Page и Instagram account.
- Meta Developer App создана и настроена.
- Instagram User ID проверен на тестовом read-only запросе только после отдельного API approval.
- Permission list и App Review status сверены с текущими официальными Meta docs.
- Token lifecycle и GitHub protected environment утверждены.
- Public media URL повторно проверен на HTTP `200`, `Content-Type: image/png` и доступ без authentication.
- Dry-run показывает ровно один ожидаемый pack после будущего approval обоих статусов.
- Тесты подтверждают idempotency и fail-closed behavior.

## First Live Publication Gate

Первая live-публикация должна быть отдельной контролируемой операцией:

1. Отдельный implementation plan и review кода.
2. Test-account/API verification без публикации либо Meta-provided test flow.
3. Human review caption, image и целевого account.
4. Dry-run с ожидаемым одним eligible pack.
5. Отдельное явное approval непосредственно на первый Meta API publish.
6. После публикации проверка external ID, public post и `publish_log.yml`.

Approval этого readiness plan не является approval на первый live publish.

## Risks

- Expired, revoked or incorrectly scoped token.
- Token связан не с тем пользователем, Page или Instagram account.
- Permission/App Review requirements изменились в новой Graph API version.
- Duplicate post при retry после timeout или частичного API success.
- Public media URL доступен браузеру, но недоступен Meta crawler либо имеет неподдерживаемый format.
- Утечка token через logs, command output, artifacts или committed files.
- Ошибочная публикация draft content из-за проверки только channel-level status.

## Rollback

- До live implementation rollback состоит в удалении только этого plan-файла.
- После будущей публикации локальное изменение metadata не удаляет Instagram post. Удаление внешней публикации является отдельной ручной операцией с отдельным approval.
- При credential incident token нужно revoke/rotate в Meta и обновить только GitHub secret; credentials нельзя исправлять через commit.

## Approval

- Readiness plan: создан по текущему запросу.
- Live publisher, live workflow, secrets configuration и API calls: не реализованы и не одобрены.
- Status текущего `instagram.yml`: оставить `draft`.
- Следующий безопасный шаг: выполнить одноразовый Meta setup и повторно сверить официальные docs, затем подготовить отдельный implementation plan.
