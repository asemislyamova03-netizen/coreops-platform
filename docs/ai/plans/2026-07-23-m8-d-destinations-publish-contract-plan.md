# Plan: M8-D Marketing Publish Destinations + Dry-run / Publish Contract

**Date:** 2026-07-23
**Type:** documentation / design gate + D1 lock
**Status:** **HQ LOCKED — D1 DONE; D2 HTTP IMPLEMENTED (no commit)**
**Category:** `universal_module` (Marketing) + `documentation_only`
**Risk:** high (live-publish adjacency; multi-tenant; secrets)

**Parents / checkpoints:**

| Item | Ref |
|---|---|
| ADR M8-A | `docs/architecture/decisions/2026-07-15-m8-publish-bridge-client-owned-resources-adr.md` |
| M8 parent plan | `docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md` |
| Prior D draft (superseded for naming/order by this gate) | `docs/ai/plans/2026-07-16-m8-d-multi-network-publishing-core-plan.md`, `…-m8-d1-shared-publish-contract-design.md` |
| D0 Margosya | `docs/ai/research/2026-07-16-m8-d0-margosya-failure-reuse-audit.md` |
| M8-B HTTP | checkpoint `a11ef00` |
| M8-B2 Envelope Vault | checkpoint `5249f04` |
| Private stage | Gate 3A GREEN; stage KEK = **fake secrets only** |
| M8-C storage | baseline in `main` (`marketing_storage_resource_profiles`, MediaResource Mode A/B) |

## Goal

Freeze the **Publish Destination** domain and the **dry-run / execute / attempt-log** contracts so that:

- Account ≠ Destination (Telegram bot ≠ chat/channel);
- Margosya is never SoT / never legacy live publisher;
- Telegram adapter starts only in **M8-E** after this gate’s approved implementation slices;
- Historical record (`M7-D`) never becomes live publish.

## Classification

| Field | Value |
|---|---|
| Project | Flexity |
| Layer | universal_module (Marketing Cabinet) |
| Required plan | documentation / design gate |
| Code | **forbidden** until separate HQ approval of a code slice (recommend **D1** first) |

## Non-goals (this gate)

- No code, migrations, deploy, DNS, Hoster KEK ceremony, real tokens, live publish.
- No Telegram / Threads / TikTok / Instagram adapters.
- No frontend.
- No ADR rewrite; no edits to other plans except this new combined file.
- No commit/push in this documentation step.

---

## Locked decisions (from ADR + HQ context)

1. **MarketingPublishingConnection** = credential / account identity (`secret_ref`, health, scopes).
2. **MarketingPublishDestination** = publish **target** allow-list entry (non-secret external id).
3. One connection → **many** destinations.
4. Every destination / attempt / log row is **tenant-scoped**; cross-tenant refs **fail-closed**.
5. Destination rows **never** store secrets / tokens / `secret_ref`.
6. Telegram **bot token account ≠ chat/channel destination**.
7. Dry-run performs **zero** provider side-effects.
8. Execute is a **separate** endpoint with **explicit idempotency key**; dry-run ≠ execute.
9. `historical_record` never calls adapters / vault plaintext / provider HTTP.
10. Margosya = optional thin client/helper later; **not** state owner.
11. Media: Mode A Flexity-managed default; Mode B public HTTPS URLs; **Mode C private buckets out of M8-D**.
12. Stage KEK / fake secrets do **not** authorize production publish.

---

## 1. Domain model

### Entities

| Entity | Role |
|---|---|
| `MarketingPublishingConnection` | Existing M8-B account / credential subject |
| `MarketingPublishDestination` | **New** — target allow-list (chat/channel/page/user) |
| `MarketingPublishDryRun` | **New** — immutable validation snapshot (optional table or pack-scoped record; prefer dedicated table) |
| `MarketingPublishIntent` | **New** — accepted execute intent keyed by idempotency |
| `MarketingPublishAttempt` | **New** — per try lifecycle (or strongly typed extension of log; **prefer new table**) |
| `MarketingPublishLog` | Existing — keep for historical; live path writes **sanitized** outcomes (may link `attempt_id`) |

