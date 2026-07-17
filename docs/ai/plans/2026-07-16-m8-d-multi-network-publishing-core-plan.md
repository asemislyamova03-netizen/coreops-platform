# Implementation Plan: M8-D Multi-Network Publishing Core

**Date:** 2026-07-16
**Project:** Flexity / `coreops-platform`
**Category:** `universal_module` (Marketing Cabinet) — **plan only**
**Status:** **DRAFT — NOT APPROVED / NOT IMPLEMENTED**
**Parent ADR:** `docs/architecture/decisions/2026-07-15-m8-publish-bridge-client-owned-resources-adr.md`
**Parent M8 plan:** `docs/ai/plans/2026-07-15-m8-publish-bridge-client-owned-resources-plan.md`
**D0 research:** `docs/ai/research/2026-07-16-m8-d0-margosya-failure-reuse-audit.md`
**Foundations ready:** M8-B ✅ · M8-C1a ✅ · M8-C2a ✅ (`874cf0e`)
**Margosya role (D0):** R3+R4 reference/adapter donor/fixtures — **not** SoT, **not** current fallback

---

## Goal

One tenant-safe Marketing publishing core that supports **Telegram, Instagram, Threads, TikTok** with:

- monthly content plan / pack scheduling
- dry-run + preflight
- destination grants (connection ≠ publish permission)
- idempotency, controlled retries
- immutable publish logs + audit
- hooks for analytics / lead attribution
- future Flexity Today AI employee (Gate D7)

**Do not** rebuild four separate publishing systems.
**Do not** restore Margosya as production publisher.

---

## Classification

| Field | Value |
|-------|-------|
| Architecture layer | `universal_module` |
| Risk | high |
| Code approval | **not granted** |
| Production migration / deploy | **forbidden until later gates** |

---

## Shared M8-D publishing core contract

All providers share one domain model (names illustrative; exact schema in D1 design):

| Field | Purpose |
|-------|---------|
| `tenant_id` | Isolation |
| `connection_id` | `MarketingPublishingConnection` identity |
| `destination_grant_id` | Explicit allow-list target (chat/page/account) |
| `pack_id` / `content_item_id` / `content_version` | What is published |
| `media_resource_ids[]` | From C2a `MediaResource` / Mode A|B |
| `scheduled_at` + `timezone` | Schedule |
| `preflight_result` | Structured pass/fail codes |
| `dry_run_result` | No provider side-effect proof |
| `idempotency_key` | Tenant-scoped unique publish intent |
| `publish_attempt_id` | Each try |
| `provider_publication_id` | External ID |
| `retry_state` | Visible, bounded |
| `final_status` | pending / dry_run_ok / publishing / published / failed / cancelled |
| `sanitized_error` | Sanitizer only |
| `audit_event_ids` | Audit recorder |
| `analytics_hook` / `attribution_hook` | Outbound events — no PII secrets |

### Non-negotiable rules (from ADR)

1. Connection bind / `token_status` ≠ publish authorization.
2. Vault plaintext only inside adapter execution boundary.
3. No YAML/Git mutation on DB-backed packs.
4. No live publish without: approval + preflight + grant + dry-run + idempotency + audit.
5. Adapters receive `MediaResource` / temporary handles — never raw object keys or bucket credentials.
6. Margosya filesystem packs are fixtures only.

---

## Margosya reuse mapping (summary)

| Donor | Into Flexity | Class |
|-------|--------------|-------|
| `publish_telegram.py` sendMessage + eligibility | Telegram adapter | B |
| `publish_instagram_live.py` container flow + URL media rules | Instagram adapter | B |
| `publish_threads_live.py` chunking + publish | Threads adapter | B |
| `publish_tiktok_live.py` init skeleton | TikTok adapter | B |
| Error `access_token=` redaction | Align with core sanitizer | B |
| ContentOps UX / YAML SoT / GHA secrets / git sync | — | C/D — do not copy as production |

Full matrix: D0 research §5–§6.

---

## Acceptance gates (mandatory order)

### Gate D0 — Margosya read-only audit *(this stream)*

- Failure diagnosis + reuse inventory accepted
- Margosya role fixed as R3+R4
- **No code**

### Gate D1 — Shared publish contract + destination grants + dry-run

**Design appendix (draft):** `docs/ai/plans/2026-07-16-m8-d1-shared-publish-contract-design.md`

**Deliverables (after approval):**

- Destination / publish-grant model (per tenant, connection, channel target)
- Dry-run API/service: validates pack, texts, media, connection health stub rules, grants, limits — **zero provider writes**
- Explicit publish intent command with `idempotency_key`
- Mapping from Cabinet pack → publish payload (no filesystem required)
- Resolve TikTok channel-enum gap vs `MarketingPublishingProvider.TIKTOK`

**First code slice after approval:** **D1a** grants only (see design appendix §7).

**Exit criteria:** unit tests + contract docs; no live network publish.

### Gate D2 — Scheduler, idempotency, retries, publish-log core

