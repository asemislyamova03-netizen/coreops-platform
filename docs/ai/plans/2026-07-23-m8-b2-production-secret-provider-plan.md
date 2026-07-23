# Implementation Plan: M8-B2 Production Secret Provider (documentation only)

Date: 2026-07-23  
Status: documentation-only — **no implementation in this slice**  
Related: M8-B Publishing Connections HTTP API clean-main port (`308b804` base, source `860d904`)

## Goal

Document the follow-up decision track for a **production** secret provider after M8-B HTTP API lands on clean main with InMemory vault only in allow-listed non-production envs.

## Classification

- Project: Flexity
- Category: documentation_only (follow-up may become platform_core / universal_module)
- Risk: high (secrets / production infra) — planning only here

## Non-goals (this plan / this slice)

- **No implementation** of AWS Secrets Manager adapter in this slice
- No production vault wiring in code
- No migrations, no deploy, no Hoster/DNS/server actions
- No Telegram publish execution or destination APIs

## Explicit constraints

1. **AWS Secrets Manager** is the **only possible development/staging adapter candidate** discussed for non-KZ cloud experimentation. It is **not** approved as the production provider by this plan.
2. **Production will run on infrastructure in Kazakhstan.** Production secret storage must fit that hosting reality and local regulatory/operational constraints.
3. **Production secret-provider remains a separate HQ decision.** Engineering must not silently pick AWS (or any cloud vault) for production without that decision.
4. **`SecretVaultPort` + opaque `secret_ref` preserve portability.** The M8-B HTTP/domain layer already depends on the port and stores only opaque refs; swapping adapters must not require leaking refs into HTTP responses.
5. **NO implementation of AWS adapter in this slice** (M8-B HTTP clean-main port). Fail-closed `503 secret_vault_unavailable` outside allow-listed envs is the correct interim behavior.

## Current interim (M8-B)

| Env | Vault behavior |
| --- | --- |
| `test`, `testing`, `development`, `dev`, `local` | `InMemorySecretVault` allowed via DI |
| `staging`, `production`, unknown | fail-closed → `secret_vault_unavailable` |

API never returns `secret_ref` or plaintext; clients see `has_secret` only.

## Proposed HQ decision questions (M8-B2)

1. Which KZ-hosted secret store is acceptable for production (self-hosted vault, cloud KZ region, HSM, etc.)?
2. Is AWS Secrets Manager allowed **only** for private development/staging sandboxes outside production?
3. Who owns rotation, audit access, and break-glass procedures?
4. What is the cutover order: staging adapter → production adapter → enable connect/rotate in those envs?

## Expected future files (NOT in this slice)

- Optional: `backend/app/core/secrets/adapters/...` for an approved provider
- Optional: DI wiring in `marketing/deps.py` for staging/production after HQ approval
- Tests for the chosen adapter (no secrets in fixtures)

## Approval

Status: waiting for HQ decision before any adapter implementation.
