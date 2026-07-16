# Implementation Plan: M8-C Secret Vault Boundary + Storage Resource Profiles (umbrella)

**Date:** 2026-07-16
**Project:** Flexity / `coreops-platform`
**Category:** `universal_module` (Marketing Cabinet) — implementation plan (docs only)
**Parent ADR (M8-A):** `docs/architecture/decisions/2026-07-15-m8-publish-bridge-client-owned-resources-adr.md`
**Parent M8 plan:** `docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md`
**M8-B baseline plan:** `docs/ai/plans/2026-07-16-m8-b-connected-accounts-implementation-plan.md`
**HQ gate:** M8-C umbrella plan — **HQ APPROVED WITH CLARIFICATIONS (2026-07-16)**.
**M8-C1a status:** hardened locally (dedicated UoW + post-commit safety + row lock path) — awaiting HQ review / mandatory PG smoke `0016→0017`.
**M8-C1 remaining / M8-C2 code:** **not approved**. Production vault/storage providers are **not selected**.

## Goal

Implement the **security and media ownership boundaries** required before M8-D dry-run/publish contract work:

1. **M8-C1 — Secret Vault Boundary:** vendor-neutral vault port, canonical `secret_ref`, bind/rotate/revoke/disconnect lifecycle, compensating transactions, centralized provider-error sanitization, on-demand health checks.
2. **M8-C2 — Storage Resource Profiles:** tenant-scoped storage mode table, S3-compatible `StoragePort`, Mode A (Flexity-managed) + Mode B (client public URL registration), media validation/safety states, typed `MediaResource` access handles for future adapters.

**Umbrella rule:** M8-C1 and M8-C2 are **sequential slices with separate approval gates**. Do not merge vault and storage into one large code change.

## Classification

| Field | Value |
|-------|-------|
| **Architecture layer** | `universal_module` (Marketing Cabinet + core ports) |
| **Risk level** | high (secrets + media ownership) |
| **Branch context** | `feature/marketing-m6-package` (M8-B implemented, uncommitted) |
| **Alembic head (planning time)** | `0017_mkt_secret_binding` after M8-C1a — **re-verify immediately before any next migration** |

## HQ decisions incorporated (M8-C forks)

| Fork | HQ decision |
|------|-------------|
| **1 Production vault** | Vendor-neutral `SecretVaultPort`; production adapter = separate deployment/infrastructure gate before M8-D/E live work |
| **2 `secret_ref` format** | `secret://marketing/tenants/{tenant_id}/publishing-connections/{connection_id}/versions/{version}` — max 255, UUIDs, positive int version, no vendor name, opaque outside vault layer |
| **3 Local/test vault** | Unit: in-memory; local dev: optional encrypted file; staging: production-class adapter; remove direct ORM `secret_ref` workaround from lifecycle tests |
| **4 Rotation** | Versioned refs + safe cutover (no dual-active grace as default) |
| **5 Storage backend** | S3-compatible `StoragePort`; local FS for dev only; production S3-compatible chosen at deployment gate |
| **6 Public URL (Mode B)** | Strict registration **without server fetch**; remote probe deferred |
| **7 Retention** | Soft archive only in M8-C; no `retention_days` without enforcement job |
| **8 Health checks** | Contract + on-demand at bind/rotate; no scheduler/Celery in M8-C |
| **9 Profile table** | `marketing_storage_resource_profiles` — not `TenantSettings` / `TenantModule.settings_json` |
| **10 Malware** | Scanner deferred; validation/safety status + quarantine boundary defined |

### Additional HQ invariants

1. **`last_error_message_redacted`** — only sanitizer output; never raw adapter strings.
2. **Vault transaction boundary** — compensating actions documented (see §Lifecycle).
3. **Plaintext access** — adapter execution boundary only; marketing service/repo never reads plaintext.
4. **Storage access** — adapters receive `MediaResource` / temporary access handle, not paths or credentials.
5. **Migration order** — PostgreSQL smoke `0015 → 0016` upgrade/downgrade mandatory before M8-C migrations; next revision number confirmed at implementation time.

### `secret_ref` length validation (no blocker)

Canonical example at `version=9999999999`: **143 characters** — within `VARCHAR(255)`. UUIDs must not be shortened.

---

## Umbrella architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     MARKETING DOMAIN (tenant-scoped)                     │
│  PublishingConnection ──secret_ref──► SecretVaultPort (opaque ref only) │
│  StorageResourceProfile ──mode──────► StoragePort (typed handles)       │
│  MediaAsset ──validation_status──────► MediaResource (adapter input)  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌───────────────────┐                         ┌───────────────────┐
│ SecretVaultPort   │                         │ StoragePort       │
│ (vendor-neutral)  │                         │ (S3-compatible)   │
├───────────────────┤                         ├───────────────────┤
│ InMemory (tests)  │                         │ InMemory (tests)  │
│ EncryptedFile     │                         │ LocalFS (dev only)│
│   (local dev)     │                         │ MinIO (opt smoke) │
│ Production adapter│                         │ S3/R2/… (deploy)  │
│   (deploy gate)   │                         │   (deploy gate)   │
└───────────────────┘                         └───────────────────┘
        │                                               │
        ▼                                               ▼
   Adapter execution                            Publish adapters (M8-E+)
   boundary ONLY                                 receive MediaResource
   (plaintext, ephemeral)                        NOT filesystem paths