### Relationship rules

```text
Tenant
  └─ MarketingPublishingConnection (1)
        └─ MarketingPublishDestination (N)   # allow-list targets
  └─ Pack (+ texts/media/approval)
        └─ DryRun (N) → Intent (1 per idempotency_key) → Attempt (N) → Log rows
```

- Publish intent **must** reference: `tenant_id`, `pack_id`, `connection_id`, `destination_id`, `idempotency_key`.
- Destination must belong to same `tenant_id` **and** `connection_id`.
- Connection `ACTIVE` + `has_secret` **does not** imply any destination is usable.

### Destination types (initial enum)

| `destination_type` | Provider | Notes |
|---|---|---|
| `telegram_chat` | telegram | chat/channel/supergroup id — **not** bot id |
| `instagram_user` | instagram | IG business/user target |
| `threads_user` | threads | |
| `tiktok_user` | tiktok | provider exists; pack `MarketingChannel` TikTok still HQ-open |

---

## 2. Destination lifecycle

### States

```text
enabled ⇄ disabled → archived
         └─ validation_status: unchecked | valid | invalid | unavailable
```

**HQ statuses:** `enabled` | `disabled` | `archived` (no normal hard delete).
Create defaults to `enabled` (capability-disabled types such as TikTok create as `disabled`) with `validation_status=unchecked`.

### Operations

| Op | Effect |
|---|---|
| create | Insert destination bound to connection; no secret fields; metadata secret-key boundary enforced |
| update | Non-secret metadata / display_name; `external_id` only while `unchecked` **and** `identity_locked_at IS NULL` |
| enable | `disabled → enabled` (blocked for capability-disabled types) |
| disable | `enabled → disabled` (does not unlock identity) |
| archive | Terminal; cannot be selected for new dry-run/execute (does not unlock identity) |
| validate | Structural first → updates `validation_status`; first `valid` sets `identity_locked_at` once; reset to `unchecked` does **not** clear lock; provider validate needs adapter (later) |

### Separation of concerns

| Signal | Meaning |
|---|---|
| Connection `token_status` / health-check | Credential health (M8-B; stub must not invent `VALID`) |
| Destination `validation_status` | Target identity / allow-list validity |
| Dry-run result | Publish-readiness of pack+destination+connection **together** |

Cross-tenant: any destination_id / connection_id from another tenant → **404** (not 403) for get; mutations fail-closed.

---

## 3. API (proposed)

Base: `/api/v1/marketing`
Auth: Bearer + `X-Tenant-ID` + `require_module("marketing")`

### Destination endpoints

| Method | Path | RBAC |
|---|---|---|
| GET | `/publish-destinations` | MEMBER+ |
| GET | `/publish-destinations/{id}` | MEMBER+ |
| POST | `/publish-destinations` | OWNER/ADMIN (+ provider staff same company) |
| PATCH | `/publish-destinations/{id}` | OWNER/ADMIN (+ staff) |
| POST | `/publish-destinations/{id}/disable` | OWNER/ADMIN (+ staff) |
| POST | `/publish-destinations/{id}/enable` | OWNER/ADMIN (+ staff) |
| POST | `/publish-destinations/{id}/validate` | OWNER/ADMIN (+ staff) |
| POST | `/publish-destinations/{id}/archive` | OWNER/ADMIN (+ staff) |

Optional nested list: `GET /publishing-connections/{connection_id}/destinations` (same RBAC; still tenant-scoped).

### Dry-run / execute endpoints

| Method | Path | RBAC | Side effects |
|---|---|---|---|
| POST | `/packs/{pack_id}/publish-dry-run` | OWNER/ADMIN (+ staff) | DB dry-run record only; **no** provider publish |
| POST | `/packs/{pack_id}/publish-execute` | OWNER/ADMIN (+ staff) | Intent + attempts; adapter call only when adapter registered (M8-E+) |
| GET | `/publish-intents/{id}` | MEMBER+ | |
| GET | `/publish-attempts/{id}` | MEMBER+ | |
| GET | `/packs/{pack_id}/publish-attempts` | MEMBER+ | |

### Schemas (response redaction)