- Scheduler/worker boundary (choice of in-process vs queue tech = separate infra decision; **no Celery assumption until approved**)
- Attempt table / log write path → `MarketingPublishLog`
- Retry policy: visible, capped, no silent bulk replay
- Timezone rules for `scheduled_at`

**Exit criteria:** SQLite/PG tests for idempotency uniqueness and retry caps; disposable PG smoke when schema lands.

### Gate D3 — Margosya parity fixtures extracted and sanitized

- Sanitize historical pack fixtures (no tokens)
- Golden dry-run cases per channel from legacy eligibility rules
- Document differences vs live provider policy

### Gate D4 — Telegram + Instagram adapters

**Parallelizable after D1+D2 contracts freeze.**

| Adapter | Donor | Notes |
|---------|-------|-------|
| Telegram | `publish_telegram.py` | Pilot-first historically (parent plan M8-E); keep as first live candidate |
| Instagram | `publish_instagram_live.py` | Requires media URL strategy (C2a Mode A temp URL or Mode B public URL); Graph version verification |

**Exit criteria:** adapter unit tests with fake HTTP; staging dry-run; **no prod publish**.

### Gate D5 — Threads + TikTok adapters

| Adapter | Donor | Notes |
|---------|-------|-------|
| Threads | `publish_threads_live.py` | Text chunking; reply-chain behavior explicit in UX |
| TikTok | `publish_tiktok_live.py` | Expect larger gap vs init-only script — video upload may need expansion |

**Exit criteria:** same as D4 for these providers.

### Gate D6 — Staging provider verification (all four)

- Verify current official API versions, scopes, token lifetimes against provider docs
- Controlled staging accounts only
- Health checks that cannot publish/refresh unless separately approved
- Record evidence pack for HQ

### Gate D7 — Flexity Today / UI / monthly plan / analytics

- Operator UI for schedule + grants
- Monthly content plan surfaces
- Analytics + lead attribution hooks
- Flexity Today AI employee consumes the **same** publish contract (no parallel publish path)

---

## Parallelism after shared contract

```text
D0 ──► D1 ──► D2 ──►┬── D3 (fixtures)
                    ├── D4 Telegram ‖ Instagram
                    └── D5 Threads ‖ TikTok
                           └──► D6 staging all-four
                                  └──► D7 UI / Today / analytics
```

D4 and D5 may proceed **in parallel** once D1/D2 contracts and MediaResource delivery are stable.
D3 can run parallel with early D4.

---

## Scheduler / queue requirements

- Tenant-scoped jobs only
- Idempotency key unique per `(tenant_id, intent)`
- No automatic publish of “all due packs” without grant + dry-run snapshot
- Crash safety: attempt row before provider call; compensation policy documented
- Orphan media cleanup remains C2a follow-up (not silently expanded here)

---

## Analytics and lead attribution boundary

- Publish success emits **hook/event** with tenant, channel, external id, pack id, timestamps
- Must not include tokens, raw provider payloads, or PII beyond existing Cabinet rules
- Detailed attribution pipelines are **consumers** of hooks (Gate D7 / separate CRM work) — not blockers for D1–D5

---

## Migration and rollback

| Phase | Action |
|-------|--------|
| During D1–D5 | Margosya frozen as reference; optional emergency one-shot posts stay **manual outside Flexity** |
| D6 | Staging only |
| Post-D6 | Cutover per channel with feature flag per tenant |
| Rollback | Disable adapter flag; no YAML fallback; no automatic Margosya re-enable |

**Production Alembic / deploy:** separate HQ approvals; not part of D0–D1 docs gates.

---

## Tests (per gate)

| Gate | Tests |
|------|-------|
| D1 | Grant enforcement; dry-run no HTTP side effects; idempotency reject duplicates |
| D2 | Retry caps; attempt/log integrity; timezone schedule |
| D3 | Fixture loaders; golden eligibility |
| D4/D5 | Adapter fakes; sanitizer; MediaResource-only inputs |
| D6 | Manual staging checklist (not CI live secrets) |
| Regression | Existing Marketing + M8-B/C suites stay green |

---

## Provider verification checklist (before coding assumes legacy still works)

| Provider | Must verify against official docs |
|----------|-----------------------------------|
| Telegram | Bot API sendMessage limits; media methods if expanded |
| Instagram | Current Graph version; content publishing scopes; container rules; token types |
| Threads | graph.threads.net version; reply chain; media types |
| TikTok | oauth scopes; video upload vs init; audit statuses |

Legacy endpoints in Flexity scripts are **evidence of past design**, not proof of current policy.

---

## Explicit non-goals (this plan)

- Implementing adapters in this D0 task
- Repairing Margosya bot/systemd/tokens
- Choosing production vault/S3 vendors (already separate deployment gates)
- Client onboarding UI (D7)
- Push/PR/merge/deploy

---

## Approval

**Status: waiting for HQ acceptance of Gate D0, then separate approval to start Gate D1 design/code.**

Do not mark M8-D implemented.
