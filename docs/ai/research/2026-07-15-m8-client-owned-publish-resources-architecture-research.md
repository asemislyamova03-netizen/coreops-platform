# Research Brief: M8 client-owned publish resources architecture

**Date:** 2026-07-15
**Project:** Flexity / `coreops-platform`
**Category:** `research_only`
**HQ gate:** `APPROVED: research existing architecture for client-owned publishing resources`

## Status

## ✅ RESEARCH COMPLETE — NO IMPLEMENTATION

The desired direction is already substantially present in Flexity architecture documents: Marketing Cabinet is the tenant-scoped source of truth; Margosya is a thin client; channel accounts, publish logs, media and queue belong in Flexity. The current code provides useful tenant/integration/marketing building blocks, but does not yet implement a safe client-owned publish bridge, secret vault, channel-account model, storage-ownership model, or onboarding UI.

## Documents inspected

| Document | Direct evidence |
|---|---|
| `docs/ai/PRODUCT_ARCHITECTURE.md` | Flexity is the multi-tenant target platform; integrations are universal modules; client-specific settings belong above templates/packages. |
| `docs/ai/CHANGE_REQUESTS.md` | Tenant customization is a separate client layer and must not leak into Core or universal modules. |
| `docs/ai/plans/2026-07-03-marketing-content-cabinet-product-tz.md` | Defines Marketing Cabinet, Channel Connection, tenant scope, vault refs, publish queue, object storage, Margosya API-first target. |
| `docs/FLEXITY_HQ_STRUCTURE_CONTENT_CABINET_PLAN.md` | Defines Content Cabinet as tenant-scoped future module, PostgreSQL + object storage, quotas, signed URLs, Margosya thin-client boundary. |
| `docs/ai/plans/2026-07-09-marketing-cabinet-data-model-draft.md` | Drafts `marketing_channel_connections`, `token_secret_ref`, storage-provider choices, tenant isolation and publish logs. |
| `docs/ai/plans/2026-07-09-marketing-cabinet-api-contract-draft.md` | Sets UI JWT + scoped Margosya service-token target; secrets never returned; channel connections deferred in M6. |
| `docs/ai/plans/2026-07-09-marketing-cabinet-ui-wireframe-plan.md` | Defers vault refs, channel health, storage settings, quotas and Margosya token rotation to later settings work. |
| `docs/ai/research/2026-07-09-margosya-to-cabinet-audit.md` | Confirms Margosya is transport/UI, not source of truth; identifies channel connections and health as a future Cabinet responsibility. |
| `docs/content/social-media-assets.md` | Requires public HTTPS media URLs for Instagram and records the current static-asset contract. |

## Existing architecture decisions

### 1. Multi-tenant ownership

`docs/ai/PRODUCT_ARCHITECTURE.md` defines Flexity as the FastAPI multi-tenant ERP target. `docs/FLEXITY_HQ_STRUCTURE_CONTENT_CABINET_PLAN.md` explicitly states that the HQ tenant is first, then the same framework scales to “tenant per client”.

Marketing product design requires `tenant_id` on all Marketing entities. This is not a shared global content store.

### 2. Marketing Cabinet is the source of truth

The product TZ states:

> “Marketing Cabinet / ContentOps Cabinet внутри Flexity становится source of truth для контент-операций. Маргося остаётся Telegram thin client.”

The same document requires all pack state, plans, media metadata, approvals and publish logs to be held in Flexity. Website is rendered output; Margosya is transport/UI.

### 3. Margosya is an API client, not a resource owner

The target boundary is:

```text
Margosya (transport + UI)
  -> Flexity Marketing Cabinet API
  -> PostgreSQL source of truth
  -> publish workers / channel adapters
```

Target rules are API-first, no local source of truth, fail-closed on API failure, and audit through Flexity. Current filesystem/Git publishing is an explicitly transitional path only.

### 4. Tenant-scoped channel connections

The product TZ and data-model draft define `marketing_channel_connections` with:

- `tenant_id`;
- channel type and account identifier;
- health and token status;
- scopes and non-secret configuration;
- `token_secret_ref`, explicitly described as a vault key name, **not a token**.

This directly supports a client connecting its own Telegram, Instagram, Threads or future channel account inside its tenant workspace.

### 5. Secrets and token policy

The existing target policy is unambiguous:

- no secrets in repository;
- no plaintext channel tokens in a DB row;
- Channel Connection stores a secret reference only;
- UI never returns a secret;
- Margosya uses scoped service credentials, not an owner’s broad credentials.

This is a target policy, not full current implementation.

### 6. Media and storage

The documents define:

```text
metadata -> PostgreSQL
media bytes -> S3-compatible object storage / interim file path
```

