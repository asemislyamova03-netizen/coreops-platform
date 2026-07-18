# Research Brief: M8-D0 Margosya failure diagnosis, reuse inventory and target role

**Date:** 2026-07-16
**Project:** Flexity (`coreops-platform`) + Margosya legacy (`margosya-os`)
**Category:** `research_only` / architecture diagnostics
**HQ gate:** Gate D0 — awaiting acceptance
**Risk:** high (credentials, external publishing, legacy side effects)
**Related ADR:** `docs/architecture/decisions/2026-07-15-m8-publish-bridge-client-owned-resources-adr.md`
**Prior audits:** `docs/ai/research/2026-07-09-margosya-to-cabinet-audit.md`, `docs/ai/research/2026-07-15-margosya-publish-bridge-assessment.md`

---

## Task Classification

| Field | Value |
|-------|-------|
| **Project** | Flexity + Margosya legacy |
| **Category** | `research_only` |
| **Risk** | high |
| **Intended scope** | this research + M8-D multi-network plan (docs only) |
| **Forbidden** | code, migrations, deploy, publish, token refresh, OAuth, webhook mutation, service restart, stage/commit/push |

---

## 1. Safety preflight (executed)

| Repo / worktree | Branch | HEAD | staged |
|-----------------|--------|------|--------|
| Flexity | `feature/marketing-m8-publish-bridge` | `874cf0e` (C2a commit; ahead 1 of origin) | **0** |
| flexity_admin | `main` | `cd10a79` | **0** |
| Trailers | `crm-roles-production-logistics` | `c1c3f51` | **0** |
| margosya-os | `master` | `7476842` | **0** |
| margosya-repo-candidate | *(not a git root)* | n/a | n/a |
| margosya-repo-candidate-server/margosya | `master` | `da72a53` | **0** |

**Dirty trees:** Flexity remains dirty with unrelated work (Branch, Booking/CRM, `.gitignore` `_c2b_tmp`, etc.). **Not modified, not staged, not cleaned.**

**SSH / live host:** `~/.ssh/config` has host `flexity`; **no** `margosya` Host entry. Prior assessment already noted hostname `margosya` does not resolve here. **No SSH, no systemctl, no journalctl, no provider API calls performed.**

**Secrets:** values never printed. Presence reported in §4 only.

---

## 2. Context

Margosya historically orchestrated Telegram / Instagram / Threads / TikTok publishing for Asem dogfood content. Flexity M8 foundations now exist:

- M8-B Connected Accounts — accepted
- M8-C1a Secret Vault boundary — accepted
- M8-C2a Storage profiles — **FINAL ACCEPTED / GREEN** (`874cf0e`)
- M8-D — **not started**

Owner reports Margosya currently **cannot publish anything**. ADR already states Margosya is **not** production SoT. This D0 answers: why it fails, what to reuse, formal role, and the shortest path to four networks **inside Flexity**.

---

## 3. As-is publish path (legacy)

```text
Telegram UX (margosya-bot)
  → content_ops_publish.preflight / approve / publish_*
  → Flexity filesystem landing/content/content-packs/<pack>/
  → either:
       A) GitHub Actions workflow_dispatch (Telegram + Instagram)
          → scripts/content/publish_telegram.py | publish_instagram_live.py
          → provider API
          → YAML publish_log.yml + git commit/push
       B) direct subprocess on Margosya host (Threads / TikTok)
          → scripts/content/publish_threads_live.py | publish_tiktok_live.py
          → .env.threads / .env.tiktok
          → provider API
          → YAML mutation
```

**Critical property:** Margosya is an **orchestrator + Telegram thin client**, not the owner of pack state. De facto SoT for legacy publish remains **Flexity git/filesystem packs + Actions secrets**, while Marketing Cabinet SoT is **PostgreSQL**. These two representations are **not interchangeable**.

---

## 4. Failure diagnosis (layer by layer)

### 4.1 Summary verdict