- Destination responses: ids, type, external_id, display_name, statuses, connection_id, timestamps — **never** `secret_ref`, tokens, KEK.
- Dry-run / attempt responses: structured codes + sanitized errors only.
- Reuse connection pattern: admin deps analogous to `require_marketing_connection_admin`.

### RBAC matrix

| Role | Destination read | Destination mutate | Dry-run | Execute |
|---|---|---|---|---|
| MEMBER | ✅ | 403 | 403 | 403 |
| TENANT_ADMIN / OWNER | ✅ | ✅ | ✅ | ✅ |
| Provider staff (same company) | ✅ | ✅ | ✅ | ✅ |
| Other tenant / unauthenticated | 404/401 | 404/401 | 404/401 | 404/401 |
| Marketing module off | 403 | 403 | 403 | 403 |

---

## 4. Dry-run contract

### Guarantees

- **No** outbound publish / post / media upload to social providers.
- **No** token refresh that mutates provider session beyond read-only validate (default: **no provider calls** in D3).
- **No** historical success log (`action=historical_record`) and **no** live `succeeded` attempt.
- Deterministic result for same inputs + content fingerprint.

### Checks (ordered)

1. Pack exists in tenant; not `ARCHIVED`.
2. `approval_status=APPROVED` (or HQ-agreed equivalent).
3. M7 pack content preflight `PASSED` (default required; waive = separate policy).
4. Destination `enabled`, not archived; same tenant + connection.
5. Connection usable for dry-run: exists; `has_secret` (or explicit policy); status not `DISABLED`; **do not** set `token_status=VALID` from stub.
6. Channel text present / length limits for selected text channels.
7. Media: required resources resolvable via Mode A temporary handle policy or Mode B registered public URL; size/MIME vs storage profile; **no Mode C**.
8. Idempotency preview: if key already `succeeded`, report conflict code.
9. Emit structured issue codes (stable strings).

### Result object (conceptual)

| Field | Notes |
|---|---|
| `dry_run_id` | UUID |
| `ok` | bool |
| `content_fingerprint` | hash of pack texts/media refs/version |
| `issues[]` | `{code, severity, field?}` |
| `checked_at` | timestamptz |
| `expires_at` | fingerprint TTL (HQ open; propose 24h) |

---

## 5. Execute contract

### Rules

1. Separate endpoint from dry-run.
2. Body **requires** `idempotency_key` (client-supplied; unique per tenant).
3. Approval required (same as dry-run).
4. Successful dry-run fingerprint must match current content within TTL (unless HQ waives — default **required**).
5. Dry-run success **never** auto-executes.
6. `historical_record` path remains isolated; cannot call execute adapters.
7. Retries under the **same** idempotency key must not create a second successful external post:
   - if attempt `succeeded` with `external_post_id` → return prior result;
   - if `running`/`unknown` → safe recovery policy (§9).
8. Persist `external_post_id` **only after** provider success acknowledgment.

### Execute input (conceptual)

- `idempotency_key`, `connection_id`, `destination_id`
- optional `dry_run_id`
- channel/provider selection if multi

---

## 6. Publish attempt / log model

### Attempt state machine

```text
requested → running → succeeded
                   → failed
                   → unknown   # timeout / ambiguous provider result
unknown → (safe retry) → running → …
```

### Proposed table: `marketing_publish_attempts`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID NN | index |
| `pack_id` | UUID NN | |
| `connection_id` | UUID NN | |
| `destination_id` | UUID NN | |
| `intent_id` | UUID NN | |
| `idempotency_key` | VARCHAR(128) NN | |
| `attempt_number` | INT NN | ≥1 |
| `status` | VARCHAR(32) NN | requested/running/succeeded/failed/unknown |
| `provider` | VARCHAR(32) NN | |
| `destination_snapshot_json` | JSON NN | type, external_id, display_name at attempt time |
| `external_post_id` | VARCHAR(255) NULL | set only on success |
| `external_url` | VARCHAR(1024) NULL | |
| `sanitized_error_code` | VARCHAR(64) NULL | |
| `sanitized_error_message` | TEXT NULL | sanitizer only |
| `started_at` / `finished_at` | TIMESTAMPTZ | |
| `created_at` / `updated_at` | TIMESTAMPTZ NN | |
| UNIQUE | `(tenant_id, idempotency_key, attempt_number)` | |
| UNIQUE partial | optional: one `succeeded` per `(tenant_id, idempotency_key)` | |

