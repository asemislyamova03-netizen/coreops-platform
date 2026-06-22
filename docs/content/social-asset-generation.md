# Social Asset Generation

Flexity can generate a local 1080x1080 Instagram feed PNG from content-pack metadata. The generator does not publish to Instagram and does not deploy the landing site.

## Dependency

The generator requires Python and Pillow:

```text
Pillow
```

Pillow is intentionally not added to global project requirements in this slice. Use a local environment where Pillow is already available, or install it only after separate dependency approval.

## visual.yml

Create `visual.yml` inside the target content-pack:

```yaml
instagram_feed:
  title: "AI не спасёт бизнес"
  subtitle: "если процесс в хаосе"
  footer: "Flexity • сначала процесс, потом AI"
  output: "landing/www/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png"
```

Required fields:

- `instagram_feed.title`;
- `instagram_feed.subtitle`;
- `instagram_feed.footer`;
- `instagram_feed.output`.

The output must end with `.png` and resolve inside:

```text
landing/www/assets/social/
```

Absolute paths, path traversal, and outputs outside this directory fail closed.

## Run the generator

From the repository root:

```bash
python scripts/content/generate_social_assets.py \
  --pack landing/content/content-packs/2026-06-22-ai-tools-need-process \
  --type instagram-feed
```

The generator creates parent directories when needed and writes an RGB PNG with exact dimensions `1080x1080`.

The MVP layout contains:

- a large wrapped title;
- a wrapped subtitle;
- a footer;
- a restrained background and accent;
- no external images or downloaded assets.

## Relation to instagram.yml

After the generated asset is reviewed and separately deployed, `instagram.yml` can reference its public URL:

```yaml
status: "draft"
type: "feed_image"
media:
  image_url: "https://www.flexity.asia/assets/social/2026-06-22-ai-tools-need-process/instagram-feed.png"
caption_source: "instagram.md"
```

The repository output path and public URL map as follows:

```text
landing/www/assets/social/<slug>/instagram-feed.png
https://www.flexity.asia/assets/social/<slug>/instagram-feed.png
```

Generating the local file does not make the URL public. The asset requires a separate approved landing deploy before any future live Instagram publishing.

## Boundaries

The generator:

- does not call Instagram or Meta APIs;
- does not make HTTP requests;
- does not read credentials or secrets;
- does not publish content;
- does not deploy the site;
- does not change `instagram.yml`, Telegram files, or publication logs;
- does not write outside `landing/www/assets/social/`.