**Primary failure class (high confidence):** architectural / data SoT mismatch — Cabinet DB packs cannot feed the legacy filesystem/GitHub publish pipeline. Margosya therefore cannot publish current Flexity Cabinet content even if the bot process were healthy.

**Contributing operational factors (medium confidence):** stale/absent local evidence of a live bot loop; documented Instagram token expiry window; Threads/TikTok secret files absent on the inspected workstation copy; dependency on `GITHUB_TOKEN` + Actions for TG/IG.

**Not proven without mutating/live checks:** “all tokens expired”, “Meta API version changed”, “systemd unit is down on production host”. Those remain **blockers for exact live diagnosis**, not assumed facts.

### 4.2 Layer table

| Layer | Component / path | Expected | Observed evidence | Failure class | Confidence |
|-------|------------------|----------|-------------------|---------------|------------|
| Content input | Bot commands + step intake (`telegram_inbox_bot.py`, `content_pack_*`) | Build/update filesystem pack | Code present; Cabinet packs live in DB without matching pack dirs (prior D0-adjacent assessment 2026-07-15) | **data / architecture** | **high** |
| Validation | `preflight_content_pack` | Files + assets + eligibility | Historical `asset_generate_failed` (PIL) report; fail-closed eligibility when ≠1 eligible pack | code/config/data | medium (historical) |
| Media prep | `generate_social_assets.py`, public URL under landing assets | PNG + public HTTPS URL for IG | Relies on local FS + landing deploy path; Cabinet Mode A/B not wired | architecture | high |
| Scheduler/queue | No real multi-tenant queue; eligibility via `publish_at` + Actions schedule | Due packs publish | Manual `/publish_*` + GHA; no Flexity scheduler | design gap | high |
| Provider adapter | Flexity `scripts/content/publish_*.py` | Channel-specific API calls | Scripts exist and encode reusable algorithms | — (code exists) | high |
| Credentials | Bot `.env`, GHA secrets, `.env.threads` / `.env.tiktok` | Present + valid | Workstation: TG+GH `.env` **PRESENT**; `.env.threads` / `.env.tiktok` / root `.env.instagram` **ABSENT**. Docs cite IG long-lived token expiry ~**2026-07-02T14:00 UTC**. Live validity **not re-probed** | credential / unknown-live | medium–high (docs); low (current live) |
| Provider request | Telegram Bot API; Graph IG `v21.0`; Threads `graph.threads.net/v1.0`; TikTok `open.tiktokapis.com/v2` | Success IDs | Not executed in this task | unknown without safe health probe | — |
| Response/error | Script redaction of `access_token=` | Sanitized errors | Pattern reusable (B) | — | high |
| Publish result/log | `publish_log.yml` + git | Immutable channel IDs | Git mutation forbidden by M8 ADR for new path | architecture / security | high |
| Runtime/service | `margosya-bot.service` on `/opt/margosya-os` | Polling bot | Local `telegram_events.jsonl` last mtime **2026-07-01**; 3× `poll_error` classified as **timeout**; no SSH to verify server unit | infrastructure / unknown | medium |

### 4.3 Sanitized local log evidence

- `logs/telegram_events.jsonl` last activity **2026-07-01**.
- Error events in file: **3× `poll_error`**, error_class **timeout** (no token material inspected).
- No local evidence of recent successful `/publish_approved` / Threads / TikTok commands in that log file.
- Code files under margosya-os continued to receive edits through **2026-07-15/16**, so “repo inactive” is false; “local runtime loop inactive” is the accurate claim.

### 4.4 Credential presence matrix (names only)