### Intent table: `marketing_publish_intents`

| Column | Notes |
|---|---|
| `id`, `tenant_id`, `pack_id`, `connection_id`, `destination_id` | |
| `idempotency_key` | **UNIQUE (`tenant_id`, `idempotency_key`)** |
| `dry_run_id`, `content_fingerprint` | |
| `status` | accepted/in_progress/succeeded/failed/cancelled |
| timestamps / actor | |

### Log linkage

- Continue writing summary rows to `marketing_publish_logs` with `action=live_publish` (new) and `metadata_json.attempt_id` **or** treat attempt table as SoT and keep log for historical only — **HQ open**; recommendation: **attempt = SoT for live**, log remains historical + optional projection.

### Forbidden in attempt/log/audit

Plaintext tokens, `secret_ref` strings, raw provider bodies with credentials, KEK material.

---

## 7. Adapter boundary

```text
PublishExecuteService
  → resolve destination + connection (tenant checks)
  → SecretVaultPort.read_secret (in-process only)
  → PublishAdapterPort.publish(request) / .dry_validate(request)?
  → clear plaintext from memory
  → persist attempt outcome (sanitized)
```

### Port (conceptual)

```python
class PublishAdapterPort(Protocol):
    provider: str
    def publish(self, req: AdapterPublishRequest) -> AdapterPublishResult: ...
    # dry_run does not call this in D3; reserved for future read-only validate
```

| Provider | Gate |
|---|---|
| Telegram | **M8-E** only |
| Instagram / Threads / TikTok | M8-G (or later) |
| Margosya | Not an adapter SoT; may donate algorithms as fixtures |

---

## 8. Media / storage (M8-D constraints)

| Mode | M8-D |
|---|---|
| A Flexity-managed | **Default**; adapters receive short-lived signed/temp handles — never raw bucket creds |
| B public HTTPS URL | Supported if registered + validated |
| C client private bucket | **Out of scope** |

Dry-run/execute must enforce profile limits (size/MIME). Signed URL lifetime remains short-lived / tenant-scoped (existing C2a policy).

---

## 9. Failure / recovery

| Failure | Policy |
|---|---|
| Timeout / ambiguous provider response | Attempt → `unknown`; retry only with same idempotency key + explicit recovery rules; do not assume success |
| Safe retry | Allowed when no `external_post_id`; provider idempotency headers if available |
| Token invalid | Attempt `failed` + sanitized code; connection health may move to ERROR; require reconnect (M8-B) |
| Destination forbidden / not found | `failed`; may set destination `validation_status=INVALID` |
| Rate limit | `failed`/`unknown` + retry-after metadata (sanitized); capped retries |
| Partial multi-channel | Per-destination attempts; pack `publish_status=PARTIAL` rollup (reuse historical rollup idea) |

---

## 10. Proposed implementation slices (code — after separate approvals)

| Slice | Scope | Migration? | Adapter? |
|---|---|---|---|
| **D1** | Destination model + migration + ORM | **Yes** (destinations only) | No |
| **D2** | Destination HTTP API + RBAC + tests | No (unless tweak) | No |
| **D3** | Dry-run service + endpoint + fingerprint storage | Maybe dry-run table | No |
| **D4** | Execute foundation: intent + attempt + idempotency + log projection; adapter port stub (no Telegram) | Yes (intent/attempt) | Stub only |
| **M8-E** | Telegram `PublishAdapterPort` impl | No / minimal | **Yes** |

**Recommended first code slice after HQ approves this design:** **D1** (model/migration only).

---

## Exact proposed tables (D1 focus + D3/D4 foreshadow)

