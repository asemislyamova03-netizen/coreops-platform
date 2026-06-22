# Implementation Plan: Reusable Instagram Approved Content Workflow

## Goal

Подготовить reusable GitHub Actions workflow для ручной публикации всех eligible Instagram `feed_image` content-packs через существующий `scripts/content/publish_instagram_live.py`.

План не разрешает создание workflow, запуск `--live`, вызовы Meta/Instagram API или изменение content-packs.

## Classification

- Project: Flexity.
- Category: `documentation_only`.
- Future implementation area: marketing/content automation, отдельно от backend/CoreOps.
- Risk: medium/high, потому что live publication необратима из git и может частично завершиться до записи metadata.
- Current branch at planning time: `main`.

## Current State

- Первая Instagram live-публикация завершена с `external_id: 18184343005390956`.
- Metadata зафиксирована commit `edd684e493b2f2a0288df94a840a0e2e49f42ca6`.
- One-off workflow удалён commit `bea75a75a7cacd12385e2f6ea57391223c42d40d`.
- Текущий published pack больше не eligible: dry-run возвращает `Done. Would publish: 0. Errors: 0`.
- Общий publisher уже сканирует `landing/content/content-packs/*/instagram.yml` и не привязан к конкретному pack.
- Сейчас в репозитории остаётся только Telegram workflow; Instagram reusable workflow отсутствует.

## Scope

### File to create after separate implementation approval

- `.github/workflows/instagram-publish.yml`

### Existing runtime dependency to reuse unchanged in first slice

- `scripts/content/publish_instagram_live.py`

### Files not to touch

- Existing content-packs during workflow implementation.
- `scripts/content/publish_telegram.py`.
- `.github/workflows/telegram-publish.yml`.
- Backend, CoreOps, FastAPI, `landing/www`, `/insights`, deploy and nginx.
- Content generation scripts and social asset generation.
- Secrets or credential files.

If implementation reveals that publisher changes are required, stop and create a separate implementation plan instead of expanding workflow scope.

## Trigger

Initial trigger:

```yaml
on:
  workflow_dispatch:
    inputs:
      confirm_live:
        description: "Type PUBLISH to confirm live Instagram publishing"
        required: true
        type: string
      expected_count:
        description: "Expected number of eligible Instagram packs"
        required: true
        type: string
```

No `schedule`, `push`, `repository_dispatch` or automatic trigger in the first reusable slice.

Both dispatch inputs are mandatory:

- `confirm_live` must equal the exact case-sensitive value `PUBLISH`. Any other value fails before secrets are attached or live mode starts. This input is only a control word and must never contain a token, credential or other secret.
- `expected_count` is a string because the workflow must validate and normalize it explicitly. It must contain only a non-negative base-10 integer and is compared numerically with the eligible count parsed from dry-run output. Invalid, signed, decimal or otherwise malformed values fail before live mode.

The manual `workflow_dispatch` action plus the exact confirmation/count inputs form the human approval gate for that run. Inputs do not make the trigger automatic and do not carry credentials.

Schedule requires separate approval after several successful manual runs and token lifecycle validation.

## Difference From One-Off Workflow

The reusable workflow must:

- have no reference to `2026-06-22-ai-tools-need-process`;
- scan all content-packs through the existing publisher;
- publish every pack that passes the common eligibility contract;
- allow metadata changes for any eligible pack only under the approved content-pack path patterns;
- use a reusable concurrency group such as `instagram-approved-publish` with `cancel-in-progress: false`;
- use commit message `Publish approved Instagram content`.

It must not reuse the one-off assumptions `Would publish: 1` or a two-file hardcoded allowlist for one slug.

## Eligibility Gates

A pack may be published only when all conditions hold:

- top-level `pack.yml status` is `approved`;
- `instagram.yml status` is `approved`;
- `publish_at` is timezone-aware and `<= now`;
- `published_at` is `null`;
- `external_id` is `null`;
- `type` is supported by the approved MVP, initially `feed_image` only;
- `media.image_url` is a non-empty absolute `https://` URL;
- `caption_source` resolves inside the same pack and exists;
- caption is non-empty;
- `INSTAGRAM_USER_ID` and `INSTAGRAM_ACCESS_TOKEN` are present for the live step;
- the pack has not already been published.

The workflow must fail closed if dry-run reports validation errors, output cannot be parsed, secrets are absent, or changed files escape the allowlist.

## Proposed Workflow Flow

