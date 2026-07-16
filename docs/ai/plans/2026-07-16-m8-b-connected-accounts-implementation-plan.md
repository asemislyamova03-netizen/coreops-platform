# Implementation Plan: M8-B Connected Accounts (tenant-scoped)

**Date:** 2026-07-16
**Project:** Flexity / `coreops-platform`
**Category:** `universal_module` (Marketing Cabinet) — implementation plan (docs only)
**Parent ADR (M8-A):** `docs/architecture/decisions/2026-07-15-m8-publish-bridge-client-owned-resources-adr.md`
**Parent M8 plan:** `docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md`

## Goal

Design and implement the **tenant-scoped connected publishing accounts** foundation for Publish Bridge:

- dedicated Marketing model for connected accounts (not `IntegrationConnection`);
- two independent axes: connection lifecycle status and credential/token health status;
- **secret reference schema** (`secret_ref`) without storing token material in DB;
- repository/service boundary with strict tenant isolation;
- audit events for key lifecycle changes;
- unit/integration tests proving invariants and preventing unsafe shortcuts.

This slice must **not** implement any publish authorization, destination allow-list, Telegram adapter, live publish, HTTP routes/UI, vault backend, storage system, or provider integrations.

## Classification

- **Architecture layer:** `universal_module` (Marketing Cabinet)
- **Risk level:** medium (schema + security boundary), mitigated by strict invariants + tests
- **HQ gate:** *this plan requires explicit approval before any code/migration work*

## Scope

### In scope (M8-B)

1. **New tenant-scoped model:** connected publishing accounts in Marketing module.
2. **Enums:** dedicated provider enum (not `MarketingChannel`) + connection status + token status.
3. **DB constraints/indexes:** tenant isolation, partial unique identity index, performance indexes.
4. **Repository/service layer:** CRUD + status/health metadata updates, with validated transitions.
5. **Audit events:** create, metadata update, enable/disable, status/token_status transitions (redacted).
6. **Tests:** unit/integration tests for tenant isolation, invariants, transitions, uniqueness, and redaction.

### Explicit out-of-scope (M8-B)

- Any **HTTP routes** / API endpoints / response schemas for this feature.
- Any **UI** (console setup screens).
- Any **vault implementation** (storing/revoking secrets, rotation, OAuth flows).
- Any **token handling** (no reading/validating real tokens, no provider API calls).
- Any **publish destination model / allow-list / publish grants** (M8-D).
- Any **Telegram adapter** or other provider adapters (M8-E+).
- Any **live publish**, dry-run, preflight, or publish queue (M8-D).
- Any **storage implementation** (M8-C).
- Any changes to **Margosya**.

## Non-negotiable constraints (security + boundaries)

### Secret boundary (must never be violated)

- **Forbidden in plaintext DB (any table/column/JSON):**
  - access tokens
  - refresh tokens
  - client secrets
  - bot tokens
  - private keys
- **Forbidden storage locations:** `IntegrationConnection.credentials_json`, `settings_json`, marketing pack/media metadata, publish logs, audit payloads, error logs, Git, exports.

### `secret_ref` handling rules

- `secret_ref` is an **opaque reference**, not a secret.
- `secret_ref` must **not** be logged.
- `secret_ref` must **not** be included in audit payloads.
- `secret_ref` must **never** be returned externally in any future API response schema (even admin/provider_owner).
  Future APIs return **`has_secret: bool` only**.

### Tenant isolation invariants

- All repository/service operations are tenant-scoped.
- Cross-tenant read/update/delete is forbidden and must be covered by tests.

### Publish boundary invariant

**Active connection + healthy credentials does not imply publish authorization.**
Publish grants / destination allow-lists are designed and enforced in **M8-D**.

### Identity boundary invariant

Account identity (credential subject) must not be silently merged with publish destination identity.

Example: Telegram bot credential identity != Telegram channel/chat destination id.

M8-B models **connected accounts** only; publish destination model is a required input to M8-D before any Telegram pilot.

## Repository inspection (evidence)