### `marketing_publish_destinations` (D1)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `tenant_id` | UUID | NN, index, FK tenants **ON DELETE RESTRICT** |
| `publishing_connection_id` | UUID | NN; composite FK `(tenant_id, publishing_connection_id)` → connections `(tenant_id, id)` **ON DELETE RESTRICT** |
| `provider` | VARCHAR(32) | NN, denormalized check vs connection |
| `destination_type` | VARCHAR(64) | NN |
| `external_id` | VARCHAR(255) | NN, non-secret |
| `display_name` | VARCHAR(255) | NN |
| `status` | VARCHAR(32) | NN: enabled/disabled/archived (DB Enum NAMES) |
| `validation_status` | VARCHAR(32) | NN: unchecked/valid/invalid/unavailable |
| `identity_locked_at` | TIMESTAMPTZ | NULL until first VALID (also reserved for future D4 live use) |
| `validated_at` | TIMESTAMPTZ | NULL |
| `validation_error_code` | VARCHAR(64) | NULL, sanitized |
| `metadata_json` | JSON | NN default `{}` — **no secrets**; forbidden keys rejected recursively |
| `created_at` / `updated_at` | TIMESTAMPTZ | NN |
| `created_by_user_id` / `updated_by_user_id` | UUID NULL | audit mixins as elsewhere |

**Indexes / uniqueness:**

- UNIQUE `(tenant_id, publishing_connection_id, destination_type, external_id)` WHERE status <> ARCHIVED
- INDEX `(tenant_id, publishing_connection_id)`
- INDEX `(tenant_id, status)`
- INDEX `publishing_connection_id` (single; no duplicate named connection-only index)

**CHECK:** status/validation enums; `external_id` / `display_name` trimmed non-empty; provider in known set.

### Later: `marketing_publish_dry_runs`, `marketing_publish_intents`, `marketing_publish_attempts` (D3–D4) — fields as §4–§6.

---

## State machines (summary)

**Destination:** enabled ⇄ disabled → archived

`identity_locked_at` set once on first `valid`; future D4 live publish may also set lock if still NULL. Reset/disable/archive never unlock.

**Dry-run record:** created as immutable snapshot (`ok` true/false); superseded by newer fingerprint

**Intent:** accepted → in_progress → succeeded | failed | cancelled

**Attempt:** requested → running → succeeded | failed | unknown

---

## Migration impact

| Slice | Impact |
|---|---|
| D1 | **One** Alembic revision adding `marketing_publish_destinations` (+ enums/checks). `revision=0026_mkt_publish_destinations` (≤32 chars; HQ long name shortened), `down_revision=0025_secret_envelope_versions`. |
| D3/D4 | Additional revision(s) for dry-run/intent/attempt — **not** in D1. |
| Forbidden now | Creating any migration in this documentation gate. |

---

## Exact proposed files / tests (future code; not created)

### D1

- `backend/app/modules/marketing/models.py` — destination model
- `backend/app/modules/marketing/enums.py` — destination status/type enums
- `backend/alembic/versions/<TBD>_mkt_publish_destinations.py`
- `backend/tests/test_marketing_publish_destinations_model.py` / migration test

### D2

- `schemas.py`, `routes.py`, `service/publish_destinations.py`, deps RBAC
- `tests/test_marketing_publish_destinations_api.py` (RBAC, cross-tenant, redaction)

### D3

- `service/publish_dry_run.py`, routes, schemas, optional model
- tests: deterministic issues; no provider mock calls; approval/grant failures

### D4

- `service/publish_execute.py`, `publish_attempts.py`, `adapters/port.py` stub
- tests: idempotency, no duplicate success, historical isolation, unknown recovery

### Always

- No Telegram module until M8-E.
- Extend sanitizer tests for live error paths.

---

## Threat model (stage)

| Threat | Mitigation |
|---|---|
| Cross-tenant destination use | tenant_id on all queries; 404 |
| Secret leakage via destination API | no secret columns; response schemas audited |
| Dry-run used as cover for publish | separate execute; adapters not wired in D3 |
| Double post | tenant idempotency unique + attempt success guard |
| Historical mistaken for live | distinct action; no adapter import in historical service |
| Fake stage KEK → prod publish | ops gates; fail-closed without real KEK/ceremony |
| Mode C / bucket creds | out of scope |
| Margosya YAML as SoT | forbidden by ADR |