```

---

# Slice M8-C1 — Secret Vault Boundary

## M8-C1 goal

Provide a **vendor-neutral secret vault boundary** that:

- stores publishing credentials outside PostgreSQL;
- returns canonical versioned `secret_ref` strings;
- binds refs to `MarketingPublishingConnection` only after successful vault write;
- supports rotate/revoke/disconnect with compensating cleanup;
- exposes on-demand health checks without periodic workers;
- centralizes provider-error redaction for `last_error_message_redacted`, audit, and logs.

## M8-C1 scope

### In scope

| Area | Deliverable |
|------|-------------|
| **Core port** | `SecretVaultPort` protocol + `SecretRef` value object + ref parser/validator |
| **Adapters** | `InMemorySecretVault` (tests, default for unit slice); `EncryptedFileSecretVault` (optional local dev only — not required for M8-C1 unit tests) |
| **Marketing service** | `bind_secret`, `rotate_secret`, `revoke_secret`, `disconnect_connection` orchestration |
| **Health** | `PublishingHealthCheckPort` contract + on-demand check at bind/rotate |
| **Sanitizer** | `ProviderErrorSanitizer` — single entry for DB/audit/log error text |
| **DB extensions** | `secret_version` (int, nullable until bound); optional `secret_bound_at` |
| **Enums** | Unblock `EXPIRED` token_status transitions per vault lifecycle rules |
| **Audit** | Sanitized events: `secret_bound`, `secret_rotated`, `secret_revoked`, `secret_disconnect`, `vault_recovery_required` |
| **Tests** | Full lifecycle without direct ORM `secret_ref` bypass; compensating failure paths |

### Explicit out-of-scope (M8-C1)

- HTTP routes / UI / OAuth flows
- Production vault adapter selection or wiring
- Real provider API calls (Telegram, Meta, etc.)
- Periodic/scheduled health checks, Celery/RQ
- Publish authorization, destinations, dry-run (M8-D)
- Telegram adapter (M8-E)
- Storage profiles / media (M8-C2)
- Margosya changes
- `IntegrationConnection.credentials_json` migration

## Canonical `SecretRef` specification

### Format

```text
secret://marketing/tenants/{tenant_id}/publishing-connections/{connection_id}/versions/{version}
```

| Rule | Requirement |
|------|-------------|
| Max length | 255 characters |
| `tenant_id` | UUID matching connection `tenant_id` |
| `connection_id` | UUID matching connection `id` |
| `version` | Positive integer ≥ 1 |
| Vendor/backend | **Not included** in logical ref |
| Opacity | Parsed/validated only in vault layer + bind orchestration |
| API/UI/audit/logs | **Never returned or logged** |
| Forbidden values | Raw token, JWT, `Bearer …`, API keys, provider secrets |

### `has_secret` semantics

- `has_secret = bool(secret_ref)` in views only.
- `secret_version` may be exposed in internal service state (not API) for rotation logic.
- Future API: `has_secret: bool`, `secret_version: int | null` optional internal admin field TBD in M8-F — default **omit version from API**.

## `SecretVaultPort` interface

**Location (proposed):** `backend/app/core/secrets/port.py`

```python
# Conceptual — implementation follows project typing conventions

class SecretVaultPort(Protocol):
    def store_secret(
        self,
        *,
        tenant_id: UUID,
        connection_id: UUID,
        version: int,
        plaintext: SecretPlaintext,  # wrapper; no repr/log
        metadata: SecretStoreMetadata | None = None,
    ) -> SecretRef: ...

    def read_secret(self, ref: SecretRef) -> SecretPlaintext: ...

    def deactivate_version(self, ref: SecretRef) -> None: ...
    # soft revoke: version unusable for read; retained for audit/recovery

    def delete_version(self, ref: SecretRef) -> None: ...
    # hard delete after confirmed cutover or orphan cleanup

    def version_exists(self, ref: SecretRef) -> bool: ...
```

### Plaintext access rules

| Allowed | Forbidden |
|---------|-----------|
| Adapter execution boundary (M8-E+) | Marketing repository/service reading plaintext |
| Ephemeral in-memory during bind health check | Caching across requests |
| Vault adapter internal | `repr()`, `str()`, debug logging, audit payloads |
| Tenant-scoped read by ref ownership validation | Cross-tenant ref resolution |

### Adapter implementations (M8-C1)

| Adapter | Environment | Notes |
|---------|-------------|-------|
| `InMemorySecretVault` | Unit/integration tests | **Default** for M8-C1 unit slice; required test fixture |
| `EncryptedFileSecretVault` | Local development only (optional) | **Not required** for M8-C1 unit tests; **never** staging/production |
| Production adapter | Staging/production | **Not implemented in M8-C1** — separate deployment/infrastructure gate |

**Encrypted-file adapter rules (local dev only):**

- Optional convenience adapter for local development; M8-C1 unit slice uses in-memory adapter only.
- **Never** staging or production.
- Uses a **dedicated master key** via env var `SECRET_VAULT_LOCAL_MASTER_KEY` — **must not reuse** application `SECRET_KEY`.
- Master key must **not** be stored in the vault file, database, Git, or audit payloads.
- Encrypted blobs live outside the repository.
- Python implementation must **not** promise guaranteed memory zeroization of plaintext secrets.

**Staging rule:** must use production-class vault adapter, not encrypted local file.

## `PublishingHealthCheckPort` interface

**Location (proposed):** `backend/app/modules/marketing/service/publishing_health.py`

```python
class PublishingHealthCheckPort(Protocol):
    def check_connection_health(
        self,
        *,
        provider: MarketingPublishingProvider,
        secret_ref: SecretRef,
        scopes: list[str],
    ) -> HealthCheckResult: ...
