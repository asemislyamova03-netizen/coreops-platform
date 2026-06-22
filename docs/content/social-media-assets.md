# Social Media Assets Contract

Этот документ определяет структуру media assets для будущей Instagram automation Flexity. Реальная генерация изображений и видео, deploy assets и Instagram API publishing в этот scope не входят.

## Public URL requirement

Instagram API получает media по URL. Перед live publishing изображение или видео должно быть доступно Meta по публичному HTTP(S) URL.

Локальный путь, например `C:\Users\...\instagram-feed.png` или `landing/www/assets/...`, не является допустимым `image_url` или `video_url`. Путь в репозитории становится пригодным для API только после deploy и проверки публичного URL.

## Структура assets

Базовая структура одного content-pack:

```text
landing/www/assets/social/YYYY-MM-DD-slug/
  instagram-feed.png
  carousel-01.png
  carousel-02.png
  reels-cover.png
  reels-video.mp4
```

Назначение файлов:

- `instagram-feed.png`: одиночное изображение `feed_image`;
- `carousel-01.png`, `carousel-02.png`: последовательные элементы carousel;
- `reels-cover.png`: cover image для Reels, если поддерживается выбранным API flow;
- `reels-video.mp4`: видео для `reels`.

Media assets не должны храниться внутри `backend/**`. Они относятся к публичной статике landing и должны проходить отдельный approved deploy `landing/www/**`.

## URL после deploy

Repository path:

```text
landing/www/assets/social/YYYY-MM-DD-slug/instagram-feed.png
```

Public URL:

[https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/instagram-feed.png](https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/instagram-feed.png)

Наличие файла в Git не подтверждает доступность URL. Перед live publish URL должен отвечать публично и возвращать ожидаемый media content.

## Связь с content-pack

Instagram metadata хранится отдельно от deployable media:

```text
landing/content/content-packs/YYYY-MM-DD-slug/instagram.yml
landing/content/content-packs/YYYY-MM-DD-slug/instagram.md
```

Slug в content-pack и в `assets/social/` должен совпадать, чтобы связь между metadata и media оставалась однозначной.

Пример `instagram.yml` для `feed_image`:

```yaml
status: "draft"
type: "feed_image"
publish_at: "YYYY-MM-DDT12:00:00+05:00"
published_at: null
external_id: null
media:
  image_url: "https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/instagram-feed.png"
caption_source: "instagram.md"
```

## Type-specific media

### Feed image

`feed_image` требует публичный `media.image_url`:

```yaml
media:
  image_url: "https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/instagram-feed.png"
```

### Carousel

`carousel` требует непустой список `media.items`. Каждый элемент должен содержать публичный `image_url` или `video_url`:

```yaml
media:
  items:
    - image_url: "https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/carousel-01.png"
    - image_url: "https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/carousel-02.png"
```

### Reels

`reels` требует публичный `media.video_url`:

```yaml
media:
  video_url: "https://www.flexity.asia/assets/social/YYYY-MM-DD-slug/reels-video.mp4"
```

## Правила

- Локальные filesystem paths нельзя использовать как `image_url` или `video_url`.
- `image_url` должен быть публично доступен до live publish.
- Для Reels нужен публичный `video_url`.
- Для carousel нужен непустой список `media.items`.
- Media files не должны лежать внутри `backend/**`.
- Telegram publisher не должен читать social media assets или `instagram.yml`.
- Instagram dry-run проверяет наличие и HTTP(S)-формат media URL как строки, но не делает HTTP-check доступности.
- Генерация assets, изменение `landing/www/**`, deploy и live Instagram publishing требуют отдельных implementation plans и approvals.

## Readiness checklist

- [ ] Media создана в согласованном формате и размере.
- [ ] Repository path соответствует `YYYY-MM-DD-slug` content-pack.
- [ ] Assets прошли отдельный approved deploy.
- [ ] Public URL доступен без авторизации.
- [ ] URL возвращает ожидаемый image/video content type.
- [ ] `instagram.yml` ссылается на правильный public URL.
- [ ] Instagram dry-run проходит fail-closed validation.
- [ ] Live publish отдельно утверждён.
