# Report — M8-A Publish Bridge architecture decision

**Date:** 2026-07-15
**Project:** Flexity / `coreops-platform`
**HQ gate:** `APPROVED: M8-A Publish Bridge architecture decision`
**Scope:** documentation only — architecture decision, threat model, implementation gates
**Parent research:** `docs/ai/research/2026-07-15-m8-client-owned-publish-resources-architecture-research.md`
**Parent plan:** `docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md`

---

## 1. Status

## ✅ COMPLETE — M8-A ACCEPTED FOR PLANNING / IMPLEMENTATION GATING

Formal ADR created. M8 plan updated to reference ADR acceptance. No code, migrations, secrets, publish, deploy, or commit performed.

## 2. ADR path

`docs/architecture/decisions/2026-07-15-m8-publish-bridge-client-owned-resources-adr.md`

## 3. Updated plan path

`docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md`

## 4. Key decisions

1. Publish Bridge is **tenant-scoped**.
2. **Client owns** publishing accounts; Flexity holds delegated capability only.
3. Flexity stores **non-secret metadata + vault references** only.
4. Social tokens live in a **secret vault / secret manager boundary**, not plaintext DB.
5. Generic `credentials_json` is **not** an approved social-token vault.
6. Storage: Flexity-managed default; client public URLs early; client buckets deferred.
7. Margosya legacy publishers are **not** production source of truth.
8. Live publish requires: approved pack, preflight, channel allow-list, dry-run, idempotency, audit, Marketing publish-log write-back.
9. Provider adapters are separate from Marketing core state.
10. Adapters must **not** mutate YAML/content-pack files or Git for DB-backed packs.

Forbidden shortcuts explicitly blocked: hardcoded Asem tokens; legacy Margosya file pipeline as production bridge; YAML as SoT; Git side effects; plaintext tokens; tenant-crossing tokens; direct publish without dry-run/approval/audit.

## 5. Ownership modes

| Mode | Name | MVP? |
|---|---|---|
| **A** | Flexity-managed vault + managed object storage | Yes — default |
| **B** | Client-provided public HTTPS URLs (metadata only) | Yes — early |
| **C** | Client-owned storage bucket | Deferred — needs IAM/lifecycle/support design |

## 6. Secret boundary

**DB may store:** provider name, account display name, channel ID, tenant ID, token health status, vault reference, scopes, `expires_at`, `last_checked_at`.

**DB must not store plaintext:** access tokens, refresh tokens, client secrets, bot tokens, private keys.

Secrets also forbidden in Marketing metadata, logs (unredacted), Git, exports, and frontend state.

## 7. Storage policy

- **Default:** Flexity-managed tenant-prefixed object storage with signed previews and public publishing URLs only when a channel requires them.
- **Early option:** external client-owned public URLs validated and stored as metadata.
- **Later:** client-owned buckets only after separate security/ops design.
- Media provenance, MIME/size validation, quotas, retention/deletion remain required for all modes.

## 8. Threat model summary

Covered risks with mitigations in the ADR:

- token leakage
- wrong tenant publishing
- duplicate posts
- stale/revoked tokens
- wrong channel/account
- accidental bulk publish
- provider API failure
- media URL exposure
- audit gaps
- operator bypass
- legacy Margosya side effects

Primary controls: vault-only secrets, tenant isolation, idempotency, health fail-closed, role separation, no auto-bulk, no filesystem/YAML/Git fallback for production publish.

## 9. M8 gates

| Gate | Focus | Migration | Deploy risk |
|---|---|---|---|
| **M8-B** | Connected Accounts model + `secret_ref` | Expected | Medium (schema) |
| **M8-C** | Vault boundary + storage resource profiles | Likely | Medium–high |
| **M8-D** | Publish dry-run / intent contract | Possible | Medium (must stay fail-closed) |
| **M8-E** | Telegram adapter pilot | Prefer none beyond prior | High if live |
| **M8-F** | Client setup UI | Prefer none | Medium (console) |
| **M8-G** | Threads / TikTok / Instagram | Per provider | High per provider |

Each gate needs its own HQ-approved implementation plan. Non-goals for MVP: auto bulk publish, Margosya live pipeline, Git/YAML mutation, plaintext tokens, TikTok/Instagram before provider review, Mode C buckets.

## 10. Recommended next slice

**M8-B — Connected Accounts model + secret reference schema**

Not Telegram adapter yet. Adapters cannot be safe without tenant-scoped connections and a vault reference boundary first.

Next doc step: narrow M8-B implementation plan (models, migration policy, API, tests, rollback) → wait for HQ approval → then code.

## 11. What was not touched

- No production code, tests, migrations, or config.
- No API/DB writes.
- No deploy, env, secrets, token handling.
- No publish/export, Margosya execution, provider integration.
- No commit / push / stage.
- No `.env`, Nginx, systemd, or live Flask projects.

## 12. Risks

1. Starting M8-E Telegram before M8-B/C/D would recreate forbidden shortcuts.
2. Reusing `IntegrationConnection.credentials_json` would violate the accepted secret boundary.
3. Dual live paths (legacy Git/YAML + DB adapters) risk duplicate posts and split SoT.
4. Mode C client buckets remain a future security/ops burden if pulled into MVP early.
5. Vault technology choice is deferred to M8-C — must not block M8-B from defining `secret_ref` shape carefully.

## 13. Next recommended step

Request HQ approval to draft **M8-B Connected Accounts implementation plan** (documentation only). Do not start code, migrations, vault product wiring, or Telegram adapter until that plan is approved.

## Final checks

- Documentation only.
- No code changes.
- No migrations.
- No deploy.
- No secret disclosure.
- No commit/push.
