# TikTok Publishing (prep / dry-run)

**Production live publishing is NOT supported yet.**

`scripts/content/publish_tiktok_live.py` is an M8-D prep script. Default mode is dry-run only.

## Dry-run (default, safe)

```bash
python scripts/content/publish_tiktok_live.py
```

Dry-run:

- does **not** require `TIKTOK_ACCESS_TOKEN`;
- does **not** call TikTok / external HTTP APIs;
- does **not** write `tiktok.yml` or `publish_log.yml`.

Eligible packs print `WOULD_PUBLISH ... would_publish=true`.

## Experimental live (unsafe, fail-closed)

```bash
# Still blocked by default:
python scripts/content/publish_tiktok_live.py --live

# Explicit experimental unlock only (NOT for production):
python scripts/content/publish_tiktok_live.py --live --allow-experimental-live
# or:
FLEXITY_ALLOW_EXPERIMENTAL_TIKTOK_LIVE=1 python scripts/content/publish_tiktok_live.py --live
```

Without `--allow-experimental-live` or `FLEXITY_ALLOW_EXPERIMENTAL_TIKTOK_LIVE=1`, `--live` fails closed before any API call.

Required for the experimental path only:

- `TIKTOK_ACCESS_TOKEN`

Errors are sanitized: `Bearer …`, `Authorization: …`, and `access_token=` values are redacted before stderr / `publish_log.yml`.

## Follow-ups (not implemented here)

- full TikTok publish status poll / completion wait;
- atomic idempotency keys (tenant-safe) beyond soft YAML `published_at` / `external_id` skip;
- production-ready Flexity Marketing adapter path (M8-D core).

## Related

- Pack template: `docs/content/templates/tiktok-content-pack-template.md`
- M8-D plan: `docs/ai/plans/2026-07-16-m8-d-multi-network-publishing-core-plan.md`
