# Marketing M8-D Publish Ops Extract Manifest

**Date:** 2026-07-17
**Source (READ ONLY):** dirty root `feature/marketing-m8-publish-bridge` @ `9658a82` + WIP
**Target worktree:** `.worktrees/marketing-publish-ops-m8d-prep`
**Branch:** `feature/marketing-publish-ops-m8d-prep` FROM `origin/main` (`abbde60`)
**Constraint:** no push / merge / deploy; dirty root not modified

## Task Classification

1. **Project:** Flexity
2. **Category:** documentation_only + universal_module (ops scripts prep extract)
3. **Risk level:** medium (live-capable scripts; default remains dry-run)
4. **Intended scope:** Instagram carousel/reels publish scripts+tests, TikTok prep scripts+tests, M8-D plans/research, extract report
5. **Forbidden scope:** credentials/.env, `.ai_local`/`.worktrees` dumps, M8 core migrations 0016–0018, E1/C1c/Booking/Branches, wholesale shared files, real publications

## Copied (full file)

| Path | Source note |
|------|-------------|
| `scripts/content/publish_instagram_live.py` | WIP over main: carousel/reels support |
| `scripts/content/publish_tiktok_live.py` | untracked on dirty root (prep script) |
| `tests/scripts/content/test_publish_instagram_live.py` | WIP carousel/reels tests |
| `tests/scripts/content/test_publish_tiktok_live.py` | untracked on dirty root |
| `docs/ai/plans/2026-07-16-m8-d-multi-network-publishing-core-plan.md` | untracked M8-D plan |
| `docs/ai/plans/2026-07-16-m8-d1-shared-publish-contract-design.md` | untracked D1 design |
| `docs/ai/research/2026-07-16-m8-d0-margosya-failure-reuse-audit.md` | untracked D0 research |

## Manual hunks / local safety patches (on top of copied WIP)

| Change | Why |
|--------|-----|
| `publish_instagram_live.py` argparse description → mentions feed_image/carousel/reels | Keep CLI help aligned with supported types |
| `publish_tiktok_live.py` `TOKEN_REDACT_PATTERN` → `r"access_token=[^&\s]+"` | Fix broken `\s` class so token redaction works |
| Trailing whitespace stripped on transferred markdown/scripts for `git diff --check` | Extract hygiene only |

## Skipped (intentionally)

| Path / area | Reason |
|-------------|--------|
| `scripts/content/publish_instagram.py` | Already on `origin/main`; dirty diff empty; shared helpers reused as-is |
| `tests/scripts/content/test_publish_instagram.py` | Already on main; no dirty delta |
| `docs/content/instagram-*.md`, TikTok/Instagram templates | Already on main; no dirty delta |
| `landing/**` (content-packs, assets, `tiktok*.txt` verification files) | Not required for ops script prep; verification files look credential-adjacent |
| `.github/workflows/instagram-publish.yml` | Ops workflow exists in dirty root but can trigger live publish; deferred out of this prep extract |
| `scripts/content/publish_threads_live.py`, Telegram scripts/tests | Out of M8-D prep transfer list |
| Backend marketing models/migrations `0016`–`0018`, vault/storage M8-C | Forbidden old M8 core |
| E1 / C1c / Booking / Branches duplicates | Forbidden |
| Wholesale `models.py` / `conftest.py` / shared backend config | Forbidden |
| `.env`, tokens, credentials, `.ai_local/**` | Forbidden |

## Shared imports kept from main (no wholesale copy)

- `publish_tiktok_live.py` / `publish_instagram_live.py` import helpers from existing main `publish_instagram.py`: `load_yaml`, `parse_publish_at`, `read_caption`
- No changes to `backend/app/core/config.py` or test conftest

## Safety invariants verified in this extract

1. **Dry-run default:** both live scripts require explicit `--live`; default path does not call provider APIs
2. **Idempotency:** skip when `published_at` / `external_id` already set
3. **Token redaction:** `sanitize_error` redacts `access_token=` values from error text
4. **Tenant isolation:** N/A for filesystem content-pack scripts (no multi-tenant DB path in this extract)
5. **No real publications / external API calls** during verification (tests mock `requests`)

## Hardening follow-up (same branch, separate commit)

After extract tip `0b0796b`:

1. TikTok (+ IG) `sanitize_error` also redacts `Bearer …` and `Authorization: …`
2. TikTok `--live` and Instagram Reels `--live` are **fail-closed** unless `--allow-experimental-live` or the matching env gate is set
3. CLI help + `docs/content/tiktok-publishing.md` / `docs/content/instagram-publishing.md` state plainly: **production live publishing is NOT supported yet**
4. Documented (not implemented): Reels status poll + atomic idempotency

## Verification commands

```bash
python -m unittest discover -s tests/scripts/content -p "test_publish_instagram*.py"
python -m unittest discover -s tests/scripts/content -p "test_publish_tiktok*.py"
git diff --check
# secret scan over changed files
```
