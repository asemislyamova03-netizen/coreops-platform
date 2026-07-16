# ADR — M8 Publish Bridge: client-owned publishing resources and tenant-scoped connected accounts

**Date:** 2026-07-15
**Project:** Flexity / `coreops-platform`
**Category:** `documentation_only` / architecture decision
**HQ gate:** `APPROVED: M8-A Publish Bridge architecture decision`
**Parent research:** `docs/ai/research/2026-07-15-m8-client-owned-publish-resources-architecture-research.md`
**Parent plan:** `docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md`

---

## 1. Decision title

**M8 Publish Bridge: client-owned publishing resources and tenant-scoped connected accounts**

## 2. Status

**Accepted for planning / implementation gating**

This ADR gates all M8 implementation slices. No M8-B+ code, migration, provider adapter, secret write, publish path, or UI may start without a separate HQ-approved implementation plan that respects this decision.

## 3. Context

Marketing Cabinet inside Flexity is the tenant-scoped source of truth for content operations: packs, channel texts, media metadata, approvals, and publish logs live in Flexity PostgreSQL under `tenant_id`.

Historical publication reconciliation (M7-D) is complete for the reviewed Asem dogfood packs. The operational problem is no longer “manually mark what was already posted.” The next product goal is a **client-replicable publishing setup**: each tenant can connect its own publishing accounts and media resources, run dry-run/preflight, and publish with audit — without hardcoding Asem tokens, without treating Margosya filesystem/YAML/Git as production state, and without a shared global credential store.

Publish Bridge must work first for the Asem dogfood tenant, then for arbitrary client tenants using the same tenant-scoped model.

Related target documents already pointed this way (Marketing Cabinet TZ, data-model draft, HQ Content Cabinet plan, Margosya-to-Cabinet audit). M8-A formalizes the binding decisions that prevent unsafe shortcuts before schema or adapters exist.

## 4. Decision

1. **Publish Bridge is tenant-scoped.** Every connection, storage profile, queue attempt, adapter dispatch, and publish log belongs to exactly one `tenant_id`. No cross-tenant credential or channel reuse.

2. **The client owns publishing accounts.** Telegram bots/channels, Instagram/Threads/TikTok accounts (when added), and similar identities remain client-owned. Flexity receives delegated publish capability; Flexity does not become the account owner.

3. **Flexity stores non-secret metadata and secret references only.** Account display names, provider codes, channel IDs, scopes, health status, and vault references may live in DB. Token material must not.

4. **Social tokens must be stored in a secret vault / secret manager boundary**, not as plaintext DB values, not in Marketing metadata, not in logs, not in Git, not in exports, not in frontend state.

5. **`credentials_json` on generic `IntegrationConnection` is not approved as a social-token vault.** Marketing Channel Connections must use `secret_ref` (or equivalent vault reference) and must not reuse plaintext JSON credentials as the production token store.

6. **Media/file storage supports three ownership modes:**
   - Flexity-managed object storage as the managed default;
   - external client-owned public HTTPS URLs as an early safe option;
   - client-owned buckets deferred until IAM/lifecycle/support/quota/revocation/billing/security design is approved.

7. **Margosya legacy publishers are not the production source of truth.** Margosya remains an optional thin API client / helper / notification surface. Legacy file scanners, YAML packs, and GitHub Actions secrets are transitional or reference only.

8. **All live publish operations require all of the following:**
   - approved pack;
   - preflight passed;
   - channel allow-list for the tenant/connection;
   - dry-run / preview completed for the intended action;
   - idempotency key;
   - audit logs;
   - write-back to Marketing publish logs.

9. **Provider adapters are separate from core Marketing state.** Adapters translate Cabinet records + vault-backed credentials into provider API calls. They do not own pack state, approval state, or media provenance.

10. **No provider adapter may mutate YAML/content-pack files or Git state for DB-backed packs.** Adapters must not write source packs, commit, push, or treat the filesystem as live publish state.

### Forbidden shortcuts (explicit)

- No hardcoded Asem (or any tenant) tokens in code, config committed to Git, or shared env as a multi-tenant default.
- No legacy Margosya file pipeline as the production Publish Bridge.
- No YAML mutation as source of truth for DB-backed packs.
- No Git side effects from publish adapters.
- No plaintext token DB storage.
- No tenant-crossing tokens or connections.
- No direct live publish without dry-run, approval, and audit.

## 5. Ownership modes

### Mode A — Flexity-managed (default)

- Flexity hosts the token vault boundary and managed object storage (tenant-prefixed keys).
- Client connects accounts through setup UI (OAuth and/or secure manual token entry where provider allows).
- Flexity manages publish execution workers, retries (controlled), and immutable publish/audit logs.
- Suitable as the SaaS / managed-tariff default.

### Mode B — Client-provided public URLs (early)

- Client hosts media/files externally under stable public HTTPS URLs.
- Flexity stores metadata + validated public URLs only (no media bytes copied unless later requested by a separate feature).
- Publishing uses the URL when the provider supports remote fetch / URL attach.
- Does not replace Mode A for tokens; channel credentials still use the vault boundary.