- Marketing models use UUID PK + `tenant_id` FK CASCADE and `native_enum=False` enums:
  - `backend/app/modules/marketing/models.py` (topics/packs/texts/media/publish logs).
- Current schema tip: `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` (revision `0015_marketing_cabinet_mvp`).
- Integrations store plaintext `credentials_json` on `IntegrationConnection` and are **not** approved as social token vault:
  - `backend/app/modules/integrations/models.py` (`credentials_json` persisted).
- Platform audit recorder exists (not yet used by marketing):
  - `backend/app/modules/audit/recorder.py`.

## Proposed data model (M8-B)

### Table naming (recommendation)

**Recommended table:** `marketing_publishing_connections`
Rationale: explicitly “publishing provider credentials”, distinct from content channels (which include `insights`).

Acceptable alternative: `marketing_channel_connections` (legacy draft name), but must still use provider enum (not `MarketingChannel`).

### Enums

1. `MarketingPublishingProvider` (new)
   - `telegram`
   - `instagram`
   - `threads`
   - `tiktok`

2. `MarketingPublishingConnectionStatus` (new, lifecycle; independent of token health)
   - `not_connected` (created without binding)
   - `active`
   - `error`
   - `disabled`
   - `expired` (optional; only if used distinctly from token_status)

3. `MarketingPublishingTokenStatus` (new, credential health; independent of lifecycle)
   - `not_configured`
   - `valid`
   - `expiring`
   - `invalid`

**Conventions:** store enums as SQLAlchemy `Enum(..., native_enum=False)` to match existing migrations.

### Columns (draft)

Required:

- `id` UUID PK
- `tenant_id` UUID FK → `tenants.id` ON DELETE CASCADE, indexed
- `provider` enum `marketing_publishing_provider`, indexed
- `account_display_name` `VARCHAR(255)` NOT NULL
- `account_identifier` `VARCHAR(255)` NULL
  (required by service validation before `status` can transition to `active`)
- `status` enum `marketing_publishing_connection_status`, NOT NULL, indexed
- `token_status` enum `marketing_publishing_token_status`, NOT NULL, indexed
- `scopes_json` JSON NOT NULL default `[]`
- `expires_at` TIMESTAMPTZ NULL
- `last_checked_at` TIMESTAMPTZ NULL
- `config_json` JSON NOT NULL default `{}` (non-secret provider config only)
- `metadata_json` JSON NOT NULL default `{}`
- `created_by_user_id` UUID NULL
- `updated_by_user_id` UUID NULL
- `created_at` TIMESTAMPTZ NOT NULL default `now()`
- `updated_at` TIMESTAMPTZ NOT NULL default `now()`

Secret reference (allowed but must be treated as non-exportable metadata):

- `secret_ref` `VARCHAR(255)` NULL
  (opaque vault reference; never returned, never logged/audited)

Optional (if needed for operator visibility without secrets):

- `last_error_code` `VARCHAR(64)` NULL
- `last_error_message_redacted` `VARCHAR(512)` NULL
  (must be redacted; must not include `secret_ref` or token-like material)

### Constraints and indexes

1. **Partial uniqueness** (HQ decision):

- Unique index on `(tenant_id, provider, account_identifier)`
  **WHERE `account_identifier IS NOT NULL`**

2. Performance indexes (minimum set):

- `(tenant_id, provider)`
- `(tenant_id, status)`
- `(tenant_id, token_status)`
- `(tenant_id, last_checked_at)` (optional; depends on health polling later)

3. No DB check constraints for transition rules (kept in service validation), but tests must cover:

- `status=active` requires `account_identifier` non-null.
- `scopes_json` normalized: unique, non-empty strings only.
- No token-like material stored in any JSON fields by service validation.

## Tenant isolation and ownership boundary

- Table is tenant-scoped and lives under Marketing module (`require_module("marketing")`).
- All repo queries require `tenant_id` input and filter by it.
- No cross-tenant lookup by `id` without tenant filter (tests must prove 404/forbidden behavior).

## Identity model: account vs destination (explicit)

M8-B models **connected account identity** only:

