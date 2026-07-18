# Design Appendix: M8-D Gate D1 — Shared publish contract (draft)

**Date:** 2026-07-16
**Status:** **DRAFT — NOT APPROVED / NO CODE**
**Parent plan:** `docs/ai/plans/2026-07-16-m8-d-multi-network-publishing-core-plan.md`
**D0 research:** `docs/ai/research/2026-07-16-m8-d0-margosya-failure-reuse-audit.md`
**Depends on:** M8-B connections · M8-C1a vault · M8-C2a MediaResource/storage profiles

This appendix deepens Gate D1 only. It does not approve implementation and does not start adapters (D4/D5).

---

## 1. Why D1 exists before adapters

Margosya failure (D0) shows adapters alone are useless without:

1. **DB pack as SoT** (no filesystem required to publish);
2. **destination grants** (connection ≠ permission to post);
3. **dry-run that cannot write to providers**;
4. **idempotent publish intent** recorded before any adapter call.

D1 freezes that contract so Telegram/Instagram/Threads/TikTok adapters plug into one core.

---

## 2. Existing Flexity building blocks (reuse, do not reinvent)

| Asset | Location | D1 use |
|-------|----------|--------|
| Pack + approval + pack-level preflight | `MarketingPublicationPack`, `service/approval.py`, `preflight_rules.py` | **Keep** editorial/content preflight (M7). D1 adds **publish-readiness** dry-run orthogonal to pack preflight. |
| Channel texts | `MarketingPublicationText` + `MarketingChannel` | Payload source for TG/IG/Threads |
| Media metadata + C2a validation | `MarketingMediaAsset`, `MediaResource` | Adapter media input |
| Connections + secret_ref | `MarketingPublishingConnection` | Auth subject |
| Publish log (historical/manual) | `MarketingPublishLog` | Extend semantics for live attempts (D2 may add attempt table; D1 defines fields) |
| Audit + sanitizer | audit recorder, provider error sanitizer | Mandatory on dry-run/publish outcomes |
| Providers enum | `MarketingPublishingProvider` includes **TIKTOK** | Connection layer ready |

### Gap already visible (must resolve in D1 design, not silently)

| Gap | Evidence | D1 decision needed |
|-----|----------|-------------------|
| `MarketingChannel` has TG/IG/Threads/Insights — **no TikTok** | `enums.py` | Add channel enum + pack text role **or** treat TikTok as provider-only media publish without pack text channel — HQ choose |
| Pack preflight ≠ provider dry-run | M7 preflight is content rules | Separate `publish_dry_run` result object |
| No destination grant entity | Connections only | New grant model (below) |
| No idempotency key on publish | Logs are post-hoc / historical | New intent/attempt fields |
| Log `error_message` may hold raw text today | `MarketingPublishLog` | Enforce sanitizer-only writes for live path |

---

## 3. Proposed D1 domain objects (names illustrative)

### 3.1 Destination grant

Explicit allow-list entry:

| Field | Notes |
|-------|-------|
| `tenant_id` | Required |
| `connection_id` | FK to publishing connection |
| `provider` | Denormalized from connection for query ease |
| `destination_type` | e.g. `telegram_chat`, `instagram_user`, `threads_user`, `tiktok_user` |
| `destination_external_id` | chat/page/user id — **non-secret** |
| `display_name` | Operator label |
| `status` | `ACTIVE` / `DISABLED` |
| `allowed_actions` | e.g. `publish_text`, `publish_image`, `publish_video` |
| `created_by` / audit | Standard |

**Rules:**

- Connection `ACTIVE` + secret bound **does not** imply any grant.
- Publish intent **must** reference exactly one `ACTIVE` grant for that connection.
- Grant target should match connection account identity where provider requires it (document per-provider in D4/D5).

### 3.2 Publish dry-run request / result

**Input (conceptual):**

- `tenant_id`, `pack_id`
- `connection_id`, `destination_grant_id`
- `channels` / provider selection
- optional `scheduled_at` + timezone (validation only in D1)
- content version stamp (pack `updated_at` or hash)

**Checks (no provider write, no token refresh):**

1. Pack `approval_status=APPROVED` (or HQ-agreed equivalent).
2. Pack content preflight `PASSED` (reuse M7) — or explicit waive policy (default: required).
3. Grant ACTIVE and belongs to tenant + connection.
4. Connection status/token_status gates: dry-run may run when secret present; **must not** set `token_status=VALID` from stub health.
5. Texts present for selected text channels; length limits from legacy algorithms (see §5).
6. Media: for IG/TikTok, `MediaResource` resolvable; Mode B URL registration rules; size/mime from profile.
7. Idempotency preview: compute canonical key; report if key already finalized.
8. Sanitized report JSON stored (pack-level or intent-level — prefer intent-level when attempt table exists in D2).

