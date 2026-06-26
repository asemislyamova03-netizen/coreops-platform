# Implementation Plan: AI Competition News Content Pack

## Goal

Publish the approved Russian Flexity news digest for `2026-06-26-ai-competition-news`, using the user-provided image as the approved source for the public Instagram feed asset.

## Classification

- Project: Flexity
- Category: documentation_only
- Risk level: high, because the approved task includes deploy and live social publishing steps.
- Architecture layer: public landing/content funnel only.

## Scope

### Files to modify

- `landing/www/assets/social/2026-06-26-ai-competition-news/instagram-feed.png`
- `landing/content/content-packs/2026-06-26-ai-competition-news/pack.yml`
- `landing/content/content-packs/2026-06-26-ai-competition-news/telegram.md`
- `landing/content/content-packs/2026-06-26-ai-competition-news/instagram.md`
- `landing/content/content-packs/2026-06-26-ai-competition-news/instagram.yml`
- `landing/content/content-packs/2026-06-26-ai-competition-news/distribution.yml`
- `landing/content/content-packs/2026-06-26-ai-competition-news/visual.yml`
- `landing/content/articles/2026-06-26-ai-competition-news.md`
- generated `/insights` static HTML under `landing/www/insights/`
- this implementation plan file

### Files not to touch

- `backend/**`
- `platform-console/**`
- GitHub workflows
- publisher scripts
- deploy scripts
- nginx/systemd config
- secrets or local token files
- TikTok content or publishing
- unrelated dirty or untracked files

## Steps

1. Verify git status and source image availability.
2. Create sanitized `1080x1080` PNG derivative at the approved asset path.
3. Create content-pack files following existing conventions.
4. Create the approved `/insights` article.
5. Regenerate static insights pages with the existing generator.
6. Run content tests, compile checks, `git diff --check`, and explicit-scope git status.
7. Stage and commit only approved scope.
8. Push to `origin/main`, deploy landing static site only, then verify URLs.
9. Run Telegram dry-run, publish live once only if dry-run reports `Would publish: 1` and `Errors: 0`.
10. Run Instagram dry-run, publish live once only if dry-run reports `Would publish: 1` and `Errors: 0`.
11. Do not run TikTok.

## Tests/checks

- `python -m unittest discover -s tests/scripts/content -v`
- `python -m compileall scripts/content`
- image dimension check for `1080x1080 PNG`
- `git diff --check`
- `git status --short`
- live URL verification after deploy
- Telegram dry-run and live output
- Instagram dry-run and live output

## Risks

- Existing unrelated dirty files must not be staged.
- Live publish and deploy require network/remote access and may fail if credentials or approved workflows are unavailable.
- The provided image is `1254x1254`, so the derivative must be resized to `1080x1080`.

## Rollback

- Remove the new content-pack, article, generated article page, and social asset from the commit if checks fail before publishing.
- If published, do not retry or delete live social posts without explicit approval.

## Approval

Status: approved by attached task brief and unblocked by user-provided image asset.