1. **Checkout**
   - `actions/checkout@v4` on the manually selected/default branch.
   - Require `permissions: contents: write` only for metadata commit/push.
   - Do not persist or print credentials beyond what checkout needs.

2. **Set up Python**
   - `actions/setup-python@v5` with Python `3.11`.

3. **Install dependencies**
   - Install only dependencies already required by the publisher: `pyyaml` and `requests`.
   - No unrelated package or application build.

4. **Pre-live dry-run**
   - Run `python scripts/content/publish_instagram_live.py` without `--live` and without Instagram secrets in the step environment.
   - Capture and print only normal dry-run output.
   - Parse the terminal summary `Done. Would publish: N. Errors: M`.
   - If output is missing/malformed or `M != 0`, fail closed.
   - If `N == 0`, exit success immediately; do not attach secrets, run live mode, create a commit or push.
   - If `N > 0`, continue only within the same manually dispatched run and only after both dispatch inputs pass validation.

5. **Manual confirmation gate**
   - Confirm that this run originated from `workflow_dispatch`.
   - Require exact case-sensitive `confirm_live == PUBLISH`.
   - Validate `expected_count` as a non-negative integer string.
   - Compare normalized `expected_count` with dry-run `N`; any mismatch fails before secrets are attached or live mode starts.
   - Never print dispatch values except a safe fixed confirmation message; neither input may contain secrets.
   - No second automatic trigger is created; the dispatch plus validated inputs are the human approval.

6. **Secret presence gate**
   - Attach `INSTAGRAM_USER_ID` and `INSTAGRAM_ACCESS_TOKEN` only to the secret-check/live step.
   - Check only whether each value is non-empty.
   - Print only secret names and presence status, never values or lengths.

7. **Remote-head preflight**
   - Immediately before live publication, fetch `origin/main` and verify the checked-out SHA still equals the remote SHA.
   - If main advanced, exit before any Meta API call and rerun manually from the new HEAD.
   - This narrows the risk that metadata push later fails as non-fast-forward.

8. **Live publish**
   - Start only when `confirm_live == PUBLISH`, normalized `expected_count == N`, dry-run `M == 0`, and both required secrets are non-empty.
   - Run exactly `python scripts/content/publish_instagram_live.py --live`.
   - Do not wrap it in an API retry loop.
   - Record its exit code for reconciliation; do not immediately discard metadata written for successful earlier packs.

9. **Changed-file allowlist and reconciliation**
   - Run even if the live command returns nonzero.
   - Inspect tracked and untracked changes using `git status --porcelain`, not only `git diff --name-only`.
   - Permit only:

     ```text
     landing/content/content-packs/*/instagram.yml
     landing/content/content-packs/*/publish_log.yml
     ```

   - Reject deletions, renames, paths outside a single content-pack directory, and every other changed file.
   - Require every changed `instagram.yml` or `publish_log.yml` to belong to a pack reported by the current live execution.
   - Stage only validated paths, never `git add -A`.

10. **Commit metadata**
    - If no metadata changed, do not commit.
    - If allowed metadata changed, commit with:

      `Publish approved Instagram content`

    - Persist successful publication metadata even if a later pack failed, then mark the job failed after reconciliation. This prevents a successfully published pack from remaining `approved` in git.
    - An implementation test must prove this partial-success behavior before enabling the workflow.

11. **Push**
    - Push only the metadata commit to the same branch after allowlist validation.
    - Do not pull/rebase after live publication.
    - If push fails, stop and surface an operator incident: do not rerun live publishing. Reconcile the published external IDs and metadata manually under a separate approval.

12. **Final job result**
    - Return success when dry-run count is zero.
    - Return success when all eligible packs publish and metadata push succeeds.
    - Return failure after preserving valid metadata when any pack/API/validation/push step fails.

## Safety Requirements

- No token echo, substring, length or serialization.
- No `set -x`, `printenv`, environment dump or verbose HTTP logging.
- Use `set -euo pipefail` except where live exit code must be captured explicitly for reconciliation.
- No retry after ambiguous container creation/publication response.
- No `schedule`, `push`, `repository_dispatch` or other automatic trigger initially.
- Live mode requires all four gates simultaneously: exact `confirm_live == PUBLISH`, matching `expected_count`, dry-run `Errors: 0`, and non-empty required secrets.
- An unparseable dry-run summary or malformed input fails before secrets/live execution.
- No Telegram file or workflow changes.
- No backend, deploy, nginx, `/insights` or landing changes.
- No content/caption/image generation inside the publish workflow.
- No mutation before eligibility and secret gates pass.
- `concurrency.cancel-in-progress` must be `false` so a newer manual run cannot terminate a live publish midway.
- Workflow logs must not print API request payloads containing tokens.

