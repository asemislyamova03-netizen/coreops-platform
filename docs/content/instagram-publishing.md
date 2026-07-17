# Instagram Publishing

**Production live publishing is NOT supported yet.**

Flexity has two Instagram publisher scripts for content packs:

- `scripts/content/publish_instagram.py` — schema validator and preview for `feed_image`, `carousel`, and `reels`;
- `scripts/content/publish_instagram_live.py` — dry-run-first publisher for approved `feed_image` / `carousel` / `reels` packs. Live paths remain non-production.

## Schema dry-run

```bash
python scripts/content/publish_instagram.py --dry-run
```

The command scans:

```text
landing/content/content-packs/*/instagram.yml
```

It reads the caption file referenced by `caption_source`, normally `instagram.md`, and does not modify any file.

Running the schema script without `--dry-run` always fails with:

```text
Instagram live publishing is not implemented yet. Use --dry-run.
```

## Live publisher dry-run (default)

```bash
python scripts/content/publish_instagram_live.py
```

Default mode is dry-run. It scans the same content packs, reads each pack's top-level `pack.yml`, and applies eligibility gates.

Dry-run does not:

- require Instagram secrets;
- call Meta / external HTTP APIs;
- write `instagram.yml`, `publish_log.yml`, or any other file.

For every valid eligible pack, dry-run prints pack name, `type`, caption length, media URL(s), `publish_at`, and `would_publish=true`.

## Live publisher (`--live`) — non-production

```bash
python scripts/content/publish_instagram_live.py --live
```

**Production live publishing is NOT supported yet.** `--live` is an ops/experimental path only.

Required environment variables for any `--live` attempt:

- `INSTAGRAM_USER_ID`
- `INSTAGRAM_ACCESS_TOKEN`

Secrets are read only from the environment. Tokens must not appear in stdout/stderr or logs. Provider-like fragments (`Bearer …`, `Authorization: …`, `access_token=`) are redacted via `sanitize_error`.

Live mode may write only:

- the current pack `instagram.yml`;
- the current pack `publish_log.yml`.

It does not modify `pack.yml`, `instagram.md`, Telegram files, or workflow artifacts.

### Reels live — fail-closed experimental gate

Instagram **Reels** live publish is unsafe without status polling and stronger idempotency. Default is fail-closed:

```bash
# Blocked:
python scripts/content/publish_instagram_live.py --live
# (eligible reels pack → ERROR, no API call)

# Explicit experimental unlock only (NOT for production):
python scripts/content/publish_instagram_live.py --live --allow-experimental-live
# or:
FLEXITY_ALLOW_EXPERIMENTAL_REELS_LIVE=1 python scripts/content/publish_instagram_live.py --live
```

`feed_image` / `carousel` `--live` still require secrets and remain non-production; they do not use the Reels experimental env, but must not be treated as production publishing.

### Meta API flow (current script)

1. Create media container: `POST /{INSTAGRAM_USER_ID}/media`.
2. Publish media container: `POST /{INSTAGRAM_USER_ID}/media_publish` with `creation_id`.
3. After confirmed API success, write `published_at`, `external_id`, `status: published` and append `publish_log.yml`.

On API failure, the script appends a redacted error event and does not mark the pack published.

## Eligibility gates

### Skip (exit 0, no API)

- top-level `pack.yml status` is not `approved`;
- `instagram.yml status` is not `approved`;
- `published_at` is already set;
- `external_id` is already set;
- `publish_at` is in the future.

### Fail closed (non-zero exit, no API)

- invalid `publish_at` / media / caption rules;
- in `--live` mode: missing `INSTAGRAM_USER_ID` or `INSTAGRAM_ACCESS_TOKEN`;
- in `--live` mode for `type: reels` without experimental unlock.

## Follow-ups (documented, not implemented here)

- **Reels status poll** after container create (wait for Meta processing before publish);
- **atomic idempotency** beyond soft YAML `published_at` / `external_id` skip (tenant-safe keys in M8-D core).

## First real publish gate

Implementation of these scripts does **not** approve any real Instagram publication.

Before any real Meta API publish:

1. Run dry-run and confirm the expected eligible pack list.
2. Review caption, media URL(s), and target account manually.
3. Verify Meta permissions, token scope/expiry, and Graph API version.
4. Obtain **separate explicit approval** for the first Meta API publish.

## GitHub Actions

No Instagram workflow is included in this hardening slice. A manually triggered workflow with protected secrets stays deferred.

## Relationship to Telegram / TikTok

The Instagram live publisher does not read Telegram or TikTok metadata and does not modify those publishers.
