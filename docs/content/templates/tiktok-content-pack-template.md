# Шаблон TikTok content-pack (planned future)

> **Status: documentation only.** Этот контракт не реализован в коде. TikTok account, API, workflow, secrets и live publishing отсутствуют.

TikTok — **script/video-first** channel. Публикация предполагает готовое короткое видео и сценарий, а не статичный image post.

## Структура content-pack

TikTok metadata хранится рядом с другими материалами ежедневного content-pack:

```text
landing/content/content-packs/YYYY-MM-DD-slug/
  tiktok.yml
  tiktok_script.md
  tiktok.md
```

Deployable video asset (после отдельного approved deploy):

```text
landing/www/assets/social/YYYY-MM-DD-slug/
  tiktok.mp4
```

- `tiktok_script.md` — полный `video_script` (сцена, текст на экране, voiceover, таймкоды).
- `tiktok.md` — `caption` для публикации в TikTok.
- `tiktok.yml` — статус, расписание, hashtags, ссылки на script/caption и media URL.

Slug в content-pack и в `assets/social/` должен совпадать.

## Draft-состояние

Новый TikTok content создаётся как draft:

```yaml
status: "draft"
publish_at: "YYYY-MM-DDT12:00:00+05:00"
published_at: null
external_id: null
video_script_source: "tiktok_script.md"
caption_source: "tiktok.md"
hashtags:
  - flexity
  - erp
media:
  video_url: null
```

Draft не означает готовность к публикации. Перед approval нужны проверенный script, caption, hashtags и готовый `tiktok.mp4` с публичным URL после deploy.

## Approval-состояние

После human review:

```yaml
status: "approved"
publish_at: "YYYY-MM-DDT12:00:00+05:00"
published_at: null
external_id: null
video_script_source: "tiktok_script.md"
caption_source: "tiktok.md"
hashtags:
  - flexity
  - erp
  - бизнес
media:
  video_url: "https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/tiktok.mp4"
```

`status: approved` означает «готово к будущему publisher», а не факт публикации в TikTok.

## Published-состояние

После будущей live-публикации (не реализовано сейчас):

```yaml
status: "published"
publish_at: "YYYY-MM-DDT12:00:00+05:00"
published_at: "YYYY-MM-DDT12:05:00+05:00"
external_id: "..."
video_script_source: "tiktok_script.md"
caption_source: "tiktok.md"
hashtags:
  - flexity
  - erp
  - бизнес
media:
  video_url: "https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/tiktok.mp4"
```

`published_at` и `external_id` заполняет только будущий approved publisher после успешной публикации.

## Поля контракта

| Field | Location | Purpose |
|-------|----------|---------|
| `video_script` | `tiktok_script.md` via `video_script_source` | Сценарий и структура ролика |
| `caption` | `tiktok.md` via `caption_source` | Текст поста в TikTok |
| `hashtags` | `tiktok.yml` | Список hashtags без `#` prefix |
| `status` | `tiktok.yml` | `draft`, `approved`, `published` |
| `media.video_url` | `tiktok.yml` | Публичный HTTPS URL на `tiktok.mp4` |
| `publish_at` | `tiktok.yml` | Плановое время (с timezone offset) |
| `published_at` | `tiktok.yml` | Фактическое время публикации |
| `external_id` | `tiktok.yml` | ID поста в TikTok API (future) |

## Правила

- TikTok — video-first: без `tiktok.mp4` и публичного `media.video_url` автопубликация невозможна.
- Image-only posts (как Instagram `feed_image`) не являются целевым форматом TikTok channel.
- Локальные filesystem paths нельзя использовать как `video_url`.
- Media files не должны лежать внутри `backend/**`.
- Telegram и Instagram publishers не должны читать `tiktok.yml`.
- Approval TikTok не должен менять Telegram или Instagram statuses.

## Explicit out of scope (now)

- нет TikTok API integration;
- нет TikTok publisher script;
- нет TikTok GitHub Actions workflow;
- нет GitHub Secrets для TikTok;
- нет live publishing;
- нет автогенерации `.mp4` в репозитории.

Реализация — только после account setup, format spec и отдельного approved implementation plan.

## Checklist перед будущим approval

- [ ] `tiktok_script.md` существует и описывает полный ролик.
- [ ] `tiktok.md` содержит проверенный caption.
- [ ] `hashtags` согласованы с brand voice.
- [ ] `tiktok.mp4` создан в согласованном vertical format.
- [ ] Asset задеплоен; `media.video_url` публично доступен.
- [ ] Текст не обещает функций Flexity, которых ещё нет.
- [ ] `published_at` и `external_id` равны `null` до фактической публикации.
