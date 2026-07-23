# Plan / Research Gate + B2 Design Lock: M8-B2 Production Secret Provider

**Date:** 2026-07-23
**Status:** **B2 DESIGN LOCKED** + **implementation present locally** (worktree `marketing-m8b-http-clean`, baseline `a11ef00`) — **still no commit / no Hoster KEK ceremony / no production migrate**
**Category:** `platform_core` (envelope adapter) — Design Lock docs remain authoritative
**Risk:** high (secrets / single-VPS ops)
**HQ research acceptance:** Option 2 — application-level envelope-encrypted `SecretVaultPort` on Hoster Astana VPS; ciphertext in PostgreSQL; KEK outside DB
**Related:** M8-B HTTP clean-main `a11ef00` on `feature/marketing-m8b-http-clean-main` (parent `308b804`)
**Implementation report:** `docs/ai/reports/2026-07-23-m8-b2-envelope-secret-vault-implementation-report.md`

## Goal

Lock crypto, envelope, AAD, persistence, lifecycle, KEK ops, threat boundary, tests, and sequencing for the accepted Option 2 adapter — without writing code or migrations yet.

## Hosting / product constraints (locked)

| Constraint | Fact |
|---|---|
| Production host | Hoster.kz VPS, Astana — Ubuntu 24.04, **2 vCPU / 4 GB RAM / 100 GB** |
| Data residency | Production secrets on KZ infrastructure |
| Store | **PostgreSQL** ciphertext table (same Core DB) |
| KEK | **Outside** PostgreSQL (systemd credential / root-owned file) |
| AWS Secrets Manager | Dev/staging **outside KZ only** — **not** production |
| Interim runtime | Production connect/rotate fail-closed `503` until approved adapter + KEK ceremony |
| Portability | Keep `SecretVaultPort` + opaque `secret_ref`; adapter swappable later (e.g. OpenBao) |

## Non-goals (this Design Lock slice)

- No code, deps, migrations, deploy, server/AWS/Hoster changes.
- No M8-D / Telegram / frontend.
- No new documents (this file only).
- No commit/push.

---

## B2 Design Lock (mandatory)

### 1. Crypto primitive — LOCKED

| Rule | Decision |
|---|---|
| Library | **PyCA `cryptography`** only (vetted); no home-grown crypto |
| Algorithm | **AES-256-GCM** for both payload ciphertext and DEK wrap |
| DEK | Fresh **random 256-bit** DEK **per secret version** |
| Nonces | **Separate random nonces**: one for payload GCM, one for wrapped-DEK GCM; never reuse nonce with same key |
| Forbidden | Self-written crypto; **deterministic** encryption; ECB; “encrypt with KEK directly” without per-version DEK; custom MAC constructions |

### 2. Envelope model — LOCKED

```text
plaintext  --AES-256-GCM(DEK, nonce_c, AAD)--> ciphertext
DEK        --AES-256-GCM(KEK, nonce_w, AAD')--> wrapped_dek
```

| Rule | Decision |
|---|---|
| Plaintext | Encrypted only with per-version DEK |
| DEK | Wrapped only with current KEK; DEK never persisted unwrapped |
| KEK | **Never** stored in PostgreSQL (or in any DB backup that sits next to ciphertext without separation policy) |
| DB may store | ciphertext, nonces, wrapped_dek, algorithm / schema / `kek_version` metadata, opaque logical refs (via existing `SecretRef` path + row keys) |
| DB must not store | plaintext, raw DEK, KEK, social tokens, API-visible `secret_ref` strings in audit payloads |

### 3. AAD binding — LOCKED

Authenticated Associated Data **MUST** bind ciphertext (and wrapped DEK) to:

| AAD field | Source |
|---|---|
| `tenant_id` | UUID |
| `connection_id` | publishing connection owner id (matches `SecretRef.connection_id`) |
| `version` | secret version int (≥1) |
| `purpose` | e.g. `publishing_connection` (`SecretStoreMetadata.purpose`) |

Canonical encoding (implementation must freeze one byte layout, e.g. length-prefixed UTF-8 / fixed UUID bytes + uint32 version + purpose string) and cover it with tests.

**Fail-closed:** decrypt with mismatched tenant/connection/version/purpose AAD → authentication failure → `SecretVaultError` (no plaintext). Cross-tenant ciphertext or `secret_ref` reuse **must not** succeed.

### 4. KEK versioning — LOCKED

| Rule | Decision |
|---|---|
| `kek_version` | Non-secret integer (or short opaque id) stored **per row** in PostgreSQL |
| Rotation | Support **future KEK rotation** by wrapping new DEKs (and optionally re-wrapping existing DEKs) under `kek_version+1` **without** forcing reconnect of all accounts when old KEK still loaded |
| Runtime map | Process loads one or more KEKs keyed by `kek_version`; encrypt uses **current** version; decrypt selects by row.`kek_version` |
| Unknown / missing KEK version | **Fail-closed** (no decrypt, no silent fallback to InMemory) |
| Total KEK loss | **Controlled reconnect procedure**: mark connections secret-less / require tenant reconnect; no plaintext recovery possible |

