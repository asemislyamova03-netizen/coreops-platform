# Telegram Publishing

Flexity publishes Telegram posts only from approved content packs. The publisher is a GitHub Actions workflow; it does not use the Flexity backend or server deploy process.

## Telegram Bot Setup

1. Open `@BotFather` in Telegram and run `/newbot`.
2. Follow the prompts and store the issued token securely. Never commit it to the repository.
3. Add the bot to the target Telegram channel as an administrator.
4. Grant the bot permission to post messages.
5. Use the public channel username such as `@flexity_channel` as the chat ID. For a private channel, obtain its numeric channel ID through an approved Telegram API method.

## GitHub Secrets

In the GitHub repository, open **Settings → Secrets and variables → Actions** and add:

- `TELEGRAM_BOT_TOKEN`: token issued by BotFather;
- `TELEGRAM_CHAT_ID`: target channel username or numeric channel ID.

The workflow needs repository **Actions → General → Workflow permissions** configured to allow read and write access so it can commit publication state. Branch protection must also permit the GitHub Actions bot to push the state commit.

## Create a Content Pack

Create a directory under:

```text
landing/content/content-packs/YYYY-MM-DD-topic-slug/
  pack.yml
  telegram.md
  publish_log.yml
```

Use this metadata shape:

```yaml
date: "2026-06-22"
topic: "Topic"
slug: "topic-slug"
status: "approved"

publish:
  telegram:
    enabled: true
    status: "approved"
    publish_at: "2026-06-22T10:00:00+05:00"
    published_at: null
    external_id: null
```

Initialize the log:

```yaml
events: []
```

Put the exact Telegram message in `telegram.md`. An absent or empty file is never published.

## Approval and Scheduling

A post is eligible only when all of these conditions are satisfied:

- top-level `status` is `approved`;
- `publish.telegram.enabled` is boolean `true`;
- `publish.telegram.status` is `approved`;
- `publish.telegram.published_at` is null;
- `publish.telegram.publish_at` is a valid timezone-aware datetime that is due;
- `telegram.md` contains text.

Drafts are never published. Approval requires changing both the pack status and Telegram status to `approved` after human review. Always include an explicit UTC offset in `publish_at`, for example `+05:00`.

The scheduled workflow runs at 05:00 and 17:00 UTC. GitHub may delay scheduled jobs, so `publish_at` is an earliest publication time rather than an exact delivery guarantee.

## Manual Run

1. Open the repository's **Actions** tab.
2. Select **Publish approved Telegram content**.
3. Choose **Run workflow** on the default branch.
4. Review the job log. A successful publication prints the content-pack name and Telegram `message_id`.

Do not run the publisher locally with production secrets unless a real publication is explicitly intended and approved.

## Publication Log

After a successful send, the workflow updates `pack.yml`:

```yaml
published_at: "2026-06-22T10:01:30+05:00"
external_id: 123
```

It also appends an event to `publish_log.yml`. Published events contain `at`, `channel`, `status`, and `message_id`. Empty content and API errors are logged as `skipped` or `error` events.

The workflow commits changed `pack.yml` and `publish_log.yml` files with:

```text
Publish approved Telegram content
```

## Avoid Repeat Publication

Never clear `published_at` after a successful publication. Every later run skips a pack with a populated value. The workflow uses one concurrency group so scheduled and manual runs do not overlap.

There is a residual failure window: Telegram can accept a message before GitHub commits the updated state. If the job reports a push or state-write failure after Telegram success, check the channel and `message_id` before rerunning. Without external durable idempotency storage, this case cannot be eliminated completely.