```

- M8-C1 ships a **noop/stub** implementation returning structured result without live provider calls.
- Real provider health (e.g. Telegram `getMe`) deferred to M8-D/E with sanitizer-wrapped errors.
- On-demand invocation: at `bind_secret` and `rotate_secret` when health port configured.

### Health-check semantics (M8-C1 — mandatory)

| Rule | Requirement |
|------|-------------|
| Stub/no-op health check | **Must not** set `token_status=valid` or `expiring` |
| Without real provider validation | Result is `unchecked` / leaves `token_status=not_configured` (or explicit `unchecked` enum value if added) |
| After vault bind | Connection **does not** become `status=active` automatically |
| Vault bind | ≠ provider health validation |
| Vault bind | ≠ publish authorization (M8-D) |
| Real `valid`/`expiring` | Only after successful **real** provider validation in M8-D/E adapter path |

**Bind default post-conditions:** `secret_ref` + `secret_version` set; `token_status` remains `not_configured` until real health check passes in a future slice; `status` unchanged unless operator explicitly activates connection (separate step).

## Provider error sanitizer

**Location (proposed):** `backend/app/core/security/provider_error_sanitizer.py`

### Input sources (must pass through sanitizer)

- Provider HTTP responses / exception messages
- Adapter-internal errors before DB write
- Health check failures

### Forbidden in output (`last_error_message_redacted`, audit, logs)

- Raw provider response bodies
- Authorization headers
- Request URLs containing tokens
- Token/JWT/Bearer fragments
- `secret_ref` strings
- Stack traces with secret material (truncate/genericize)

### Output contract

| Field | Content |
|-------|---------|
| `error_code` | Stable machine code, e.g. `provider_auth_failed`, `health_check_timeout` |
| `message_redacted` | Human-safe, no secrets, max length enforced (e.g. 512) |
| `audit_metadata` | `error_code`, `provider`, optional `http_status_class` only |

**Rule:** `last_error_message_redacted` on connection row accepts **only** sanitizer `message_redacted` — service rejects direct assignment.

## Marketing vault binding service

**Location (proposed):** `backend/app/modules/marketing/service/publishing_secret_lifecycle.py`

Orchestrates vault + DB; **marketing domain never calls `read_secret` for business logic**.

### Operations

| Operation | Summary |
|-----------|---------|
| `bind_secret` | vault store → optional health check → DB bind → audit |
| `rotate_secret` | new version store → health → atomic DB switch → deactivate old |
| `revoke_secret` | deactivate current version in vault → update token_status |
| `disconnect_connection` | revoke vault → confirm → clear `secret_ref` → status update |

### Lifecycle diagrams

#### Bind (initial connect)

```text
Client/operator provides plaintext (future UI; tests use fixture)
        │
        ▼
[1] Validate connection exists, tenant-scoped, status allows bind
        │
        ▼
[2] version = 1 (or next if re-bind policy allows)
        │
        ▼
[3] vault.store_secret(...) → SecretRef
        │
        ▼
[4] Optional: health_check_port.check_connection_health(ref)
        │ fail → vault.delete_version(new ref) → sanitized error → STOP
        ▼
[5] DB: SET secret_ref, secret_version; token_status stays not_configured (stub health cannot set valid)
        connection status unchanged (bind ≠ activate; operator activates separately)
        │ fail → vault.delete_version(new ref) → COMPENSATING CLEANUP → STOP
        ▼
[6] Audit: secret_bound (sanitized metadata only)
```

#### Rotate (safe cutover)

```text
[1] Load connection + current secret_ref/version
        │
        ▼
[2] new_version = current + 1
        │
        ▼
[3] vault.store_secret(..., version=new_version) → new_ref
        │
        ▼
[4] Optional health check on new_ref
        │ fail → vault.delete_version(new_ref) → STOP
        ▼
[5] DB TRANSACTION: SET secret_ref=new_ref, secret_version=new_version
        │ fail → vault.delete_version(new_ref) → COMPENSATING CLEANUP → STOP
        ▼
[6] vault.deactivate_version(old_ref)
        │ fail → connection stays on new_ref; audit vault_recovery_required
        ▼
[7] Audit: secret_rotated (old_version, new_version numbers only — no refs)
```

**No dual-active grace period** as default rule.

#### Disconnect / offboarding

```text
[1] vault.deactivate_version(current_ref)
        │
        ▼
[2] Confirm version inactive / unreadable
        │ fail → STOP (do NOT clear DB ref — avoid orphan secret with no DB pointer)
        ▼