### 5. Exact persistence model — LOCKED (table proposed; migration **not** created)

**Table name:** `secret_envelope_versions`

**Purpose:** physical store for `SecretVaultPort` envelope adapter (platform secrets core; first consumer = Marketing publishing connections).

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | NO | PK |
| `tenant_id` | UUID | NO | AAD + isolation |
| `connection_id` | UUID | NO | owner id (= publishing connection id for purpose `publishing_connection`) |
| `purpose` | VARCHAR(64) | NO | e.g. `publishing_connection` |
| `version` | INTEGER | NO | ≥ 1; aligns with `SecretRef.version` |
| `state` | VARCHAR(32) | NO | `pending` \| `active` \| `deactivated` |
| `algorithm` | VARCHAR(32) | NO | fixed `aes-256-gcm` |
| `crypto_schema_version` | INTEGER | NO | envelope format version (start at `1`) |
| `kek_version` | INTEGER | NO | non-secret KEK id used to wrap DEK |
| `ciphertext` | BYTEA | NO | AES-GCM ciphertext (+tag per library convention) |
| `ciphertext_nonce` | BYTEA | NO | random; unique per encrypt under DEK |
| `wrapped_dek` | BYTEA | NO | DEK wrapped under KEK |
| `wrapped_dek_nonce` | BYTEA | NO | random; unique per wrap under KEK |
| `created_at` | TIMESTAMPTZ | NO | |
| `updated_at` | TIMESTAMPTZ | NO | |

**Constraints / indexes (proposed):**

- PK: `id`
- **UNIQUE** `(tenant_id, connection_id, purpose, version)`
- CHECK `version >= 1`
- CHECK `state IN ('pending','active','deactivated')`
- CHECK `algorithm = 'aes-256-gcm'`
- CHECK `crypto_schema_version >= 1`
- CHECK `kek_version >= 1`
- CHECK `octet_length(ciphertext_nonce) >= 12` (and same for `wrapped_dek_nonce`) — exact length locked in impl tests (96-bit GCM nonce recommended)
- INDEX `(tenant_id, connection_id, purpose, state)`
- INDEX `(tenant_id, connection_id, purpose, version)` (supports unique)

**No FK** to `marketing_publishing_connections` (keeps vault adapter portable; logical bind via `SecretRef` + lifecycle service).

**Logical ref:** continue existing opaque
`secret://marketing/tenants/{tenant_id}/publishing-connections/{connection_id}/versions/{version}`
stored on connection row as today; envelope row is the ciphertext backing store.

**Migration impact:** **Yes — required** for PostgreSQL store.
**Revision id / `down_revision`:** **`0025_secret_envelope_versions`** ← **`0024_task_run_automation_key`** (landed locally; not committed; do not run on production without ops approval).

### 6. Secret lifecycle — LOCKED

Align with `SecretVaultPort`:

| Method | Behavior |
|---|---|
| `store_secret` | New `version` row: generate DEK+nonces; encrypt; wrap DEK; persist `state=pending`; return `SecretRef` |
| `read_secret` | Load row; verify AAD/ownership; unwrap DEK with `kek_version`; decrypt; return `SecretPlaintext` **only in-process** for narrow adapter use |
| `activate_version` | `pending → active` after successful DB bind |
| `deactivate_version` | Soft-revoke: `deactivated`; subsequent read fail-closed |
| `delete_version` | Hard-delete row (compensation / orphan cleanup) |
| `confirm_inactive` / `version_exists` / `get_version_state` | As port semantics |

**Compensation (bind/rotate failure):**

1. On failed bind after `store_secret`: `delete_version` (or deactivate + delete) for the orphan pending version.
2. On failed rotate: do not activate new version; delete orphan pending; leave prior active intact.
3. Periodic/safe orphan cleanup: `pending` older than TTL without bind → delete (impl detail in code plan).

**Redaction:** never emit plaintext, DEK, KEK, or `secret_ref` strings in API responses, audit payloads, or logs (continue `has_secret` only on HTTP).

### 7. KEK operations — LOCKED

| Topic | Decision |
|---|---|
| Delivery | Prefer **systemd `LoadCredential=`** into `coreops` (or equivalent unit); fallback: **root-owned file** outside app tree |
| App access | Service user **read-only** on credential path |
| Mode/owner | File: `root:root` or `root:<service>`, mode **`0600`** (dir `0700`); not world-readable |
| Generation | Offline/`umask 077`; **no** stdout/log/shell-history leakage of key material |
| Offline backup | Separate **encrypted** offline backup of KEK material; HQ-owned; **not** co-stored with DB dump |
| Restore drill | Documented restore of KEK into credential slot + app start smoke **without** printing key |
| Forbidden locations | git repo, committed `.env`, PostgreSQL, same tarball/snapshot as DB backup, chat/tickets |

### 8. Threat boundary — LOCKED