| Source category | Keys / files | Presence on inspected copy |
|-----------------|--------------|----------------------------|
| Telegram bot transport | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS` in `integrations/telegram/.env` | **PRESENT** (values not read) |
| GitHub orchestration | `integrations/github/.env` (+ runtime `GITHUB_TOKEN` for dispatch/sync) | **PRESENT** |
| Threads channel | `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN` via `.env.threads` | **ABSENT** locally |
| TikTok channel | `TIKTOK_ACCESS_TOKEN` via `.env.tiktok` | **ABSENT** locally |
| Instagram (Actions) | `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN` as GitHub secrets | Not inspectable here; docs warn expiry ~2026-07-02 |
| Telegram publish (Actions) | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Not inspectable here |

### 4.5 What would be required for a sharper live diagnosis (not done)

Controlled, separately approved, **non-mutating** probes only:

1. Read-only `systemctl is-active margosya-bot` / recent journal **without** restart.
2. Presence checks for `/opt/margosya-os/.env.threads` / `.env.tiktok` (names/mtime only).
3. Existing IG token-health workflow **read-only** if it cannot refresh/publish (confirm before run).
4. Confirm whether current Cabinet packs have filesystem mirrors (they should not be required for Flexity M8-D).

Any probe that refreshes tokens, dispatches workflows, or posts content is **out of scope**.

---

## 5. Provider inventory and reuse classification

Classification legend: **A** nearly unchanged · **B** reuse algorithm/contract, adapt · **C** reference/fixture · **D** replace for security/tenancy/obsolete · **E** unknown — needs official API verification.

### 5.1 Telegram

| Item | Detail |
|------|--------|
| Adapter paths | Margosya: `content_ops_publish.publish_approved` → GHA `telegram-publish.yml` → Flexity `scripts/content/publish_telegram.py` |
| API | `https://api.telegram.org/bot{token}/sendMessage` |
| Auth | Bot token + chat id |
| Formats | Text ≤4096; no native media in this script path |
| Scheduling | Pack `publish_at` + Actions/manual dispatch |
| Idempotency | Soft via `published_at` in YAML — **not** tenant idempotency key |
| Result ID | Telegram message id → YAML `external_id` |
| Operational status | Pipeline **code present**; **ops status unverified**; cannot publish Cabinet-only packs |
| Reuse | **B** sendMessage + eligibility rules; **D** GHA secrets as tenant vault, YAML/Git writeback, bulk scanner; **C** packs as fixtures |

### 5.2 Instagram

| Item | Detail |
|------|--------|
| Adapter paths | GHA `instagram-publish.yml` → `publish_instagram_live.py` (+ dry schema `publish_instagram.py`) |
| API | Graph `v21.0` `/{user_id}/media` + `/media_publish` |
| Auth | `INSTAGRAM_USER_ID` + `INSTAGRAM_ACCESS_TOKEN` |
| Formats | Feed image / carousel via public HTTPS URLs; caption from md/yml |
| Upload | Create container → publish container |
| Operational status | Documented **token expiry blocker** (~2026-07-02); current validity **E** |
| Reuse | **B** container workflow + media URL validation + error redaction; **D** Actions secret store, YAML mutation, global single account; **E** current Graph version/scopes |

### 5.3 Threads

| Item | Detail |
|------|--------|
| Adapter paths | `publish_threads_approved` → `publish_threads_live.py` with Margosya `.env.threads` |
| API | `https://graph.threads.net/v1.0` create + publish; text chunk ≤500 |
| Auth | `THREADS_USER_ID` + `THREADS_ACCESS_TOKEN` |
| Operational status | Local secret file **absent**; server presence unknown; `--live` required |
| Reuse | **B** chunking + container publish; **D** host-local env files, YAML write; **E** current Threads API policy |

### 5.4 TikTok

| Item | Detail |
|------|--------|
| Adapter paths | `publish_tiktok_approved` → `publish_tiktok_live.py` |
| API | `https://open.tiktokapis.com/v2/post/publish/video/init/` |
| Auth | `TIKTOK_ACCESS_TOKEN` |
| Formats | Video init workflow (narrow script) |
| Operational status | Local `.env.tiktok` **absent**; live capability **E** |
| Reuse | **B** init/publish sequence skeleton; **D** single global token file; **E** full upload/scopes/video constraints |