## Partial Success and Idempotency

The existing publisher loops over all eligible packs. A reusable run can therefore publish one pack successfully and fail on a later pack.

The workflow must not use a simple `if: success()` metadata commit step. That would lose metadata for already published packs when the publisher exits nonzero later, creating a republish risk.

Required behavior:

- preserve metadata for each confirmed successful publication;
- allow error events only in the matching `publish_log.yml`;
- commit valid metadata through an `always()`/captured-exit reconciliation path;
- fail the run after metadata persistence when any error occurred;
- never automatically rerun an ambiguous pack.
- after partial success, stop the workflow and require operator analysis of API output, external posts and committed metadata before any new manual run; do not attempt to republish failed or ambiguous packs automatically.

## Token Lifecycle

Facebook Graph access token expiry/revocation is an independent operational risk.

This workflow plan does not implement token exchange, refresh, App Secret handling or rotation. Before schedule or unattended publishing, create a separate plan covering:

- long-lived token acquisition supported by the selected Meta auth flow;
- expiry monitoring without printing token values;
- rotation owner and runbook;
- GitHub Secret replacement;
- revocation and incident response;
- test procedure after rotation.

Token lifecycle must not be solved by committing credentials or adding token output to workflow logs.

## Tests and Checks

Before commit of the future workflow:

- YAML syntax/action validation passes.
- Workflow contains only `workflow_dispatch`.
- Both `confirm_live` and `expected_count` are required dispatch inputs of type `string`.
- `confirm_live` accepts only exact `PUBLISH`; every other value prevents the live step.
- `expected_count` rejects malformed values and must numerically match parsed dry-run `N` when `N > 0`.
- Dry-run output that cannot be parsed reliably prevents the live step.
- No hardcoded content-pack slug exists.
- Static grep confirms no `set -x`, `printenv`, token echo or schedule.
- Dry-run with zero eligible packs exits success and creates no commit.
- Zero eligible packs never attach secrets or require a count match to perform live work because live work is skipped.
- Dry-run with one and multiple fixture packs parses counts correctly.
- Count mismatch prevents secrets/live execution.
- Dry-run errors prevent live execution.
- Missing either secret prevents live execution without printing values.
- Allowlist accepts only `instagram.yml` and `publish_log.yml` under content-packs.
- Allowlist rejects untracked, deleted, renamed and out-of-scope files.
- Tests prove already published packs are skipped.
- Mocked partial-success scenario commits successful metadata, then leaves the job failed.
- Push failure path does not retry `--live`.
- `git diff --check` passes.
- Final diff contains only `.github/workflows/instagram-publish.yml` unless a separate publisher-change plan is approved.

No test may call Meta or Instagram API.

## Risks

- **Partial success:** some posts may be live before a later pack fails.
- **Ambiguous API response:** publication may exist even if the client receives timeout/error.
- **Metadata push race:** main can advance after preflight but before workflow push.
- **Expired token:** live run fails despite successful dry-run.
- **Broad allowlist:** a weak glob can accidentally commit unrelated content-pack changes.
- **Multiple eligible packs:** one manual dispatch may publish more content than the operator expected.
- **Log leakage:** unsafe shell/debug output can expose credentials.
- **Branch protection:** GitHub Actions may be unable to push directly to `main` after external publication.
- **Input mismatch:** an operator may approve a different number of packs than dry-run finds; mandatory `expected_count` must stop the run before live publication.

Before implementation approval, confirm that direct Actions push to `main` remains permitted. Mandatory `confirm_live` and `expected_count` inputs are now part of the approved design and must not be omitted.

## Rollback

- Before any live run: delete/revert only `.github/workflows/instagram-publish.yml`.
- After external publication: reverting git does not delete Instagram posts.
- Never automatically delete an Instagram post as workflow rollback.
- If metadata commit/push fails after publication, do not rerun; reconcile `external_id`, `published_at`, status and log manually under separate approval.

## Future Scope

Requires separate approval and plan:

- scheduled Instagram publishing;
- carousel publishing;
- Reels publishing;
- token refresh/rotation automation;
- Insights site publishing;
- content or social asset generation within automation.

## Approval

Status: waiting for explicit approval to create `.github/workflows/instagram-publish.yml`.

This plan approval, when given, authorizes only the reusable manual workflow. It does not authorize a live workflow run or any Meta/Instagram API call.