Media metadata already includes `storage_provider`, `storage_key`, `public_url`, and `preview_url`. Draft values are:

- `git_path` — current transition;
- `local_path` — legacy/server path;
- `s3` — future object storage;
- `url` — external HTTPS resource with no bytes stored by Flexity.

Target object storage adds signed previews, public CDN URLs for channel fetches, per-tenant quotas and audit/provenance.

### 7. Client-owned versus Flexity-managed resources

Existing documents establish the technical primitives for both:

- **Client-owned external resource:** an external HTTPS `url`, a tenant-scoped Channel Connection, and a vault reference to the client’s channel credential.
- **Flexity-managed resource:** stored object under a Flexity-controlled S3-compatible provider with tenant prefix, quota, signed preview and stable public publishing URL where required.

However, there is **no implemented or approved data model that explicitly records resource ownership** (`client_owned` versus `flexity_managed`), storage-provider selection per tenant, customer cloud credentials, encryption/key ownership, or tariff entitlement. The client-choice policy is therefore compatible with the architecture, but is a new M8 product decision rather than completed implementation.

## Current code/model support

### Tenant and module foundation

| Existing building block | Evidence | Relevance |
|---|---|---|
| `Tenant` / membership | `backend/app/modules/tenants/models.py` | Tenant identity and member isolation exist. |
| `TenantSettings` | same file | Has generic `labels_config` and `industry_config_json`, but no storage/channel ownership settings. |
| `TenantModule` | `backend/app/modules/module_registry/models.py` | Tenant-specific module enablement, external provider code and generic settings exist. |
| Tenant context route guard | `backend/app/modules/integrations/routes.py` | Integration endpoints are tenant-scoped through `require_module("integrations")`. |

### Generic integrations foundation

`backend/app/modules/integrations/models.py` contains:

- `IntegrationProvider`;
- tenant-scoped `IntegrationConnection`;
- tenant-scoped external references;
- sync jobs/logs;
- webhook events.

`IntegrationConnection` has a uniqueness constraint on `(tenant_id, provider_code, module_code)` and has connection state, settings, last-sync and error fields. API responses expose `has_credentials` rather than `credentials_json`.

**Security limitation:** the implementation currently persists `credentials_json` directly on `IntegrationConnection`. That is useful as a generic development integration shape, but it is not a compliant secret vault for long-lived client social tokens. The target Channel Connection design must not reuse plaintext JSON credentials as the token-store solution.

The current provider catalog contains only mock/generic CRM and accounting providers. There are no Telegram, Instagram, Threads, TikTok, social-storage or media-provider adapters.

### Marketing foundation

`backend/app/modules/marketing/models.py` already implements tenant-scoped:

- content topics;
- publication packs;
- channel texts;
- media-asset metadata;
- publish logs;
- lead attribution.

`MarketingMediaAsset` stores `storage_provider`, `storage_key`, public/preview URLs and tenant ownership. `MarketingPublishLog` retains channel, external URL/ID, timestamp, action/status/error and metadata. This is a strong starting point for a tenant publish bridge.

Current Marketing has no:

- `marketing_channel_connections` model;
- publish queue/attempt/idempotency model;
- secret reference/vault integration;
- adapter registry for social platforms;
- token health worker;
- upload/object-storage provider abstraction;
- client onboarding/settings UI for resources.

### File storage foundation

`backend/app/modules/documents/storage.py` provides tenant-isolated local filesystem paths:

```text
<STORAGE_PATH>/tenants/<tenant_id>/documents/<document_id>/
```

It does not provide an object-storage abstraction, signed URLs, quota enforcement, external-provider upload, or Marketing media byte storage.

## Current versus target

| Area | Current code | Existing target decision | Gap |
|---|---|---|---|
| Tenant isolation | Present in tenant, marketing and integration records | Required everywhere | Good base |
| Connected accounts | Generic `IntegrationConnection` only | `marketing_channel_connections` tenant-scoped | Dedicated social-account model absent |
| Secret storage | `credentials_json` persisted | vault reference only | Must not use current JSON field as social token vault |
| Token health | Generic mock `test_connection` | health, scopes, valid/expiring/invalid | No real OAuth/token-health adapters |
| Publish logs | Present | immutable audit history | Good base; no native adapter workflow |
| Publish queue | No table | per-channel queue/retries/dispatch target | Missing |
| Media metadata | Present | provider/key/URLs/provenance | Good base |
| Media bytes | Document local path; Marketing metadata only | S3-compatible/object storage | Missing provider abstraction and upload flow |
| Client storage choice | None | not yet explicitly modeled | M8 decision required |
| Client onboarding | Tenant creation/module config exists | settings + connected-channel setup | No end-to-end setup flow |
| Margosya bridge | Legacy files/scripts | scoped API client | API bridge not implemented |