### 5.5 Cross-cutting Margosya components

| Component | Class | Notes |
|-----------|-------|-------|
| Telegram ContentOps UX / step intake | **C** (product UX reference) | Do not copy as SoT; Flexity UI later (Gate D7) |
| `content_ops_publish` orchestration | **C/B** | Preflight checklist ideas reusable; Git sync/dispatch **D** |
| GitHub Actions publishers | **D** as production path | Useful CI history **C** |
| YAML pack schema | **C** fixtures | Not Flexity SoT |
| Universal dispatcher / executor_queue | **D/C** | Not Marketing publish core |
| Error sanitizer regex in scripts | **B** | Align with Flexity `provider_error_sanitizer` |

---

## 6. Flexity parity mapping

| Margosya / legacy piece | Responsibility today | Flexity destination | Class | Required changes | Security | Tenant | Provider verify | Slice |
|-------------------------|----------------------|---------------------|-------|------------------|----------|--------|-----------------|-------|
| Bot publish commands | Operator trigger | Marketing API dry-run + explicit publish intent | D/C | No bot as SoT | — | multi-tenant API | — | D1 |
| Filesystem pack.yml | Pack state | `MarketingPublicationPack` + texts/media | D | Stop YAML mutation | no secrets in YAML | `tenant_id` | — | D1 |
| GHA TG/IG secrets | Credential store | `SecretVaultPort` + `MarketingPublishingConnection.secret_ref` | D | Vault only | critical | per connection | health stub ≠ valid | D1/D4 |
| `.env.threads` / `.env.tiktok` | Host secrets | same vault boundary | D | — | critical | per connection | E | D5 |
| `publish_telegram.py` | Adapter | Telegram adapter service | B | MediaResource, idempotency, audit, no git | redact | tenant | Bot API stable-ish | D4 |
| `publish_instagram_live.py` | Adapter | Instagram adapter | B | Mode B URL or Mode A temp URL; Graph version check | redact | tenant | Graph v + scopes | D4 |
| `publish_threads_live.py` | Adapter | Threads adapter | B | chunking; destination grant | redact | tenant | Threads API | D5 |
| `publish_tiktok_live.py` | Adapter | TikTok adapter | B | full video upload path likely | redact | tenant | TikTok API | D5 |
| `publish_log.yml` | Result log | `MarketingPublishLog` + audit | D | immutable DB | no raw provider bodies | tenant | — | D2 |
| Eligibility / publish_at | Schedule gate | scheduler + grants + preflight | B | TZ, idempotency | — | tenant | — | D2 |
| Public asset URL | IG media delivery | `MediaResource` / storage profile | B | C2a already | no keys | tenant | — | D1/D4 |
| Connection = publish right | Implicit | destination/publish grants | D | allow-list required by ADR | critical | tenant | — | D1 |

### Must NOT copy into Flexity

- Tokens in DB/files/YAML/GHA-as-tenant-model
- Logging of token or full provider payloads
- Single global Asem account assumptions
- Cross-tenant credential reuse
- Git/YAML as runtime publish state
- Absolute local media paths as adapter contract
- Bulk “scan all packs and publish” without idempotency keys
- Treating `status=active` / vault bind as publish authorization
- Workflow dispatch that commits publish results into git

---

## 7. Formal role for Margosya

| Candidate | Verdict |
|-----------|---------|
| R1 Production publisher | **Rejected** — ADR + SoT mismatch + current non-operational claim |
| R2 Temporary fallback | **Rejected for now** — broken / unproven; cannot publish Cabinet packs |
| R3 Legacy reference + adapter donor | **Accepted (primary)** |
| R4 Read-only regression oracle / fixtures | **Accepted (secondary)** |
| R5 Archive after verified Flexity parity | **Accepted (end state)** |
| R6 Separately repaired standalone tool | **Optional only** — see §8 |