### Mode C — Client-owned storage bucket (deferred)

- Client cloud bucket (S3-compatible or provider-equivalent) with Flexity write/read via IAM role or equivalent.
- **Deferred.** Requires separate design for IAM, lifecycle, support, quotas, revocation, billing, data residency, and security review.
- Not in first MVP.

## 6. Secret boundary

### May be stored in DB (non-secret / metadata)

| Field class | Examples |
|---|---|
| Provider identity | provider name / code |
| Account identity | account display name, channel/page/chat ID |
| Tenancy | `tenant_id` |
| Health | token health status, `last_checked_at` |
| Vault pointer | vault reference / `secret_ref` (name or opaque id, not the secret) |
| Authorization metadata | scopes |
| Lifecycle metadata | `expires_at` |

API responses may expose `has_secret` / health status. They must never return secret values.

### Must not be stored in plaintext DB

- access tokens
- refresh tokens
- client secrets
- bot tokens
- private keys

Also forbidden as plaintext storage locations for social tokens: `credentials_json`, `settings_json`, Marketing pack/media metadata, publish log error bodies (must be redacted), audit detail payloads, frontend local storage, Git, and exports.

### Vault lifecycle (binding intent)

Connect → health check → expiry tracking → rotate → revoke → tenant offboarding revocation. Workers may read secrets only inside the publish/worker boundary; Console/API consumers must not receive them.

Exact vault technology (platform secret manager vs dedicated vault service) is an M8-C implementation gate; this ADR only binds the **boundary**: secrets out of plaintext DB and out of Marketing state.

## 7. Threat model

| Risk | Mitigation |
|---|---|
| **Token leakage** | Vault-only secret storage; never return secrets via API; redact provider errors; no secrets in Git/logs/exports; least-privilege Margosya service credentials separate from channel tokens. |
| **Wrong tenant publishing** | Enforce `tenant_id` on every connection, pack, media, queue row, and adapter call; refuse cross-tenant connection IDs; module/permission gates. |
| **Duplicate posts** | Mandatory idempotency key; reconcile external post id/url into publish logs; controlled retries only; no parallel live publish for the same key. |
| **Stale / revoked tokens** | Token health status + `expires_at` + `last_checked_at`; fail-closed when unhealthy/expired/revoked; require reconnect before live publish. |
| **Publishing to wrong channel/account** | Explicit target account on dry-run and publish intent; channel allow-list; show account identity in dry-run preview; no implicit “default Asem” account. |
| **Accidental bulk publish** | No automatic bulk publish by default; per-pack / per-channel explicit intent; no legacy bulk scanner in production path. |
| **Provider API failure** | Record redacted failure in publish log + audit; visible retry; no silent success; adapter version recorded. |
| **Media URL exposure** | Prefer signed time-limited previews for internal UI; public publishing URLs only when provider requires; validate HTTPS and MIME/size; Mode B URLs are client-owned and must be intentional. |
| **Audit gaps** | Immutable Marketing publish logs + platform audit events for configure/approve/publish/revoke; required fields listed in §8. |
| **Operator bypass** | Role separation (editor ≠ approver ≠ publisher); no publish for unapproved packs; dry-run required before live; no undocumented “admin force publish” without audit and HQ-approved exception. |
| **Legacy Margosya side effects** | Adapters must not mutate YAML/Git; Margosya is not source of truth; legacy publishers remain non-production; fail-closed if API path unavailable rather than falling back to filesystem publish. |

## 8. Idempotency and audit

### Idempotency key (suggested composition)

```text
tenant_id + pack_id + channel + target_account_id + content_hash
```

The same key must not produce a second successful live post. Dry-run keys must not be treated as live success.

### Publish logs must record

- `tenant_id`
- `pack_id`
- channel
- target account
- action
- status
- dry_run vs live
- external post id / url (when available)
- error if failed (redacted)
- actor
- timestamp
- adapter version

Write-back to Marketing publish logs is mandatory for live publish attempts that leave the Flexity boundary (success or failure). Dry-run results should also be recorded in a way that operators can audit (same log table with `dry_run` flag, or an equivalent auditable dry-run record — exact shape is an M8-D contract decision).

## 9. Roles and permissions

| Role (logical) | Allowed |
|---|---|
| **provider_owner / admin** | Configure connected accounts; set storage resource profile (within tariff); revoke connections |
| **content editor** | Prepare packs, texts, media metadata |
| **approver** | Approve packs |
| **publisher** | Execute dry-run and live publish for approved packs only |

**Hard rule:** no live publish for unapproved packs. Role names may map to existing Flexity RBAC codes in later plans; the separation of duties above is binding.

## 10. M8 implementation gates

### M8-B — Connected Accounts model

| | |
|---|---|
| **Scope** | Dedicated Marketing Channel Connection model/API: tenant, provider, account identifiers, scopes, health, `secret_ref`, uniqueness, permissions, audit of connect/revoke |
| **Out of scope** | Real provider OAuth UX polish; live publish; Telegram adapter; storage bytes; vault product selection beyond reference field |
| **Migration** | Expected (new table(s) / columns) — only after separate HQ-approved implementation plan |
| **Tests** | Tenant isolation, uniqueness, secret never in API responses, permission checks, audit events |
| **Deploy risk** | Medium (schema); low runtime if no live publish wired |