## Token storage recommendation

1. The client owns the social account and grants Flexity the minimum platform permission required for the selected publishing mode.
2. Store only a `secret_ref` in tenant-scoped Channel Connection metadata. Never put access/refresh tokens in `credentials_json`, `settings_json`, Marketing metadata, logs, audit details, frontend state, Git or exports.
3. Use a dedicated secret-vault abstraction behind the application boundary. It must support create/read-for-worker/rotate/revoke without returning the secret to the Console API.
4. Keep non-secret account data separately: provider, account/page/channel identifier, scopes, expiry metadata, status and last health check.
5. Use least-privilege service credentials for Margosya; they must be tenant-scoped and separately revocable.
6. Encrypt at rest and redact any provider error payload before storage or audit logging.

## File/media storage recommendation

Adopt a tenant resource profile with one explicit storage mode per purpose:

| Mode | Ownership | Flexity stores | Best use |
|---|---|---|---|
| `flexity_managed` | Flexity | bytes in tenant-prefixed object storage; metadata in DB | Default SaaS / managed tariff |
| `client_owned_url` | Client | external stable URL + validated metadata only | Public media already hosted by client |
| `client_owned_bucket` | Client | provider/secret references and object key; no copied bytes unless requested | Enterprise / client cloud policy |

All modes need tenant isolation, access controls, media provenance, size/type validation, retention/deletion policy, preview handling, and a public delivery URL only when a channel requires it. Internal previews should be signed and time-limited.

This is a proposed M8 extension. The existing design supports `url` and future `s3`, but not the ownership/profile data, client bucket adapter or commercial policy.

## Recommended M8 direction

### M8-A — architecture and security alignment

Produce a decision record and threat model:

- tenant/account/resource ownership;
- secret vault boundary and rotation/revocation;
- storage modes and data residency;
- audit/redaction;
- publish authorization and approval separation.

### M8-B — tenant-scoped connected-account foundation

Plan a dedicated Marketing Channel Connection model using the documented target fields, not generic plaintext credentials. Include provider/account/scopes/status/token expiry/secret reference and tenant uniqueness.

### M8-C — resource and storage profile

Plan tenant storage settings and media provider abstraction. Start with Flexity-managed object storage plus external public URL registration; defer client-owned bucket write access until its security design is approved.

### M8-D — safe publish operation contract

Plan a per-channel dry-run and publish lifecycle:

```text
approved pack + healthy connection + preflight
  -> dry-run result
  -> explicit publish intent / idempotency key
  -> adapter dispatch
  -> immutable Publish Log + audit
```

Add request idempotency, external post reconciliation, retry policy, redacted failure storage and a no-auto-publish default.

### M8-E — first adapter

Implement one least-risk adapter only after approved plans. Telegram is the natural first candidate because it has a mature existing script and a simple message result, but it must run against the Cabinet record rather than legacy YAML/Git state.

### M8-F — client onboarding and settings UI

Plan an owner-admin workflow:

1. tenant created and Marketing module enabled;
2. select resource mode/tariff entitlement;
3. connect client account through provider OAuth or secure credential entry;
4. validate scopes and health;
5. configure media resource and quotas;
6. dry-run a known-safe pack;
7. grant editor/publisher roles and audit the setup.

### M8-G — further adapters

Threads, Instagram, TikTok and Insights follow only after the shared connection, storage, dry-run, audit and idempotency foundation is proven.

## Risks

1. Treating `credentials_json` as a vault would violate the documented token policy.
2. Publishing from both legacy Git packs and DB records would create duplicate posts and split source of truth.
3. OAuth refresh tokens and provider error bodies may leak unless logs/audit are redacted by design.
4. Client-owned buckets create IAM, cross-account, lifecycle, egress, support and data-residency obligations.
5. Social providers require different public-media rules; a signed preview URL is not always sufficient for publisher fetch.
6. A generic integration sync model is not automatically a safe publication worker.
7. M8 is an architecture/product initiative; it must not be mixed into current M7-D operational work.

## What was not touched

- No code, migration, configuration, secret, database/API write, deployment, publish/export, Margosya command, commit or push.
- No token values, secret-file contents or credential values were read or printed.

## Next recommended step

Request an HQ-approved **M8-A architecture decision and threat-model plan**. It should first decide vault technology/boundary, client-resource modes, tenant ownership and first-adapter constraints. Only then create a small M8-B implementation plan with exact models, migration policy, API scope, UI scope and rollback rules.

## Final checks

- No code changes.
- No migrations.
- No deploy.
- No production writes.
- No secret disclosure.