**Output:** `ok` + structured issue codes (stable strings, not raw provider text).

### 3.3 Publish intent (explicit)

| Field | Notes |
|-------|-------|
| `idempotency_key` | Unique per `(tenant_id, key)` |
| `pack_id`, `grant_id`, `connection_id` | Required |
| `dry_run_id` / fingerprint | Must match last successful dry-run within TTL (HQ: propose 24h) |
| `status` | `accepted` / `in_progress` / `succeeded` / `failed` / `cancelled` |
| `content_fingerprint` | Detect stale content after dry-run |

**Live adapter call is out of D1 code scope** — D1 only defines acceptance rules so D2/D4 cannot bypass them.

---

## 4. Relationship: M7 preflight vs D1 dry-run vs live publish

```text
M7 pack preflight (content quality)
        │
        ▼
D1 publish dry-run (grants + connection + media delivery + limits)
        │
        ▼
D2 schedule / attempt / retry
        │
        ▼
D4/D5 adapter live call
        │
        ▼
MarketingPublishLog + audit (+ analytics hook)
```

No arrow may skip grants or dry-run for live publish.

---

## 5. Legacy algorithm contracts to port later (B-class) — freeze for adapters

Extracted from Flexity scripts (read-only). D4/D5 implement against **verified** provider docs; numbers below are **legacy evidence**, not final policy.

### Telegram (`publish_telegram.py`)

- Eligibility: pack `status=approved`; `publish.telegram.enabled`; not yet `published_at`; `publish_at` due.
- Action: `sendMessage` to chat id.
- Limit: text length (Margosya preflight warns >4096).
- Result: message id → external id.
- **D1 dry-run:** validate text presence + length + grant chat id shape; **do not** call Bot API.

### Instagram (`publish_instagram_live.py`)

- Graph base evidence: `https://graph.facebook.com/v21.0`.
- Flow: create media container → `media_publish`.
- Secrets names: `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN`.
- Media: HTTPS `image_url` / carousel items / optional video_url.
- Errors: redact `access_token=`.
- **D1 dry-run:** validate MediaResource → public or temporary HTTPS URL strategy; caption source; **no** Graph POST.

### Threads (`publish_threads_live.py`)

- Base evidence: `https://graph.threads.net/v1.0`.
- Text chunk max **500**; reply chain for long posts.
- Secrets: `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN`.
- **D1 dry-run:** chunk plan + grant; **no** live create/publish.

### TikTok (`publish_tiktok_live.py`)

- Base evidence: `https://open.tiktokapis.com/v2` + `post/publish/video/init/`.
- Secret: `TIKTOK_ACCESS_TOKEN`.
- Script is narrower than full upload — D5 likely expands.
- **D1 dry-run:** video MediaResource present + mime/size; flag “upload path incomplete until D5 design”.

---

## 6. Fixture sources for Gate D3 (inventory only)

Filesystem packs under `landing/content/content-packs/` (16 `pack.yml` found) are **fixtures/reference**, not live SoT:

- Use sanitized copies for golden eligibility tests.
- Never load tokens from workflows into tests.
- Prefer reconstructing fixtures from **public structure** (status, publish_at, channel files) without copying production secrets.

---

## 7. Proposed D1 implementation slices (after HQ approval only)

| Slice | Scope | Forbidden |
|-------|-------|-----------|
| D1a | Destination grant model + migration + service + tests | Adapters, live publish |
| D1b | Publish dry-run service + API + report schema | Provider HTTP writes |
| D1c | Publish intent + idempotency unique constraint | Worker/scheduler (D2) |
| D1d | Wire audit + sanitizer on dry-run/intent | Margosya, GHA dispatch |

**Suggested first code slice after approval:** **D1a** only (smallest, testable, no provider risk).

---

## 8. Open HQ decisions (blockers for code)

1. TikTok as `MarketingChannel` vs provider-only media publish.
2. Dry-run TTL and whether content fingerprint mismatch forces re-dry-run.
3. Whether Insights site publish stays out of M8-D core (recommended: separate track).
4. Whether D2 attempt table is new entity or extension of `MarketingPublishLog`.
5. Optional read-only server probe for Margosya (still not required for D1 design).

---

## 9. Tests planned for D1 (when approved)

- Grant: cross-tenant reject; disabled grant reject; active grant allow.
- Dry-run: no outbound HTTP (monkeypatch/network guard).
- Dry-run fails without approval/preflight/media as designed.
- Idempotency: duplicate key reject after success.
- Audit entries contain no token material.
- Migration chain + disposable PG smoke when schema lands.

---

## 10. Approval

**Waiting for:** Gate D0 acceptance (if not already) + **explicit HQ approval to start D1a**.

**Not started:** any production code, migration, adapter, Margosya repair, push.
