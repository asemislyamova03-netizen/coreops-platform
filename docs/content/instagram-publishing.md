# Instagram Publishing

Instagram publishing in Flexity currently supports validation and preview in dry-run mode only. Live publishing and Meta API calls are not implemented.

## Run dry-run

```bash
python scripts/content/publish_instagram.py --dry-run
```

The command scans:

```text
landing/content/content-packs/*/instagram.yml
```

It reads the caption file referenced by `caption_source`, normally `instagram.md`, and does not modify either file.

Running the script without `--dry-run` always fails with:

```text
Instagram live publishing is not implemented yet. Use --dry-run.
```

## Eligibility

A pack is previewed only when:

- `status` is `approved`;
- `published_at` is null;
- `publish_at` is timezone-aware and not later than the current time;
- `caption_source` exists inside the same pack and contains text;
- media requirements for the selected type are satisfied.

Draft, already-published, and future packs are skipped. An approved due pack with malformed metadata or missing media fails closed and makes the command return a non-zero exit code.

## instagram.yml fields

```yaml
status: "approved"
type: "feed_image"
publish_at: "YYYY-MM-DDT12:00:00+05:00"
published_at: null
external_id: null
media:
  image_url: "https://cdn.example.com/post.jpg"
caption_source: "instagram.md"
```

Supported types and required media:

- `feed_image`: public HTTP(S) `media.image_url`;
- `reels`: public HTTP(S) `media.video_url`;
- `carousel`: non-empty `media.items`, where every item contains an HTTP(S) `image_url` or `video_url`.

Without a public image URL, Meta cannot fetch a feed image from the content pack. A local path from a laptop is not a public media URL and is rejected by validation.

## Dry-run output

For every valid eligible pack, the script prints:

- pack name;
- content type;
- caption length;
- media URL or carousel URL list;
- scheduled `publish_at`;
- `would_publish=true`.

Dry-run does not:

- read Instagram tokens, user IDs, or secrets;
- make HTTP requests or Meta API calls;
- create media containers;
- write `published_at` or `external_id`;
- modify content-pack files;
- interact with the Telegram publisher or workflow.

## Live publishing

Live publishing is a separate future stage. It requires current Meta API research, credential storage design, a dedicated implementation plan, test-account verification, and explicit approval before any API call is enabled.