- `provider` identifies credential domain.
- `account_identifier` identifies the connected account subject (e.g., bot username/id, ig account id).

M8-B explicitly does **not** model publish destinations (e.g., Telegram chat/channel ID).
M8-D must introduce destination model / publish grants / allow-lists, and must ensure:

- credential subject != destination id are separate entities;
- preflight validates destination allow-list before publish.

## Health/status, scopes, expiration metadata

### Normalization rules (service layer)

- `scopes_json`: normalize to lowercase? (provider-specific decision), trim whitespace, drop empties, unique set.
- `expires_at`, `last_checked_at`: metadata only; no token parsing or provider calls in M8-B.
- `token_status`: purely administrative/metadata in this slice; updates come from future health checks (M8-C/D), but transitions should still be validated for consistency (e.g., cannot set `valid` if `secret_ref` is null — policy decision; if enforced, add tests).

### Status transition rules (service layer)
Service must validate transitions and enforce HQ rules (no provider calls, no vault ops):

- **Activation rule:** `status=active` requires `account_identifier` to be present (service validation; DB remains nullable).
- **Two independent axes:** changing `token_status` must not implicitly change `status`, and vice versa.
- **Soft lifecycle only:** no hard delete in M8-B.
- **Disable behavior:** `disabled` keeps `secret_ref` (no vault cleanup imitation).
- **Disconnect/offboarding:** must be deferred to M8-C workflow (vault revoke/delete → clear ref → disconnected + audit).
- **Active != publish authorization:** service must not expose “publish ready”; no allow-list implied.

## Repository / service boundary (M8-B)

No HTTP routes. Implement as internal domain service only:

- **Repository**: DB CRUD with mandatory tenant filters.
- **Service**: validation (transitions + scopes normalization + “no token-like material” checks), redacted error fields, audit events, tenant isolation.

## Audit requirements (M8-B)

Use `AuditRecorder.audit_log` (tenant-scoped) for:

- create
- metadata update (display name / identifier / scopes / timestamps / redacted error)
- enable/disable (status change)
- token_status updates
- secret binding metadata changes (record only `has_secret` boolean before/after; never the ref)

Audit payload rules:

- Never include `secret_ref`.
- Never include token-like material.
- Never include raw provider payloads (redacted summaries only).

## Migration plan (M8-B implementation; not executed here)

Next Alembic revision after `0015_marketing_cabinet_mvp`:

**Canonical revision ID:** `0016_mkt_publishing_conn` (≤32 chars for `alembic_version.version_num`).

1. Create enums with `native_enum=False`:
   - `marketing_publishing_provider`
   - `marketing_publishing_connection_status`
   - `marketing_publishing_token_status`
2. Create `marketing_publishing_connections` table.
3. Create indexes, including partial unique index:
   - `(tenant_id, provider, account_identifier)` **WHERE** `account_identifier IS NOT NULL`

Downgrade: drop indexes → drop table → drop enums.

## Test matrix (M8-B)

### Integration tests (DB + tenant isolation)

- Tenant isolation: tenant A cannot be read/updated from tenant B.
- Partial uniqueness: NULL identifiers allowed; non-null duplicates blocked per tenant/provider.

### Service/unit tests (validation + invariants)

- Activation requires `account_identifier`.
- Status and token_status independence.
- Scopes normalization: unique non-empty strings; stable ordering if enforced.
- Security: reject token-like material in `config_json` / `metadata_json` / `scopes_json`.
- Redaction: ensure `secret_ref` never appears in audit payloads or log/error messages (string search in test assertions).

## Rollback (future implementation)

- DB rollback via Alembic downgrade (drops table + enums).
- App rollback: feature is self-contained and has no HTTP exposure in M8-B.

## Risks

- Identity confusion (account vs publish destination) if M8-D shortcuts; blocked by invariant.
- Secret_ref leakage via audit/logging if not strictly excluded; blocked by tests.
- Token-like material creeping into JSON; blocked by validation + tests.

## Approval

Status: **approved and implemented (M8-B domain slice)**
