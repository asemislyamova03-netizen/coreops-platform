# Шаблон Instagram content-pack

Instagram-контент хранится рядом с другими материалами ежедневного content-pack:

```text
landing/content/content-packs/YYYY-MM-DD-slug/
  instagram.md
  instagram.yml
```

- `instagram.md` содержит caption для публикации.
- `instagram.yml` содержит тип публикации, статус, расписание и ссылку на media.

## Draft-состояние

Новый Instagram content создаётся как draft:

```yaml
status: "draft"
type: "feed_image"
publish_at: "YYYY-MM-DDT12:00:00+05:00"
published_at: null
external_id: null
media:
  image_url: null
caption_source: "instagram.md"
```

Draft не означает готовность к публикации. Перед approval необходимо добавить caption в `instagram.md`, проверить текст и подготовить доступный media URL.

## Approval-состояние

После human review Instagram content можно перевести в состояние `approved`:

```yaml
status: "approved"
type: "feed_image"
publish_at: "YYYY-MM-DDT12:00:00+05:00"
published_at: null
external_id: null
media:
  image_url: "https://..."
caption_source: "instagram.md"
```

Статус `approved` пока означает «готово к ручной публикации или будущему API publisher», а не фактическую автопубликацию.

## Правила

- Без `media.image_url` Instagram feed post не может быть опубликован автоматически.
- Caption хранится в `instagram.md`; `caption_source` должен ссылаться на этот файл.
- Reels требует `video_url` и будет отдельным `type`, не `feed_image`.
- Instagram API publisher пока не реализован.
- `published_at` и `external_id` не заполняются до фактической публикации.
- Telegram workflow и Telegram publisher не должны читать `instagram.yml`.
- Approval и публикация Instagram не должны менять Telegram statuses или Telegram publication log.

## Checklist перед approval

- [ ] `instagram.md` существует и содержит проверенный caption.
- [ ] Текст не обещает функций Flexity, которых ещё нет.
- [ ] CTA корректный.
- [ ] `type` соответствует media format.
- [ ] Для `feed_image` заполнен `media.image_url`.
- [ ] `publish_at` содержит timezone offset.
- [ ] `published_at` и `external_id` равны `null`.
- [ ] Материал готов к ручной публикации; автоматический Instagram publisher отсутствует.
