# Plan — M8 publish bridge and client-owned resources

**Date:** 2026-07-15
**Project:** Flexity / `coreops-platform`
**Status:** M8-A ✅ · M8-B ✅ · M8-C1a ✅ · M8-C2a ✅ FINAL ACCEPTED / GREEN — PG smoke `0017→0018→0017→0018` PASS; M8-D **not approved**
**Parent research:** `docs/ai/research/2026-07-15-m8-client-owned-publish-resources-architecture-research.md`
**Accepted ADR:** `docs/architecture/decisions/2026-07-15-m8-publish-bridge-client-owned-resources-adr.md`
**M8-A report:** `docs/ai/reports/2026-07-15-m8-a-publish-bridge-architecture-decision-report.md`
**M8-B implementation plan:** `docs/ai/plans/2026-07-16-m8-b-connected-accounts-implementation-plan.md`
**M8-C implementation plan:** `docs/ai/plans/2026-07-16-m8-c-secret-vault-storage-resource-profiles-implementation-plan.md`
**Branch:** `feature/marketing-m8-publish-bridge` · Alembic head: `0018_mkt_storage_profiles`

## Goal

Evolve Marketing Cabinet from Asem’s dogfood tenant into a repeatable tenant-scoped publishing capability where each client can connect and control its own publication accounts and media resources without making Margosya, legacy YAML packs, GitHub secrets, or a shared global credential store the source of truth.

## Product boundary

```text
Client tenant workspace
  -> Channel Connection (account metadata + secret reference)
  -> Storage Resource Profile (client-owned or Flexity-managed)
  -> Marketing Pack / Media / Preflight
  -> Dry-run
  -> explicit publish intent
  -> Channel Adapter
  -> immutable Publish Log + Audit
```

Margosya remains an optional scoped client/notification surface. It never owns publish state, tenant credentials, or the primary source of truth.

## Non-negotiable rules

1. Every connection, resource profile, pack, media item, queue attempt and log is tenant-scoped.
2. Token values are never returned by API or stored in plaintext DB JSON.
3. `credentials_json` in the current generic integration module is not an approved social-token vault.
4. A channel is never published without preflight, explicit approval, healthy connection and idempotency protection.
5. Existing legacy source packs are transition/import references, not a second live publishing source.
6. Client-owned and Flexity-managed media are explicit resource modes; no implicit cross-tenant fallback.
7. No auto-publish by default.

## Phased M8 plan

### M8-A — Architecture Decision Record and threat model

**Status:** ✅ COMPLETE — ADR accepted for planning / implementation gating
**ADR:** `docs/architecture/decisions/2026-07-15-m8-publish-bridge-client-owned-resources-adr.md`
**Report:** `docs/ai/reports/2026-07-15-m8-a-publish-bridge-architecture-decision-report.md`

**Purpose:** fix ownership, security and operational decisions before schema or provider code.

**Output (accepted):**

- client account ownership model (Modes A/B/C);
- vault/secret-provider boundary (DB metadata + `secret_ref` only; no plaintext tokens);
- token lifecycle intent: connect, health, expiry, rotation, revoke, offboarding;
- storage modes: Flexity-managed default, client public URLs early, client buckets deferred;
- roles and publish authorization (editor / approver / publisher separation);
- publication idempotency/reconciliation and audit field requirements;
- redaction and threat-model mitigations;
- M8-B…M8-G implementation gates and explicit non-goals.

**No code, migrations, credential changes or live provider calls.**

### M8-B — Connected Accounts implementation plan

**Status:** ✅ IMPLEMENTED (domain layer only — no HTTP routes/UI/vault)
**Plan:** `docs/ai/plans/2026-07-16-m8-b-connected-accounts-implementation-plan.md`

**Must include:**

- tenant ID;
- publishing provider/account identifier (provider enum is distinct from `MarketingChannel`);
- non-secret scopes/configuration;
- connection/token health state and timestamps;
- `secret_ref` only;
- tenant uniqueness;
- owner/editor/publisher permission checks;
- audit events.

**Explicit exclusion:** do not repurpose or expose generic `IntegrationConnection.credentials_json` for social tokens without an approved security migration design.

**HQ invariants (M8-B):**

- `secret_ref` is an opaque reference (not a secret) and must not be logged, audited, or returned in any future API response schema (return `has_secret` only).
- Connection `status` and `token_status` are two independent axes (do not merge).
- `status=active` and healthy credentials do **not** imply publish authorization (allow-list / publish grants are designed in M8-D).
- Account identity (credential subject) must not be silently merged with publish destination identity (e.g., Telegram bot vs channel/chat id). Destination model is an M8-D prerequisite for Telegram pilot.

### M8-C — Secret Vault Boundary + Storage Resource Profiles (umbrella)

**Status:** ✅ UMBRELLA PLAN — **HQ APPROVED WITH CLARIFICATIONS (2026-07-16)**. M8-C1/C2 code **not approved**. Production providers **not selected**.
**Plan:** `docs/ai/plans/2026-07-16-m8-c-secret-vault-storage-resource-profiles-implementation-plan.md`

**Slice structure (mandatory order):**

| Slice | Scope | Code gate |
|-------|-------|-----------|
| **M8-C1a** | `SecretVaultPort`, canonical `secret_ref`, bind/rotate/disconnect, commit-owning lifecycle, sanitizer, unchecked health stub, `0017_mkt_secret_binding` | Implemented — awaiting HQ acceptance |
| **M8-C2** | `marketing_storage_resource_profiles`, `StoragePort`, Mode A + Mode B, `MediaResource` handles, media `validation_status` | HQ approve M8-C2 after M8-C1 acceptance |