[3] DB: CLEAR secret_ref, secret_version; token_status=not_configured; status→disabled/not_connected
        │
        ▼
[4] Optional: vault.delete_version after grace (config, not M8-C1 default)
        │
        ▼
[5] Audit: secret_disconnect
```

**Forbidden order:** clear DB `secret_ref` before vault revoke confirms — prevents losing track of vault secret.

### Compensating actions matrix

| Scenario | Action |
|----------|--------|
| Vault write OK, DB bind fails | `delete_version` new ref; connection unchanged |
| DB bind OK, old deactivate fails | Keep connection on new ref; emit `vault_recovery_required` audit; manual ops playbook (M8-C1 docs) |
| Rotate health check fails | `delete_version` new ref only |
| Disconnect vault revoke fails | Do not clear DB ref; surface sanitized operational error |

## M8-C1 data model changes

### `marketing_publishing_connections` extensions

| Column | Type | Notes |
|--------|------|-------|
| `secret_version` | INTEGER NULL | Set when bound; NULL when not configured |
| `secret_bound_at` | TIMESTAMPTZ NULL | Optional audit-friendly timestamp |

Existing `secret_ref VARCHAR(255)` retained.

### CHECK constraints (add in M8-C1 migration)

- `secret_ref` IS NOT NULL → `secret_version` IS NOT NULL AND `secret_version` >= 1
- `secret_ref` format validated in service layer (DB regex optional, service mandatory)
- Re-enable `EXPIRED` transitions via service rules tied to `expires_at` + health (not blocked stub)

### Migration policy

1. **Pre-gate:** PostgreSQL smoke `0015 → 0016` upgrade + downgrade on staging clone.
2. **Re-verify** `alembic heads` immediately before authoring migration.
3. **Canonical revision (M8-C1a):** `0017_mkt_secret_binding` (len ≤ 32; `down_revision=0016_mkt_publishing_conn`).
4. No plaintext secrets in migration files.

## M8-C1 files (planned)

### Create

| File | Purpose |
|------|---------|
| `backend/app/core/secrets/port.py` | `SecretVaultPort`, `SecretRef`, exceptions |
| `backend/app/core/secrets/ref.py` | Parse/build/validate canonical ref |
| `backend/app/core/secrets/adapters/in_memory.py` | Test adapter |
| `backend/app/core/secrets/adapters/encrypted_file.py` | Local dev adapter |
| `backend/app/core/security/provider_error_sanitizer.py` | Centralized redaction |
| `backend/app/modules/marketing/service/publishing_secret_lifecycle.py` | Bind/rotate/revoke/disconnect |
| `backend/app/modules/marketing/service/publishing_health.py` | Health check port + stub |
| `backend/tests/test_secret_ref_format.py` | Ref validation |
| `backend/tests/test_secret_vault_in_memory.py` | Vault adapter tests |
| `backend/tests/test_publishing_secret_lifecycle.py` | Full lifecycle + compensating |
| `backend/tests/test_provider_error_sanitizer.py` | Redaction cases |
| `backend/alembic/versions/20260716_0017_...py` | **Provisional** — confirm head first |

### Modify

| File | Change |
|------|--------|
| `backend/app/modules/marketing/models.py` | `secret_version`, `secret_bound_at` |
| `backend/app/modules/marketing/service/publishing_connections.py` | Delegate secret ops; sanitizer for errors; unblock EXPIRED |
| `backend/app/modules/marketing/repository.py` | `bind_secret_ref`, `clear_secret_ref` internal methods |
| `backend/app/modules/marketing/enums.py` | Document token_status lifecycle |
| `backend/tests/test_marketing_publishing_connections.py` | Remove `_set_secret_ref_direct` from lifecycle tests |
| `backend/app/core/config.py` | **Names only:** `SECRET_VAULT_ADAPTER`, `SECRET_VAULT_LOCAL_MASTER_KEY`, `SECRET_VAULT_LOCAL_PATH` |

### Do not touch (M8-C1)

- `IntegrationConnection` / integrations module
- HTTP routes, platform-console UI
- Margosya, landing, scripts/content publishers
- M8-C2 storage files
- Production deployment manifests

## M8-C1 test matrix

| ID | Case | Expected |
|----|------|----------|
| C1-T01 | Build canonical ref | 143 chars max case passes; invalid UUID fails |
| C1-T02 | Reject raw token as ref | Validation error |
| C1-T03 | `store_secret` → ref | Ref matches canonical format |
| C1-T04 | Tenant mismatch in ref | `read_secret` forbidden |
| C1-T05 | Bind happy path | DB has ref+version; vault has secret; audit sanitized |
| C1-T06 | Bind DB failure | New vault version deleted; old state unchanged |
| C1-T07 | Bind health failure (stub/real) | New version deleted; sanitized error; token_status not set to valid |
| C1-T07b | Bind with stub health | token_status stays not_configured; status not auto-active |
| C1-T08 | Rotate happy path | New version active; old deactivated |
| C1-T09 | Rotate DB failure | New version deleted; old remains active |
| C1-T10 | Rotate old deactivate fails | Connection on new; recovery audit event |
| C1-T11 | Disconnect happy path | Vault inactive; DB ref cleared |
| C1-T12 | Disconnect vault fail | DB ref **not** cleared |
| C1-T13 | `has_secret` only in view | No `secret_ref` in API schema |
| C1-T14 | Sanitizer strips Bearer token | Safe message only in DB |
| C1-T15 | Sanitizer strips secret_ref substring | Safe message only |
| C1-T16 | Audit payload | No ref, no plaintext, no scope values |
| C1-T17 | Cross-tenant bind | Forbidden |
| C1-T18 | Plaintext not in repo layer | Repository has no read_secret import |
| C1-T19 | Encrypted file adapter roundtrip | Local dev only test |
| C1-T20 | Migration upgrade/downgrade | SQLite test + PG smoke gate |

## M8-C1 approval gate

**Status:** M8-C1a implemented locally — awaiting HQ acceptance

**Prerequisites:**

- M8-B FINAL ACCEPTED ✅ (PG smoke PASS)
- M8-C umbrella plan approved ✅
- M8-C1a code: Secret Vault Core Boundary (`0017_mkt_secret_binding`)

**Not approved yet:** encrypted-file adapter, env/config wiring, M8-C2.

---

# Slice M8-C2 — Storage Resource Profiles

## M8-C2 goal

Introduce **tenant-scoped storage ownership** and **typed media access** for publish bridge:

- `marketing_storage_resource_profiles` table with mode enum;
- `StoragePort` for Flexity-managed uploads (Mode A);
- strict client public URL registration (Mode B) without server fetch;
- media validation/safety status on `MarketingMediaAsset`;
- `MediaResource` handle for future publish adapters.

## M8-C2 scope

### In scope

| Area | Deliverable |
|------|-------------|
| **Profile table** | `marketing_storage_resource_profiles` per tenant (one active profile row policy TBD: one default per tenant) |
| **Mode enum** | `flexity_managed` (default), `client_public_url`, `client_bucket` (reserved/deferred) |
| **StoragePort** | Vendor-neutral S3-compatible interface |
| **Adapters** | InMemory (tests), LocalFilesystem (dev), S3-compatible stub interface |
| **Mode A** | Upload/store via `StoragePort`; tenant-prefixed keys; metadata on `MarketingMediaAsset` |
| **Mode B** | URL registration validator (HTTPS, no userinfo, no localhost/private/metadata IPs, length limits) |
| **Media safety** | `validation_status` enum, size limits, declared vs verified MIME boundary |
| **MediaResource** | Typed handle: `resource_id`, `mode`, `delivery_kind`, ephemeral access descriptor |
| **Service** | Profile CRUD (domain only), media attach respects active profile mode |
| **Tests** | Mode A upload, Mode B URL rejection matrix, tenant isolation |

### Explicit out-of-scope (M8-C2)

- Client-owned bucket credentials/IAM (Mode C implementation)
- Server-side HEAD/GET/DNS fetch for URL validation
- Malware scanner implementation
- Hard delete / object lifecycle enforcement / `retention_days`
- Signed URL generation for production CDN (interface only; impl with deploy gate)
- Remote URL probe component (future)
- Publish eligibility rules (M8-D)
- HTTP routes / UI
- Celery/background orphan cleanup
- Margosya

## Storage modes

| Mode | M8-C2 support | Description |
|------|---------------|-------------|
| **A `flexity_managed`** | ✅ Implement | Bytes in Flexity storage via `StoragePort`; tenant-prefixed keys |
| **B `client_public_url`** | ✅ Implement | Metadata + validated URL only; **unverified external resource** |
| **C `client_bucket`** | ⏸ Reserved | Enum value allowed; no credentials/config implementation |

**Default:** new tenants / marketing module activation → `flexity_managed` profile created or implied.

## `marketing_storage_resource_profiles` table

**Storage config boundary (HQ clarification):**

- **No general-purpose `config_json`** on this table.
- Use **only explicit typed columns** for tenant-safe profile metadata.
- **Mode A** backend configuration (S3 endpoint, bucket, credentials, signing keys) is **deployment-level Flexity configuration** — not tenant profile columns.
- **Mode B** stores only safe resource/profile metadata (limits, labels) — no URLs with embedded credentials.
- **Mode C** credentials/configuration fully **deferred** — enum may exist; no implementation columns.
- **Never store** in profile metadata: bucket keys, access keys, secrets, signed URLs, provider credentials.

**Future extensibility:** if JSON is ever needed, requires **separate HQ decision** with explicit typed allow-list and unknown-key rejection — not a deny-list pattern.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | CASCADE, indexed |
| `mode` | ENUM | `flexity_managed`, `client_public_url`, `client_bucket` (reserved) |
| `status` | ENUM | `active`, `disabled` |
| `display_name` | VARCHAR(255) | Operator label |
| `max_upload_bytes` | BIGINT NULL | Mode A tenant upload limit (safe metadata); NULL = platform default |
| `max_url_length` | INTEGER NULL | Mode B URL length cap; NULL = platform default (1024) |
| `allowed_mime_types` | TEXT[] NULL | Declared MIME allow-list subset; NULL = platform default |
| `created_at` / `updated_at` | TIMESTAMPTZ | |
| `created_by_user_id` / `updated_by_user_id` | UUID NULL | |

**Unique:** `(tenant_id)` WHERE `status = 'active'` — one active profile per tenant (partial unique index).

### Mode-specific column usage

| Mode | Typed columns used | Deployment-level (not in profile) |
|------|-------------------|-----------------------------------|
| **A `flexity_managed`** | `max_upload_bytes`, `allowed_mime_types` | S3-compatible endpoint, bucket, IAM/credentials, signing config via `STORAGE_*` env / deploy config |
| **B `client_public_url`** | `max_url_length`, `allowed_mime_types` | N/A — URLs live on `marketing_media_assets.public_url` |
| **C `client_bucket`** | None in M8-C2 | Fully deferred |

**Forbidden in all profile columns:** any secret, credential, signed URL, bucket access key, or provider token.

## `StoragePort` interface

**Location (proposed):** `backend/app/core/storage/port.py`

```python
class StoragePort(Protocol):
    def put_object(
        self,
        *,
        tenant_id: UUID,
        object_key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObjectDescriptor: ...

    def delete_object(self, *, tenant_id: UUID, object_key: str) -> None: ...
    # M8-C2: soft/no-op or marker only — hard delete deferred

    def generate_temporary_access(
        self,
        *,
        tenant_id: UUID,
        object_key: str,
        purpose: str,
        ttl_seconds: int,
    ) -> TemporaryAccessHandle: ...
```

### Adapter roadmap

| Adapter | Environment |
|---------|-------------|
| `InMemoryStorage` | Unit tests |
| `LocalFilesystemStorage` | Local dev (extends `STORAGE_PATH` convention) |
| `MinIOStorage` | Optional integration smoke — **not required infra for M8-C2** |
| S3-compatible production | Deployment gate — **not implemented in M8-C2** |

**Rule:** Local filesystem is **not** production Mode A for multi-tenant SaaS.

### Object key convention (Mode A)

```text
marketing/tenants/{tenant_id}/media/{asset_id}/{filename}
```

- Keys never exposed to publish adapters as raw paths.
- Adapters receive `MediaResource` with `TemporaryAccessHandle`.

## Mode B — public URL registration (strict, no server fetch)

### Validation rules (M8-C2)

| Rule | Enforcement |
|------|-------------|
| Scheme | `https` only |
| Userinfo | Reject `user:pass@host` |
| Localhost | Reject |
| Private/link-local/loopback IPs | Reject literal IPs in these ranges |
| Metadata service IPs | Reject (e.g. `169.254.169.254`) |
| Length | ≤ profile `max_url_length` / column max |
| Redirects | N/A — no fetch |
| MIME/size | **Declared only** — not verified |

### Semantics

- URL stored as **unverified external resource**.
- `validation_status = registered_unverified` (see below).
- Do **not** claim SSRF-safe — server fetch not implemented.

### Future component (post M8-C2, pre/live publish)

`RemoteUrlProbe` (name TBD) with egress restrictions, DNS/IP validation, redirect revalidation, timeout/size caps — **M8-D input** for publish eligibility.

## Media asset extensions

### New enum: `MarketingMediaValidationStatus`

| Value | Meaning |
|-------|---------|
| `pending` | Mode A upload in progress |
| `registered_unverified` | Mode B URL registered, static validation only — **not publish eligibility** |
| `validated_metadata` | Declared MIME/size/URL rules passed local policy — **not malware-safe, not publish-ready** |
| `rejected` | Failed policy (MIME, size, URL rules) |
| `quarantined` | Reserved for future scanner positive |
| `archived` | Soft archive (existing asset status may overlap — align: use `MarketingMediaAssetStatus.ARCHIVED` for lifecycle, `validation_status` for safety) |

**Clarification:** Keep `MarketingMediaAssetStatus` for pack lifecycle (`stored`, `archived`). Add `validation_status` for safety/eligibility track.

### Media validation semantics (HQ clarification)

| Status | Meaning | Publish-ready? |
|--------|---------|----------------|
| `validated_metadata` | Declared metadata and platform limits passed | **No** — not malware-safe, not publish-ready |
| `registered_unverified` | Mode B URL passed static registration rules | **No** — not publish eligibility |
| `quarantined` / `rejected` | Safety policy failure | **No** |

- **Final publish eligibility** is defined in **M8-D** (preflight + `validation_status` + future probe/scanner gates).
- Malware scanner implementation remains **deferred**; MIME extension/pattern validation does **not** make a file malware-safe.
- Mode B `registered_unverified` explicitly does **not** grant publish eligibility.

### New fields on `marketing_media_assets`

| Column | Type | Notes |
|--------|------|-------|
| `validation_status` | ENUM | Default by mode |
| `declared_mime_type` | VARCHAR(128) | Copy of declared MIME at registration |
| `declared_size_bytes` | BIGINT NULL | Optional declared size (not verified in M8-C2) |
| `verified_mime_type` | VARCHAR(128) NULL | NULL in M8-C2 (future probe/magic-byte) |
| `storage_profile_id` | UUID FK NULL | Link to active profile at attach time |
| `resource_mode` | ENUM | Denormalized mode snapshot for audit |

### Size limits (M8-C2)

| Limit | Default | Enforced |
|-------|---------|----------|
| Max upload bytes (Mode A) | 10 MiB images (configurable per profile) | On `put_object` |
| Max URL length (Mode B) | 1024 | On registration |
| Video | **Deferred** — extend `ALLOWED_MEDIA_MIME_TYPES` only after HQ video policy |

### Magic-byte / content validation boundary

- M8-C2: **not implemented** for production path.
- Interface hook: `ContentValidationPort.validate_magic_bytes(data, declared_mime) -> bool` — stub returns `declared accepted`.
- M8-D publish eligibility must check `validation_status` (among other gates).

### Malware scanner boundary

- No scanner in M8-C2.
- `quarantined` status reserved.
- Future: `MalwareScanPort.scan(descriptor) -> ScanResult` async hook.
- **Do not claim** MIME extension validation is malware-safe.

## `MediaResource` typed handle

**Location (proposed):** `backend/app/modules/marketing/service/media_resource.py`

```python
@dataclass(frozen=True)
class MediaResource:
    asset_id: UUID
    tenant_id: UUID
    mode: MarketingStorageResourceMode
    delivery_kind: Literal["temporary_url", "external_url", "inline_bytes"]
    access: TemporaryAccessHandle | ExternalUrlReference
    validation_status: MarketingMediaValidationStatus
    declared_mime_type: str
    # NO filesystem path, NO bucket credentials, NO permanent private URL
```

Publish adapters (M8-E+) resolve `MediaResource` at execution time — not `storage_key` path strings.

## M8-C2 service boundaries

| Service | Responsibility |
|---------|----------------|
| `MarketingStorageProfileService` | Create/activate/disable profile; enforce one active per tenant |
| `MarketingMediaService` (extend) | Route attach/upload through active profile + `StoragePort` or URL validator |
| `MarketingMediaResourceResolver` | Build `MediaResource` for adapter boundary |

### Mode A attach flow

```text
[1] Load active storage profile (flexity_managed)
        │
        ▼
[2] Validate MIME + size against profile allow-list
        │
        ▼
[3] storage_port.put_object(tenant-prefixed key)
        │
        ▼
[4] Create/update MarketingMediaAsset metadata
        validation_status = validated_metadata
        storage_provider = flexity_managed
        storage_key = object key (internal; not adapter path)
        │
        ▼
[5] Audit: media_stored (asset_id, mode, mime, size — no key secrets)
```

### Mode B attach flow

```text
[1] Load active storage profile (client_public_url)
        │
        ▼
[2] Validate URL rules (no fetch)
        │
        ▼
[3] Create MarketingMediaAsset
        public_url = normalized URL
        validation_status = registered_unverified
        storage_provider = client_public_url
        │
        ▼
[4] Audit: media_url_registered (sanitized host only, no full URL in audit if policy requires host-only)
```

**Audit note:** Prefer `url_host` + `url_hash` in audit, not full URL, to reduce leakage in log aggregation.

## M8-C2 data model / migration

1. **Pre-gate:** M8-C1 migration applied + PG smoke on cumulative head.
2. **Re-verify** alembic head before authoring.
3. **Provisional revision:** `0018_marketing_storage_resource_profiles` — confirm number at implementation time.

### Tables

- `marketing_storage_resource_profiles` (new)
- `marketing_media_assets` (alter — new columns)

## M8-C2 files (planned)

### Create

| File | Purpose |
|------|---------|
| `backend/app/core/storage/port.py` | `StoragePort`, descriptors, handles |
| `backend/app/core/storage/adapters/in_memory.py` | Test adapter |
| `backend/app/core/storage/adapters/local_filesystem.py` | Dev adapter |
| `backend/app/modules/marketing/models.py` (add) | `MarketingStorageResourceProfile` |
| `backend/app/modules/marketing/enums.py` (add) | Storage mode, validation status |
| `backend/app/modules/marketing/service/storage_profiles.py` | Profile service |
| `backend/app/modules/marketing/service/media_resource.py` | `MediaResource` resolver |
| `backend/app/modules/marketing/service/public_url_validator.py` | Mode B rules |
| `backend/tests/test_storage_resource_profiles.py` | Profile CRUD/isolation |
| `backend/tests/test_public_url_validator.py` | URL rejection matrix |
| `backend/tests/test_media_resource_modes.py` | Mode A/B attach |
| `backend/tests/test_storage_port_in_memory.py` | Storage adapter |
| `backend/alembic/versions/20260716_0018_...py` | **Provisional** |

### Modify

| File | Change |
|------|--------|
| `backend/app/modules/marketing/models.py` | Media asset columns |
| `backend/app/modules/marketing/service/media.py` | Profile-aware attach |
| `backend/app/modules/marketing/repository.py` | Profile + media queries |
| `backend/app/modules/marketing/schemas.py` | Views include `validation_status`, not internal keys |
| `backend/app/core/config.py` | **Names only:** `STORAGE_ADAPTER`, optional MinIO vars for smoke |

## M8-C2 test matrix

| ID | Case | Expected |
|----|------|----------|
| C2-T01 | Create flexity_managed profile | Active profile per tenant |
| C2-T02 | Duplicate active profile | Rejected |
| C2-T03 | Mode A upload happy path | Asset stored; validation_status=validated_metadata |
| C2-T04 | Mode A oversize upload | Rejected |
| C2-T05 | Mode A invalid MIME | Rejected |
| C2-T06 | Mode B https URL valid | registered_unverified |
| C2-T07 | Mode B http URL | Rejected |
| C2-T08 | Mode B localhost | Rejected |
| C2-T09 | Mode B 10.0.0.1 | Rejected |
| C2-T10 | Mode B 169.254.169.254 | Rejected |
| C2-T11 | Mode B userinfo URL | Rejected |
| C2-T12 | Mode C profile create | Allowed enum; no credential columns populated |
| C2-T13 | Profile typed columns only | No `config_json` column; secrets rejected at service layer if ever passed |
| C2-T14 | MediaResource has no path | Adapter handle only |
| C2-T15 | Cross-tenant profile access | Forbidden |
| C2-T16 | Archive media | Status archived; no hard delete |
| C2-T17 | Tenant key prefix isolation | Keys scoped |
| C2-T18 | Migration upgrade/downgrade | SQLite + PG smoke |

## M8-C2 approval gate

**Status:** waiting for HQ approval before code

**Prerequisites:**

- M8-C1 implemented and accepted ⏳
- M8-C umbrella plan approved ✅

**Approve to start:** M8-C2 code + migration `0018` (provisional) only — **after** M8-C1 merge/acceptance.

---

# Cross-cutting threat controls

| Threat | Control |
|--------|---------|
| Plaintext token in DB | Vault port only; CHECK + service guards; no `credentials_json` |
| `secret_ref` leakage | Never in API/audit/logs; ref validator rejects token-like strings |
| Cross-tenant secret access | Ref embeds tenant_id; vault adapter validates ownership |
| Orphan vault secrets | Compensating delete on DB failure; disconnect order enforced |
| Provider error leakage | Centralized sanitizer mandatory |
| SSRF via Mode B URL | Strict static validation only; **no claim of SSRF-safe without fetch controls** |
| Client bucket credential storage | Mode C deferred; no credential columns in profile table |
| Path/credential exposure to adapters | `MediaResource` typed handles only |
| Malware | Status/quarantine boundary; scanner deferred |
| Local dev secrets in Git | Encrypted file master key env-only; never commit |
| Staging parity | Production-class vault on staging; not local file adapter |

---

# Implementation sequence (mandatory order)

```text
[Gate 0] PG smoke: 0015 → 0016 upgrade/downgrade
        │
        ▼
[Gate 1] HQ approve M8-C1
        │
        ▼
[M8-C1] Vault port + lifecycle + migration 0017 (provisional)
        │
        ▼
[Gate 2] HQ accept M8-C1 / PG smoke on new head
        │
        ▼
[Gate 3] HQ approve M8-C2
        │
        ▼
[M8-C2] Storage profiles + StoragePort + migration 0018 (provisional)
        │
        ▼
[Gate 4] HQ accept M8-C2
        │
        ▼
[Deploy gates] Production vault provider + production storage backend
        │
        ▼
[M8-D] Dry-run / publish eligibility (uses validation_status + health)
```

---

# Rollback

| Slice | Rollback |
|-------|----------|
| **M8-C1** | `alembic downgrade` one revision; remove vault binding service; connections retain `secret_ref` if already bound (manual vault cleanup playbook) |
| **M8-C2** | `alembic downgrade` one revision; media assets retain new columns nullable/defaulted |

**Code rollback:** revert slice branch commit only — do not partial-revert across C1/C2.

---

# Unresolved production-provider decisions (explicit)

These require **separate deployment/infrastructure gates** — not decided in M8-C:

| Decision | Status | Required before |
|----------|--------|-----------------|
| Production vault vendor (AWS SM / Vault / Azure KV / other) | **Unresolved** | M8-D/E live provider calls |
| Production S3-compatible backend (AWS S3 / R2 / MinIO managed) | **Unresolved** | Mode A production uploads |
| Staging vault adapter wiring | **Unresolved** | Staging secret bind smoke |
| CDN/signed URL delivery for Mode A previews | **Unresolved** | M8-F UI / external preview |
| `RemoteUrlProbe` implementation | **Deferred** | M8-D publish eligibility for Mode B |
| Malware scanner vendor | **Deferred** | Production media upload hardening |
| Video MIME policy | **Deferred** | Video channel adapters |
| Background health check scheduler | **Deferred** | Post job-architecture |

---

# Approval

| Document / gate | Status |
|-----------------|--------|
| M8-C umbrella plan | **HQ APPROVED WITH CLARIFICATIONS (2026-07-16)** — this document |
| M8-C1a Secret Vault Core Boundary | **Implemented locally — awaiting HQ review** (`0017_mkt_secret_binding`) |
| M8-C1 remaining (encrypted-file, env wiring) | **Not approved / deferred** |
| M8-C2 code implementation | **Not approved** — requires M8-C1 acceptance + separate explicit HQ approval |
| Production vault provider | **Not selected** — deployment/infrastructure gate |
| Production storage backend | **Not selected** — deployment/infrastructure gate |

---

# Handoff note

Next safe step: HQ review/accept **M8-C1a**. Do not start M8-C2 or encrypted-file/env wiring until separate approval. Optional: disposable PG smoke `0016 → 0017_mkt_secret_binding` before deploy.
