# Content Factory

Flexity Content Factory — это набор согласованных content-pack контрактов, генераторов, publisher scripts и GitHub Actions workflows для публичного маркетингового контента. Контент живёт в `landing/content/**`; deployable media — в `landing/www/**`.

## Operational channels

Сейчас в эксплуатации:

| Channel | Contract | Publisher / generator | Status |
|---------|----------|----------------------|--------|
| Telegram | `pack.yml`, `telegram.md`, `publish_log.yml` | `scripts/content/publish_telegram.py`, `.github/workflows/telegram-publish.yml` | operational |
| Instagram | `instagram.yml`, `instagram.md` | `scripts/content/publish_instagram.py`, `publish_instagram_live.py`, `.github/workflows/instagram-publish.yml` | operational |
| Insights (static site) | `landing/content/articles/*.md` | `scripts/content/generate_insights.py` | operational |

Каждый operational channel имеет отдельный approval flow, отдельные secrets (где нужно) и не должен читать metadata другого channel без явного плана.

Документация по operational channels:

- [Telegram Publishing](../telegram-publishing.md)
- [Instagram Publishing](instagram-publishing.md)
- [Insights Publishing](insights-publishing.md)
- [Telegram content-pack template](templates/telegram-content-pack-template.md)
- [Instagram content-pack template](templates/instagram-content-pack-template.md)
- [Social media assets contract](social-media-assets.md)

## Planned future channel: TikTok

TikTok добавлен в planning как **будущий** channel. Аккаунт TikTok ещё не создан.

TikTok в Flexity проектируется как **script/video-first** channel:

- основной артефакт — короткое вертикальное видео и сценарий (`video_script`);
- caption и hashtags — вторичные поля для публикации;
- это **не** image-post channel вроде Instagram `feed_image`.

Предлагаемый будущий content-pack контракт описан в [TikTok content-pack template](templates/tiktok-content-pack-template.md). Пример структуры:

```text
landing/content/content-packs/YYYY-MM-DD-slug/
  tiktok.yml
  tiktok_script.md
  tiktok.md

landing/www/assets/social/YYYY-MM-DD-slug/
  tiktok.mp4
```

Поля `tiktok.yml` (draft proposal only):

- `status`: `draft` | `approved` | `published`
- `video_script` (или `video_script_source` → `tiktok_script.md`)
- `caption` (или `caption_source` → `tiktok.md`)
- `hashtags`
- `media.video_url` — публичный URL после deploy (аналог Instagram Reels)
- `publish_at`, `published_at`, `external_id`

## TikTok: explicit out of scope (now)

Сейчас **не делаем**:

- TikTok API integration;
- TikTok publisher script;
- GitHub Actions workflow для TikTok;
- GitHub Secrets для TikTok;
- live publishing в TikTok;
- генерацию или commit реальных `.mp4` файлов;
- изменения backend, Flexity tenants или production config.

Реализация TikTok channel допустима **только после**:

1. создания и утверждения TikTok account;
2. согласования format spec (длительность, aspect ratio, safe zones, cover frame);
3. отдельного approved implementation plan (readiness, API choice, secrets, workflow, first-live checklist).

До этого этапа TikTok существует только в documentation и future content-pack contract.

## Channel isolation rules

- Telegram publisher не читает `instagram.yml`, `tiktok.yml` или article markdown.
- Instagram publisher не читает `tiktok.yml` или Telegram-only fields.
- Insights generator не читает social channel metadata.
- Будущий TikTok publisher (когда появится) не должен менять Telegram или Instagram statuses без отдельного плана.

## Related docs

- [Social asset generation](social-asset-generation.md) — локальная генерация Instagram feed PNG (operational)
- [Instagram API readiness](instagram-api-readiness.md) — Meta credentials checklist (operational)
