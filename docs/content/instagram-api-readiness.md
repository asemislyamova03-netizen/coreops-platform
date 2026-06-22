# Instagram API Readiness

Этот документ фиксирует требования для будущей автопубликации Instagram-контента Flexity. Он не является approval на реализацию или live publishing.

## Текущий статус

- Draft template создан: `docs/content/templates/instagram-content-pack-template.md`.
- Instagram API publisher пока не реализован.
- Instagram credentials и secrets не настроены в рамках текущего content flow.
- Telegram workflow и Telegram publisher не должны читать `instagram.yml`.
- Статус Instagram `approved` означает готовность к ручной публикации или будущему API publisher, но не фактическую автопубликацию.

## Требования для будущей автопубликации

Перед разработкой publisher потребуются:

- Instagram Professional account;
- подключение аккаунта к Meta Business и Facebook Page;
- Meta Developer App;
- актуальные permissions для content publishing;
- действующий access token с подходящим сроком жизни;
- IG User ID целевого Instagram account;
- публичный `image_url` для feed posts;
- публичный `video_url` для Reels.

Названия permissions, поддерживаемые media formats, лимиты и token lifecycle необходимо повторно сверить с актуальной официальной документацией Meta перед implementation plan.

## Минимальная структура content-pack

```text
landing/content/content-packs/YYYY-MM-DD-slug/
  instagram.md
  instagram.yml
```

- `instagram.md` хранит caption.
- `instagram.yml` хранит publication state, type, schedule и media URL.

## Контракт instagram.yml

Минимальные поля:

```yaml
status: "draft"
type: "feed_image"
publish_at: "YYYY-MM-DDT12:00:00+05:00"
published_at: null
external_id: null
media:
  image_url: null
  video_url: null
caption_source: "instagram.md"
```

Допустимые значения:

- `status`: `draft`, `approved`, `published`;
- `type`: `feed_image`, `carousel`, `reels`;
- `publish_at`: timezone-aware datetime планируемой публикации;
- `published_at`: null до успешной публикации, затем фактическое время;
- `external_id`: null до успешной публикации, затем Instagram media ID;
- `media.image_url`: публичный URL изображения для feed image или элемента carousel;
- `media.video_url`: публичный URL видео для Reels;
- `caption_source`: `instagram.md`.

Для carousel потребуется отдельное уточнение структуры массива media items до реализации publisher.

## Media requirements

- Без `media.image_url` feed post нельзя публиковать автоматически.
- Без `media.video_url` Reels нельзя публиковать автоматически.
- Локальные файлы с ноутбука Instagram API не примет как media URL.
- Media должна быть доступна Meta по публичному URL во время создания и обработки публикации.
- Формат, размер, длительность, aspect ratio и другие ограничения media должны проверяться до API request.

## Безопасный путь реализации

1. Отдельный research brief по актуальному Meta Instagram API.
2. Отдельный implementation plan с точным API flow, permissions, token storage и rollback.
3. Read-only validator для `instagram.yml` и media requirements.
4. Dry-run publisher без создания media container и без live publish.
5. Тестовый Professional account и тестовый content-pack.
6. Human approval результата dry-run.
7. Live publish включать только после отдельного явного approval.

До реализации live publisher запрещено:

- считать `status: approved` фактом публикации;
- заполнять `published_at` или `external_id` без подтверждённого результата API;
- передавать credentials в content-pack или commit;
- расширять Telegram workflow для чтения `instagram.yml`;
- публиковать Instagram content автоматически.
