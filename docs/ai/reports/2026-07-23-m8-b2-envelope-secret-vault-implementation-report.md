# M8-B2 Implementation Report: Envelope-encrypted SecretVaultPort

**Date:** 2026-07-23
**Branch:** `feature/marketing-m8b-http-clean-main`
**Baseline HEAD:** `a11ef00942c220ecebfa033cdc316698ab8c7298`
**Status:** Implementation present **locally** — **no commit / no push / no Hoster deploy**

## Summary

Landed Option 2 envelope adapter: AES-256-GCM per-version DEK, KEK ring outside PostgreSQL, ciphertext in `secret_envelope_versions`, Marketing DI fail-closed to HTTP 503 when production/staging lacks a valid KEK/adapter (no silent InMemory fallback).

## Files created

| Path | Role |
|---|---|
| `backend/app/core/secrets/envelope_crypto.py` | PyCA AES-256-GCM + canonical AAD |
| `backend/app/core/secrets/kek_provider.py` | KEK ring load/validate + ephemeral test helpers |
| `backend/app/core/secrets/models.py` | ORM `SecretEnvelopeVersion` (no marketing FK) |
| `backend/app/core/secrets/adapters/envelope_pg.py` | Full `SecretVaultPort` + compensation/TTL cleanup |
| `backend/alembic/versions/20260723_0025_secret_envelope_versions.py` | Migration `0025_secret_envelope_versions` |
| `backend/tests/test_secret_envelope_vault.py` | Design Lock §9 matrix |
| `backend/tests/test_migration_0025_secret_envelope_versions.py` | Single-head + import/metadata checks |
| `docs/ai/reports/2026-07-23-m8-b2-envelope-secret-vault-implementation-report.md` | This report |

## Files modified

| Path | Change |
|---|---|
| `backend/app/core/config.py` | Vault/KEK config keys (no secret defaults) |
| `backend/app/modules/marketing/deps.py` | Explicit adapter selection (`auto` / `in_memory` / `envelope_pg`) |
| `backend/app/core/secrets/__init__.py` | Export model |
| `backend/app/core/secrets/adapters/__init__.py` | Export envelope adapter |
| `backend/app/modules/models.py` | Register `SecretEnvelopeVersion` for metadata |
| `backend/pyproject.toml` | Direct `cryptography>=41,<46` |
| `backend/tests/test_migration_0024_task_run_automation_key.py` | Head assertion extensible for 0025 |
| `docs/ai/plans/2026-07-23-m8-b2-production-secret-provider-plan.md` | Status: implementation local |

## Migration

- **revision:** `0025_secret_envelope_versions` (≤32 chars)
- **down_revision:** `0024_task_run_automation_key`
- **Single Alembic head:** `0025_secret_envelope_versions`
- Table `secret_envelope_versions` with Design Lock columns, UNIQUE owner+version, state/algorithm/schema/kek/nonce CHECKs, indexes; **no FK** to marketing.

## Config keys added

| Key | Purpose |
|---|---|
| `secret_vault_adapter` | `auto` (default) \| `in_memory` \| `envelope_pg` |
| `secret_kek_credential_path` | Absolute path to KEK ring JSON |
| `secret_kek_credentials_dir` | systemd-style credentials directory (or relies on `CREDENTIALS_DIRECTORY` env when name set) |
| `secret_kek_credential_name` | Basename inside credentials dir |
| `secret_envelope_pending_ttl_seconds` | Orphan pending TTL (default **900** = 15 min) |

## Crypto / AAD notes (for security review)

- Library: PyCA `cryptography` AESGCM only.
- Fresh 256-bit DEK per version; separate 96-bit nonces for payload and wrap.
- Canonical AAD magic `fxse1` + UUID bytes + uint32 version + length-prefixed purpose + uint32 crypto_schema_version (documented in `envelope_crypto` module docstring; covered by tests).
- Fail-closed generic `SecretVaultError` codes on AAD/tag/KEK/algorithm mismatch — no key material in messages.
- KEK ring JSON: `schema_version`, `active_kek_version`, `keys` map → base64 of exactly 32 bytes.

## Unresolved ops items

1. Hoster KEK ceremony (systemd `LoadCredential=` / root-owned file, offline backup, restore drill).
2. Exact credential filename / unit drop-in on `coreops.service`.
3. Whether staging on same VPS shares KEK ring or separate namespace.
4. Production Alembic upgrade approval for `0025`.
5. Assign KEK recovery owner.
6. Commit / PR after security review.

## Intentionally not done

- Commit / push
- Hoster/server changes
- AWS Secrets Manager / OpenBao
- M8-D / Telegram / frontend
- Real KEKs or social tokens in repo/tests