---

## Stop conditions

Stop / do not start code when:

1. This design gate is not HQ-approved.
2. Request merges destination into connection.
3. Request starts Telegram adapter before D1–D4 foundations.
4. Request treats historical publish as execute.
5. Plaintext tokens / `secret_ref` in destination or API responses.
6. Mode C private buckets required for M8-D MVP.
7. Production publish demanded while stage uses fake secrets only.

---

## Unresolved questions (HQ)

~~1. Is destination `destination_external_id` immutable after first successful publish?~~
~~2. Dry-run fingerprint TTL (propose **24h**)?~~
~~3. Live SoT: new `marketing_publish_attempts` only vs dual-write to `marketing_publish_logs`?~~
~~4. TikTok: add `MarketingChannel.TIKTOK` vs provider-only media publish?~~
~~5. Destination `validate` in D2: structural only vs optional read-only provider call?~~
~~6. Insights channel: in or out of live publish core?~~
~~7. FK on `connection_id`: RESTRICT vs CASCADE on connection delete?~~

**All seven resolved — see «HQ locked decisions (2026-07-23)» above.** Remaining open items for later slices only (not blocking D1): exact D2 validate HTTP shape; Telegram adapter schedule (M8-E).

---

## HQ locked decisions (2026-07-23)

Encoded in D1 model/migration (and binding for later slices):

| # | Decision | D1 encoding / later slice |
|---|---|---|
| 1 | `external_id` mutable **only** while `validation_status=unchecked` **AND** `identity_locked_at IS NULL`. First transition to `valid` sets `identity_locked_at` once. Reset to unchecked / disable / archive do **not** unlock. Replacement = archive old + create new. Future D4 live use may also set lock. | Model `identity_locked_at` + `assert_external_id_mutable` |
| 2 | Dry-run fingerprint **TTL = 15 minutes** | Document only in this plan — **no dry-run code in D1** |
| 3 | Scheduled execute requires **fresh preflight** | Plan only — no execute code in D1 |
| 4 | `publish_attempts` = future live execution SoT; `publish_logs` = linked history | Plan only — no attempt/log live path in D1 |
| 5 | TikTok: enum/registry may include `tiktok_user`, but capability **disabled** — cannot activate, cannot structural-validate as available/VALID, **no adapter** | `destination_capability_enabled` → False; create defaults DISABLED; enable/VALID refused |
| 6 | Structural validate first; provider validate **unavailable without adapter** | `apply_structural_validation` only; no provider calls |
| 7 | Insights **out** of live destination types | Not in `MarketingPublishDestinationType` |
| 8 | FK to connection: composite `(tenant_id, publishing_connection_id)` **ON DELETE RESTRICT**; destination `tenant_id` FK **ON DELETE RESTRICT** (no CASCADE) | Migration + ORM |
| 9 | Lifecycle: `enabled` / `disabled` / `archived` — **no normal hard delete** | HQ status names; repository refuses hard delete |
| 10 | `validation_status`: `unchecked` / `valid` / `invalid` / `unavailable` | HQ wording on `.value`; DB stores Enum NAMES |

**Column naming (D1):** `publishing_connection_id`, `external_id` (not `destination_external_id`).

**Status:** D1 complete; **D2 HTTP slice authorized** on worktree `marketing-m8b-http-clean` — see D2 implementation report. D3/D4 still blocked.

---

## Recommended first implementation slice

**D1 — Destination model + migration + unit/migration tests only.**
No HTTP, no dry-run, no execute, no Telegram.

---

## Approval

**Status:** HQ locked decisions applied; D1 code slice authorized for worktree implementation (no commit/push; no HTTP/adapters).

**Verdict of this documentation step:** **DESIGN + D1 LOCKED FOR IMPLEMENTATION**.

---

## Confirmation

| | |
|---|---|
| Docs-only (original gate) | Superseded by D1 code slice |
| D1 code / migration in approved worktree | **Yes** |
| Commit / push | **No** |
| Server / tokens / publish | **No** |
| HTTP / dry-run / execute / adapters | **No** |