**HQ invariants (M8-C):**

- Canonical `secret_ref`: `secret://marketing/tenants/{tenant_id}/publishing-connections/{connection_id}/versions/{version}` (max 255; no vendor name; never in API/audit/logs).
- Vault write before DB bind; compensating delete on DB failure; disconnect = revoke vault → confirm → clear DB ref.
- Plaintext secret: adapter execution boundary only; marketing service/repo never reads plaintext.
- `last_error_message_redacted`: sanitizer output only — never raw provider strings.
- Storage modes: `flexity_managed` (default), `client_public_url` (strict registration, **no server fetch**), `client_bucket` (reserved/deferred).
- Storage profile: **explicit typed columns only** — no general-purpose `config_json`; Mode A backend = deployment config; Mode B = safe metadata only; Mode C credentials deferred.
- Publish adapters receive `MediaResource` / temporary access handle — not filesystem paths or bucket credentials.
- Vault bind ≠ `status=active`; stub health check cannot set `token_status=valid`; vault bind ≠ publish authorization.
- No Celery/RQ, no hard delete/retention enforcement, no malware scanner implementation in M8-C.
- Production vault provider and production S3-compatible backend: **separate deployment gates** before M8-D/E live work.

**Pre-migration gate:** PostgreSQL smoke `0015 → 0016` upgrade/downgrade mandatory before any M8-C migration. Next revision number confirmed at implementation time (provisional `0017` C1, `0018` C2).

### M8-D — Publish dry-run and intent contract

**Target:**

- dry-run endpoint validates pack, channel connection, scopes, token health and media delivery;
- explicit publish request has idempotency key;
- each attempt is tenant-scoped and auditable;
- provider responses are redacted;
- external IDs/URLs are reconciled into immutable `MarketingPublishLog`;
- retry is a visible, controlled operation.

**No legacy Git/YAML writes by the new adapter path.**

### M8-E — Telegram adapter pilot

Start with one adapter only after M8-A through M8-D receive separate approvals.

**Why Telegram:** mature reference script and simple post result.
**Guardrails:** use Channel Connection secret reference, Cabinet text/media records, dry-run first, explicit publish intent, and Cabinet log/audit writeback. Do not call the legacy bulk scanner.

### M8-F — Client setup and operator UI

Tenant owner setup:

1. enable Marketing module;
2. choose storage/resource mode allowed by tariff;
3. connect a client-owned account;
4. validate scopes and health;
5. configure media settings and quota;
6. perform a no-write dry-run;
7. assign roles and publish rules;
8. record audit/onboarding completion.

### M8-G — Additional adapters

Add Threads, Instagram, TikTok and Insights only after shared security, media and operational controls are proven. Each requires its own provider/API, media, token-refresh and reconciliation review.

## Existing code to reuse carefully

- Tenant context and module gating.
- Tenant-scoped Marketing entities, media metadata and immutable publish logs.
- Generic integration provider patterns, sync job/log patterns and external reference model.
- Tenant-isolated document storage path conventions.

## Existing code not to reuse as final solution

- Generic plaintext `credentials_json` as a token vault.
- Legacy `content-packs` filesystem as primary publish state.
- Margosya local state or YAML writes as Marketing Cabinet source of truth.
- GitHub Actions secrets as a per-client credential model.

## Decision gates

| Gate | Required approval before next step |
|---|---|
| M8-A complete ✅ | ADR accepted — vault boundary and storage ownership policy fixed for planning |
| M8-B complete ✅ | Connected accounts domain + PG smoke `0015 → 0016_mkt_publishing_conn` PASS — FINAL ACCEPTED |
| M8-C plan complete ✅ | Umbrella **HQ APPROVED WITH CLARIFICATIONS**; C2 code **not approved** |
| M8-C1a complete (review) | Secret vault core hardened (dedicated UoW) + `0017_mkt_secret_binding` — awaiting HQ + mandatory PG smoke `0016→0017` |
| M8-C1 remaining | Encrypted-file adapter / env wiring — deferred |
| M8-C2 code approval | ✅ **FINAL ACCEPTED / GREEN** (2026-07-16) — storage profiles + Mode A/B boundary; PG smoke PASS |
| M8-C2 complete | Storage profiles + StoragePort + media validation; PG smoke on new head |
| Production vault adapter | Deployment/infrastructure gate — required before M8-D/E live work |
| Production storage backend | Deployment gate — required before Mode A production uploads |
| M8-D plan complete | HQ approves dry-run/publish contract and safety controls |
| M8-E plan complete | HQ approves one tenant-scoped Telegram pilot |

## Forbidden before an approved implementation plan

- Creating channel-connection tables or migrations.
- Saving any client token, OAuth code, refresh token or storage credential.
- Connecting client accounts, granting provider scopes or checking real token values.
- Publishing, exporting, enabling a scheduler or altering Margosya.
- Moving existing media, changing storage providers or deploying.
- Implementing Telegram (or any) adapter before M8-B connected accounts + secret reference schema exist.

## Next safe step

1. M8-C2a accepted — local commit + full regression green; **no deploy / no production migration**.
2. Production storage provider (S3-compatible adapter) remains a **separate deployment gate** — unresolved in C2a.
3. Request **M8-D plan approval** when ready (dry-run/publish contract) — **not started**.
4. Do not start Telegram adapter, client onboarding UI, or production vault/storage wiring until M8-D is approved.