### M8-C — Secret vault boundary + storage resource profiles

| | |
|---|---|
| **Scope** | Vault abstraction (create/read-for-worker/rotate/revoke); Mode A managed storage design; Mode B public URL validation; tenant resource profile metadata; quotas/provenance policy hooks |
| **Out of scope** | Mode C client buckets; live multi-provider publish; Margosya changes |
| **Migration** | Likely for storage/resource profile fields; vault may be external config — exact choice in implementation plan |
| **Tests** | Secret boundary unit/integration; URL validation; tenant prefix isolation; redaction |
| **Deploy risk** | Medium–high (secrets + storage); no production token writes without explicit approval |

### M8-D — Publish dry-run API

| | |
|---|---|
| **Scope** | Dry-run/preflight contract; publish intent + idempotency; allow-list checks; approval gate; log/audit write-back shape; no-auto-publish default |
| **Out of scope** | Provider-specific live posting beyond contract stubs; bulk scheduler |
| **Migration** | Possibly queue/attempt tables — only if required by approved plan |
| **Tests** | Unapproved pack blocked; unhealthy connection blocked; idempotency; dry_run vs live distinction |
| **Deploy risk** | Medium; must remain fail-closed (no accidental live) |

### M8-E — Telegram adapter pilot

| | |
|---|---|
| **Scope** | One tenant-scoped Telegram adapter using Channel Connection + vault ref + Cabinet texts/media + dry-run + explicit publish + log write-back |
| **Out of scope** | Legacy Margosya bulk scanner; YAML/Git mutation; other providers; auto-schedule |
| **Migration** | Preferably none beyond prior M8-B/C/D; adapter code only |
| **Tests** | Dry-run no side effects; idempotency; wrong-tenant refusal; redacted errors |
| **Deploy risk** | High if live-enabled; must be gated per tenant and HQ-approved |

### M8-F — Client setup UI

| | |
|---|---|
| **Scope** | Owner/admin onboarding: enable Marketing, choose storage mode, connect account, health check, quota/settings, dry-run, role assignment, audit completion |
| **Out of scope** | Full marketing editor redesign; provider marketing OAuth for all platforms |
| **Migration** | Unlikely if APIs exist; frontend/console only preferred |
| **Tests** | Permission-gated screens; secrets never rendered; happy-path dry-run |
| **Deploy risk** | Medium (console); no live publish button until M8-D/E gates pass |

### M8-G — Provider adapters: Threads / TikTok / Instagram

| | |
|---|---|
| **Scope** | Per-provider adapters after shared foundation proven; each with own auth/media/reconciliation review |
| **Out of scope** | Until provider-specific auth/media flow is HQ-approved; no TikTok/Instagram in first MVP bridge |
| **Migration** | Provider-specific metadata only as needed |
| **Tests** | Provider contract tests + shared idempotency/audit suite |
| **Deploy risk** | High per provider; isolated enablement |

## 11. Explicit non-goals

- No automatic bulk publish.
- No Margosya legacy live pipeline as production Publish Bridge.
- No Git/YAML mutation by adapters for DB-backed packs.
- No plaintext token storage.
- No TikTok / Instagram adapter work until provider-specific auth/media flow is approved.
- No client-owned bucket (Mode C) support in first MVP.
- No hardcoded Asem tokens as a multi-tenant shortcut.
- No treating historical-publish reconciliation APIs as a live publish bridge.

## 12. Recommendation for next implementation slice

**Recommended first implementation slice after this ADR:**

> **M8-B — Connected Accounts model + secret reference schema**

Not the Telegram adapter yet.

**Why:**

- A Telegram (or any) adapter cannot safely run without a tenant-scoped connected account record and a vault reference boundary.
- Implementing the adapter first would recreate the forbidden shortcuts: shared tokens, plaintext credentials, or legacy Margosya/Git paths.
- M8-B creates the durable multi-tenant foundation; M8-C binds vault/storage; M8-D binds dry-run/publish safety; only then M8-E pilots Telegram.

**Next documentation step:** produce a narrow M8-B implementation plan (exact models, migration policy, API scope, tests, rollback) and wait for HQ approval before any code.

## 13. References

- `docs/ai/research/2026-07-15-m8-client-owned-publish-resources-architecture-research.md`
- `docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md`
- `docs/ai/plans/2026-07-03-marketing-content-cabinet-product-tz.md`
- `docs/ai/plans/2026-07-09-marketing-cabinet-data-model-draft.md`
- `docs/FLEXITY_HQ_STRUCTURE_CONTENT_CABINET_PLAN.md`
- `docs/ai/research/2026-07-09-margosya-to-cabinet-audit.md`

## 14. Final checks

- Documentation only.
- No code, migrations, API/DB writes, deploy, env changes.
- No secret disclosure, token handling, publish/export, Margosya execution, or provider integration implementation.
- No commit/push required by this ADR alone.