**Recommended formal role during migration:**
**R3 + R4** — reference implementation and sanitized fixture/donor for adapter algorithms.
**After Gate D6 parity:** **R5** archive / read-only.

---

## 8. Repair vs port

| Option | Effort (order-of-magnitude) | Benefit | Risk | Recommendation |
|--------|-----------------------------|---------|------|----------------|
| Full Margosya repair to restore Asem filesystem publish | days–weeks (service, tokens, pack sync, PIL, IG refresh, Threads/TikTok env) | Temporary Asem convenience | Delays Flexity; keeps unsafe SoT; still no multi-tenant | **Do not** |
| Narrow blocker only (e.g. restart bot + one token) | hours–1 day | May restore TG bot UX | Does not fix Cabinet→publish; token refresh is mutating | **Only if HQ needs emergency Asem post outside Flexity**, with explicit one-shot approval |
| No repair — port algorithms into Flexity M8-D | planned D1–D6 | Durable tenant-safe four-network path | Needs provider verification | **Default / preferred** |

**Recommendation:** **Do not repair Margosya as a product path.** Port Flexity script algorithms (class B) onto M8-B/C foundations. Keep Margosya frozen as reference/fixtures unless a separate emergency hotfix is explicitly approved.

---

## 9. Security findings

1. Legacy production path stores/uses secrets in **GitHub Actions** and **host env files** — incompatible with M8 vault ADR for multi-tenant SaaS.
2. Publish success writes **git-tracked YAML** — forbidden for DB-backed packs.
3. `content_ops_publish` embeds GitHub HTTPS remote with token for sync (`x-access-token:…`) — high-risk pattern; must not migrate.
4. Scripts already redact `access_token=` in errors — good pattern to keep under Flexity sanitizer.
5. No secrets were printed in this audit.

---

## 10. Unknowns / blockers

1. Live `margosya-bot.service` state on server (no authorized non-mutating access used).
2. Current validity of IG/TG Actions secrets and Threads/TikTok server env.
3. Whether Meta/TikTok API versions/scopes changed since last successful publish (needs official docs Gate D6).
4. Exact owner-facing failure symptom (bot silent vs preflight fail vs Actions fail) — local logs only show stale timeouts.
5. Whether any Cabinet pack was ever successfully bridged via Margosya (prior assessment concluded **not safe / not done**).

---

## 11. Do not touch

- Margosya services, `.env*`, Actions, tokens
- Flexity production DB / migrations / deploy
- Live publish / refresh / OAuth / webhooks
- Unrelated dirty Flexity worktree files
- M8-D implementation code (this gate is docs only)

---

## 12. Next safe step

1. HQ accept **Gate D0** (this document).
2. Review **D1 design appendix:** `docs/ai/plans/2026-07-16-m8-d1-shared-publish-contract-design.md`.
3. After D0: approve **Gate D1**, starting with **D1a destination grants** (no adapters).
4. Do **not** start adapter coding until D1 (+ ideally D2 skeleton) is approved.
5. Optional separate approval: read-only server health snapshot — only if needed to close operational unknowns; still no Margosya repair by default.

## 13. Continuation note (2026-07-16)

Follow-up research (still docs-only) added:

- D1 design appendix mapping existing Marketing preflight / publish_log / connections onto the shared contract.
- Confirmed gap: `MarketingChannel` lacks TikTok while `MarketingPublishingProvider` includes it.
- Legacy algorithm contracts frozen as B-class evidence for D4/D5 (Graph v21.0 / Threads v1.0 / TikTok v2 init — pending official verification at D6).
- Fixture inventory: 16 filesystem `pack.yml` under `landing/content/content-packs/` for future Gate D3 sanitization.

No code, publish, SSH, or commit in that continuation.

## Final checks

- No production code changes (docs only).
- No migrations / deploy / publish / provider mutation.
- No secret values exposed.
- staged remains 0 (verify in final report).
