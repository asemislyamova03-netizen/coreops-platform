# Instagram Publishing

Flexity supports two Instagram publisher scripts for content packs:

- `scripts/content/publish_instagram.py` — schema validator and preview for `feed_image`, `carousel`, and `reels`;
- `scripts/content/publish_instagram_live.py` — live-oriented publisher MVP for approved `feed_image` posts only.

## Schema dry-run

```bash
python scripts/content/publish_instagram.py --dry-run
```

The command scans:

```text
landing/content/content-packs/*/instagram.yml
```

It reads the caption file referenced by `caption_source`, normally `instagram.md`, and does not modify any file.

Running the script without `--dry-run` always fails with:

```text
Instagram live publishing is not implemented yet. Use --dry-run.
```

## Live publisher dry-run (default)

```bash
python scripts/content/publish_instagram_live.py
```

Default mode is dry-run. It scans the same content packs, but also reads each pack's top-level `pack.yml` and applies live MVP gates.

Dry-run does not:

- require Instagram secrets;
- call Meta API;
- write `instagram.yml`, `publish_log.yml`, or any other file.

For every valid eligible pack, dry-run prints:

- pack name;
- `type=feed_image`;
- caption length;
- `image_url` (HTTPS only);
- scheduled `publish_at`;
- `would_publish=true`.

## Live publisher (`--live`)

```bash
python scripts/content/publish_instagram_live.py --live
```

Live mode is enabled only with the explicit `--live` flag.

Required environment variables:

- `INSTAGRAM_USER_ID`
- `INSTAGRAM_ACCESS_TOKEN`

Secrets are read only from the environment. The script never prints the token and never writes credentials to files or logs. If either secret is missing, the command fails closed before any API call.

Live mode may write only:

- the current pack `instagram.yml`;
- the current pack `publish_log.yml`.

It does not modify `pack.yml`, `instagram.md`, Telegram files, or workflow artifacts.

### Meta API flow (feed image MVP)

1. Create media container: `POST /{INSTAGRAM_USER_ID}/media` with `image_url` and caption.
2. Publish media container: `POST /{INSTAGRAM_USER_ID}/media_publish` with `creation_id`.
3. After confirmed API success, write:
   - `instagram.yml`: `published_at`, `external_id`, `status: published`;
   - `publish_log.yml`: append `channel: instagram`, `status: published`, `external_id`.

On API failure, the script appends an error event to `publish_log.yml` and does not set `published_at`, `external_id`, or `status: published`.

Before the first real `--live` run, verify exact Meta permissions, App Review status, and Graph API version in the Meta App Dashboard. The script currently uses Graph API version `v21.0` as a placeholder constant and that value must be confirmed against the dashboard before production use.

## Eligibility gates

A pack is considered for live publisher dry-run or `--live` only when all gates pass.

### Skip (exit 0, no API)

- top-level `pack.yml status` is not `approved`;
- `instagram.yml status` is not `approved`;
- `published_at` is already set;
- `external_id` is already set;
- `publish_at` is in the future.

### Fail closed (non-zero exit, no API)

- `publish_at` is missing or has no timezone;
- `type` is not `feed_image` (Reels and carousel are future scope);
- `media.image_url` is missing or does not start with `https://`;
- `caption_source` is missing, escapes the pack directory, points to a missing file, or is not `instagram.md`;
- caption file is empty;
- in `--live` mode: `INSTAGRAM_USER_ID` or `INSTAGRAM_ACCESS_TOKEN` is missing.

Republish protection: if `published_at` or `external_id` is already set, the pack is skipped and API is never called.

## instagram.yml fields (live MVP)

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

Live publisher MVP supports only:

- `type: feed_image`;
- `media.image_url` as HTTPS public URL;
- `caption_source: instagram.md`.

The schema dry-run script still validates `reels` and `carousel` for future work, but the live publisher rejects them.

Without a public HTTPS image URL, Meta cannot fetch a feed image from the content pack.

## First live publish gate

Implementation of the live publisher does **not** approve the first real Instagram publication.

Before the first `--live` run with real credentials:

1. Run both dry-run commands and confirm the expected eligible pack list.
2. Review caption, image URL, and target Instagram account manually.
3. Verify Meta permissions, token scope/expiry, and Graph API version in the Meta App Dashboard.
4. Obtain **separate explicit approval** for the first Meta API publish.
5. After publish, verify the public post, `external_id`, and `publish_log.yml`.

## GitHub Actions

No Instagram workflow is included yet. A manually triggered workflow with protected secrets will be added only after local/manual verification of the live publisher.

## Relationship to Telegram

The Instagram live publisher does not read Telegram metadata and does not modify the Telegram publisher or workflow.