| Boundary | Statement |
|---|---|
| DB-only leak | Ciphertext + wrapped DEK **without KEK** does **not** disclose social tokens |
| Full root / runtime compromise | Attacker with host root or process memory **can** obtain KEK + decrypt active secrets — **accepted risk** of single-VPS stage |
| Not a substitute | Envelope adapter **does not** replace host hardening, SSH discipline, backups, monitoring, or least privilege |
| Phase-2 | OpenBao/separate barrier remains optional later if HQ wants stronger separation |

### 9. Test matrix — LOCKED (required before production enable)

| # | Case |
|---|---|
| 1 | Encrypt/decrypt round-trip |
| 2 | Identical plaintext → **different** ciphertext (random DEK/nonces) |
| 3 | AAD tenant (or connection/version/purpose) mismatch → fail-closed |
| 4 | Tampered ciphertext / tag → fail-closed |
| 5 | Missing / wrong KEK or unknown `kek_version` → fail-closed |
| 6 | DEK per-version uniqueness; KEK rotation path (encrypt under vN+1, decrypt old vN while both loaded) |
| 7 | Bind/rotate/disconnect compensation + orphan pending cleanup |
| 8 | Redaction: API/audit/logs have no plaintext / `secret_ref` / key material |
| 9 | Production-like env without vault/KEK → HTTP **503** `secret_vault_unavailable` |
| 10 | Backup/restore fixture asserts ciphertext-only restore; **no plaintext output** in test logs |

Fixtures: synthetic secrets only — never real social tokens.

### 10. Sequencing — LOCKED

```text
B2 Design Lock (this document)
  → separate HQ approval: code + migration (from then-current main head)
  → local tests (matrix §9)
  → Hoster KEK ceremony as separate ops gate
  → stage lifecycle smoke (connect/rotate/disconnect) WITHOUT social publish
  → M8-D destinations
  → M8-E Telegram
```

**Stop:** do not start M8-D/E or live social publish until vault stage smoke is green under HQ ops gate.

---

## Exact implementation file manifest (proposed; not created)

| Path | Role |
|---|---|
| `backend/app/core/secrets/adapters/envelope_pg.py` (name TBD) | `SecretVaultPort` PostgreSQL envelope adapter |
| `backend/app/core/secrets/envelope_crypto.py` (name TBD) | AES-256-GCM + AAD encode helpers (PyCA only) |
| `backend/app/core/secrets/kek_provider.py` (name TBD) | Load KEK map from systemd credential / file; versioned |
| `backend/app/modules/models.py` or secrets models module | ORM for `secret_envelope_versions` |
| `backend/alembic/versions/<TBD>_secret_envelope_versions.py` | **Created only after HQ code+migration approval**; `down_revision` = then-current main head |
| `backend/app/modules/marketing/deps.py` | Wire envelope adapter for staging/production; keep InMemory allow-list |
| `backend/tests/test_secret_envelope_vault.py` (name TBD) | Matrix §9 |
| Existing | `tests/test_marketing_publishing_connections_api.py` / lifecycle tests — extend for envelope DI |

**Intentionally not in first impl:** AWS adapter, OpenBao client, Telegram, destinations, frontend.

---

## Research background (accepted Option 2; condensed)

OpenBao/Vault deferred (ops/RAM on shared 4G). systemd alone = KEK delivery only. No ready managed KZ Secrets Manager. AWS SM non-prod only.

---

## Unresolved questions (non-blocking for Design Lock; resolve in code/ops plans)

1. Exact credential filename / systemd unit drop-in naming on Hoster (`coreops.service`).
2. Whether staging on same VPS shares KEK ring or uses separate `kek_version` namespace.
3. Orphan `pending` TTL: **15 minutes** (default `secret_envelope_pending_ttl_seconds=900`).
4. `cryptography` declared as direct dependency `cryptography>=41,<46` in `backend/pyproject.toml`.
5. Multi-KEK load format: **JSON ring** (`schema_version`, `active_kek_version`, `keys` map of version → base64-32-bytes).

---

## HQ checklists

### Research (done)

- [x] Accept Option 2 envelope adapter on Hoster Astana
- [x] Ciphertext in PostgreSQL; KEK outside DB
- [x] AWS SM not production

### Design Lock (this slice)

- [x] Crypto / envelope / AAD / KEK versioning / table / lifecycle / KEK ops / threat / tests / sequencing locked in this file

### Still required before production enable

- [x] Separate HQ approval: **implementation + migration** (landed locally; awaiting commit)
- [ ] Separate ops approval: **Hoster KEK ceremony**
- [ ] Assign KEK recovery owner
- [ ] Production/staging Alembic upgrade of `0025_secret_envelope_versions`
- [ ] Commit / security review / merge gate

## Approval

**Design Lock status:** **DESIGN LOCKED**

**Implementation status:** **present locally** on `feature/marketing-m8b-http-clean-main` (no commit). Migration revision `0025_secret_envelope_versions` → `down_revision = 0024_task_run_automation_key`.

**Hoster KEK ceremony and production migrate remain blocked until separate ops approval.**
