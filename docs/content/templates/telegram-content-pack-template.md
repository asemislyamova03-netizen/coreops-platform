# Шаблон ежедневного Telegram content-pack

Каждый Telegram-пост хранится в отдельной папке:

```text
landing/content/content-packs/YYYY-MM-DD-slug/
  pack.yml
  telegram.md
  publish_log.yml
```

- `pack.yml` содержит метаданные, статусы и время публикации.
- `telegram.md` содержит точный текст сообщения для Telegram.
- `publish_log.yml` хранит результат работы publisher.

## Draft-состояние

Новый pack всегда создаётся как draft:

```yaml
date: "YYYY-MM-DD"
topic: "..."
slug: "..."
status: "draft"

publish:
  telegram:
    enabled: true
    status: "draft"
    publish_at: "YYYY-MM-DDT10:00:00+05:00"
    published_at: null
    external_id: null
```

Начальный `publish_log.yml`:

```yaml
events: []
```

Draft никогда не публикуется:

- если верхнеуровневый `status` остаётся `draft`, pack не будет опубликован;
- если `publish.telegram.status` остаётся `draft`, pack не будет опубликован;
- для публикации нужны оба статуса `approved`.

## Approval-состояние

После human review переведите оба статуса в `approved`:

```yaml
date: "YYYY-MM-DD"
topic: "..."
slug: "..."
status: "approved"

publish:
  telegram:
    enabled: true
    status: "approved"
    publish_at: "YYYY-MM-DDT10:00:00+05:00"
    published_at: null
    external_id: null
```

`published_at` и `external_id` вручную не заполнять. После успешной отправки их обновляет publisher.

## Checklist перед approval

- [ ] `telegram.md` существует и не пустой.
- [ ] Текст не обещает функций Flexity, которых ещё нет.
- [ ] CTA корректный и ведёт на существующий маршрут или контакт.
- [ ] `publish_at` содержит timezone offset и указан в будущем для расписания либо в прошлом для ручного запуска.
- [ ] Верхнеуровневый `status` установлен в `approved`.
- [ ] `publish.telegram.enabled` установлен в `true`.
- [ ] `publish.telegram.status` установлен в `approved`.
- [ ] `published_at` и `external_id` равны `null`.
- [ ] Выполнен dry-run eligible check без Telegram API и secrets.
- [ ] Dry-run показывает только нужный pack.

Ожидаемый результат непосредственно перед публикацией:

```text
ELIGIBLE_COUNT=1
ELIGIBLE=YYYY-MM-DD-slug
```

Если eligible packs больше одного, workflow запускать нельзя: сначала отключите или верните в draft лишние packs.

## Проверка после публикации

После успешной публикации проверьте:

- `publish.telegram.published_at` заполнен;
- `publish.telegram.external_id` заполнен;
- в `publish_log.yml` есть событие `status: published`;
- повторный dry-run не считает опубликованный pack eligible.

Ожидаемый результат после публикации:

```text
ELIGIBLE_COUNT=0
```
