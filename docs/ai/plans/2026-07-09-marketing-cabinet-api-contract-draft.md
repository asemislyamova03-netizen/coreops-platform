# M4 — Marketing Cabinet API Contract Draft

**Дата:** 2026-07-09  
**Проект:** Flexity / `coreops-platform`  
**Фаза:** M4 — API contract draft  
**Категория:** `documentation_only`  
**Статус:** contract draft — **код не менялся, migrations не создавались**

**Родительские документы:**
- [2026-07-03-marketing-content-cabinet-product-tz.md](./2026-07-03-marketing-content-cabinet-product-tz.md) (M0)
- [2026-07-09-margosya-to-cabinet-audit.md](../research/2026-07-09-margosya-to-cabinet-audit.md) (M1)
- [2026-07-09-marketing-cabinet-data-model-draft.md](./2026-07-09-marketing-cabinet-data-model-draft.md) (M2)
- [2026-07-09-marketing-cabinet-ui-wireframe-plan.md](./2026-07-09-marketing-cabinet-ui-wireframe-plan.md) (M3)

**HQ approval:** documentation-only.

---

## Task Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `documentation_only` |
| **Risk level** | low |
| **Intended scope** | `docs/ai/plans/2026-07-09-marketing-cabinet-api-contract-draft.md` |
| **Forbidden scope** | код, migrations, production, deploy, Margosya bot, Core public inbound, Booking / Clinic / Trailers |

---

## 1. Goal

### 1.1 Зачем нужен API contract

Дать **единый контракт** между:

| Consumer | Role |
|----------|------|
| **platform-console** Marketing UI | Primary client (P0) |
| **Marketing backend module** | Source of truth implementation |
| **Margosya bot** | Thin Telegram client (later) |
| **Core services** | Party / WorkItem for leads |
| **Git export bridge** | Transition publish pipeline |

### 1.2 Что контракт фиксирует

- REST endpoints и HTTP methods
- Request/response JSON schemas (draft)
- Status transitions и fail-closed gates
- Tenant isolation rules
- Error codes
- MVP vs deferred scope
- Margosya ↔ Cabinet ↔ Core boundaries

### 1.3 Что контракт **не** фиксирует

- Alembic migrations (M5+)
- OpenAPI YAML file in repo (может быть generated later)
- Channel token storage implementation
- Native Meta/WhatsApp API payloads

---

## 2. API namespace

### 2.1 Current Flexity convention (as-is)

Из существующего Core API:

| Pattern | Example |
|---------|---------|
| Base prefix | `/api/v1` (`settings.api_v1_prefix`) |
| Module routes | flat prefix, **без** `tenant_id` в path |
| Tenant scope | header `X-Tenant-ID: <uuid>` |
| Auth | Bearer JWT + `get_current_user` |
| Module guard | `Depends(require_module("crm"))` |
| IDs in path | UUID (`{pack_id}`, `{topic_id}`) |

Примеры сегодня:

```http
GET  /api/v1/work-items
POST /api/v1/parties
GET  /api/v1/documents
```

Header (workspace client):

```http
Authorization: Bearer <token>
X-Tenant-ID: <tenant-uuid>
```

### 2.2 Recommended Marketing namespace

**Рекомендация:** следовать существующему стилю Core — **flat module prefix + `X-Tenant-ID`**.

```text
/api/v1/marketing/*
```

**Не рекомендуется для MVP:**

```text
/api/v1/tenants/{tenant_id}/marketing/*
```

Причины:
- все модули Core уже используют header tenancy;
- `platform-console` уже шлёт `X-Tenant-ID` из workspace context;
- меньше дублирования tenant в path и header.

### 2.3 Router registration (future implementation hint)

```python
# backend/app/modules/marketing/routes.py
marketing_router = APIRouter(prefix="/marketing", tags=["marketing"])

# backend/app/api/v1/router.py
api_router.include_router(marketing_router)
```

### 2.4 Module code

| Field | Value |
|-------|-------|
| `module_registry` code | `marketing` (new) |
| MVP tenant | `flexity-sales` |
| `require_module` | `Depends(require_module("marketing"))` |
| Dependencies | `parties`, `crm` (for lead link/create) |

### 2.5 Content-Type

| Request | `application/json` |
| Upload | `multipart/form-data` for media |
| Response | `application/json` |

### 2.6 Pagination convention (align with Core)

Query params on list endpoints:

| Param | Default | Max |
|-------|---------|-----|
| `skip` | 0 | — |
| `limit` | 50 | 200 |

Response wrapper (optional, align with existing list endpoints — flat array OK for MVP):

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 50
}
```

**MVP:** flat `[]` array acceptable (как `work-items`, `parties` сегодня).

---

## 3. Auth and tenant rules

### 3.1 User auth (Console UI)

| Rule | Detail |
|------|--------|
| All marketing endpoints | require authenticated user |
| Tenant context | `X-Tenant-ID` header **required** |
| Access check | user membership OR provider staff on tenant |
| Cross-tenant | **denied** — `PermissionDeniedError` |
| Module enabled | `marketing` module active for tenant |

Implementation reference: `get_tenant_context()` in `app/core/tenancy.py`.

### 3.2 Margosya bot auth (later)

| Rule | Detail |
|------|--------|
| Mechanism | separate **service principal** or scoped API key |
| Header | `Authorization: Bearer <bot-service-token>` |
| Tenant | fixed `X-Tenant-ID` for `flexity-sales` |
| Scopes | marketing:read, marketing:write, marketing:publish |
| No user JWT | bot does not impersonate Asem without explicit delegation |

**MVP:** Margosya may continue filesystem; API auth slice in M6+.

### 3.3 Audit

| Action | Audit event |
|--------|-------------|
| `POST .../approve` | `marketing.pack.approved` |
| `POST .../reject` | `marketing.pack.rejected` |
| `POST .../publish` | `marketing.pack.publish_requested` |
| Publish success/fail | `marketing.pack.published` / `marketing.pack.publish_failed` |
| `POST .../lead-attribution` | `marketing.attribution.created` |
| `POST .../topics` import | `marketing.topics.imported` |

Use existing `AuditRecorder` pattern from parties module.

### 3.4 Idempotency (later)

Publish endpoints may accept `Idempotency-Key` header — **deferred MVP**.

---

## 4. P0 Dashboard API

### 4.1 Endpoint

```http
GET /api/v1/marketing/dashboard
```

**Query (optional):**

| Param | Type | Default |
|-------|------|---------|
| `date` | `YYYY-MM-DD` | today (tenant TZ) |

### 4.2 Response `MarketingDashboardResponse`

```json
{
  "date": "2026-07-09",
  "today_content": {
    "pack_id": "uuid-or-null",
    "title": "string-or-null",
    "slug": "string-or-null",
    "status": "draft|approved|published|...",
    "planned_date": "2026-07-09"
  },
  "pending_approval_count": 2,
  "failed_publish_count": 1,
  "draft_packs_count": 3,
  "latest_publications": [
    {
      "pack_id": "uuid",
      "title": "string",
      "slug": "string",
      "channel": "telegram",
      "published_at": "2026-07-08T13:25:50Z",
      "external_url": "https://..."
    }
  ],
  "new_leads_from_content_count": 1,
  "active_demo_count": null,
  "reminders": []
}
```

### 4.3 Field MVP matrix

| Field | MVP | Notes |
|-------|-----|-------|
| `today_content` | ✅ | pack for `date` or null |
| `pending_approval_count` | ✅ | |
| `failed_publish_count` | ✅ | |
| `draft_packs_count` | ✅ | |
| `latest_publications` | ✅ | last 5 |
| `new_leads_from_content_count` | ✅ | last 7 days |
| `active_demo_count` | ⚠️ optional | null if no demo table |
| `reminders` | ❌ later | empty array MVP |

---

## 5. Topics API

### 5.1 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/marketing/topics` | List topics |
| `POST` | `/marketing/topics` | Create topic |
| `GET` | `/marketing/topics/{topic_id}` | Detail |
| `PATCH` | `/marketing/topics/{topic_id}` | Update |
| `POST` | `/marketing/topics/{topic_id}/take` | Create draft pack from topic |
| `POST` | `/marketing/topics/{topic_id}/archive` | Archive |
| `POST` | `/marketing/topics/{topic_id}/mark-used` | Manual used override |
| `POST` | `/marketing/topics/import-content-bank` | Admin import from markdown |

**Suggested topic (selector):**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/marketing/topics/suggested` | Margosya `/daily_content_topic` equivalent |

Query for `GET /marketing/topics`:

| Param | Type |
|-------|------|
| `status` | draft \| approved \| used \| archived |
| `rubric` | string |
| `reusable` | bool |
| `unused_only` | bool |
| `search` | string |
| `skip`, `limit` | int |

Query for `GET /marketing/topics/suggested`:

| Param | Type |
|-------|------|
| `date` | YYYY-MM-DD |
| `exclude_topic_ids` | comma-separated UUIDs |

### 5.2 `TopicResponse`

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "legacy_topic_id": "CB-2026-06-28-015",
  "title": "AI в госсекторе",
  "rubric": "Продуктовое видение Flexity",
  "angle": "string",
  "source": "content_bank",
  "status": "approved",
  "priority": 0,
  "reusable": false,
  "recommended_channels": ["telegram", "instagram", "insights"],
  "used_count": 1,
  "last_used_at": "2026-07-07T00:00:00Z",
  "duplicate_status": "ok",
  "duplicate_detail": null,
  "created_at": "...",
  "updated_at": "..."
}
```

`duplicate_status`: `ok` | `warning` | `blocked` (from selector logic).

### 5.3 `TopicCreate` / `TopicUpdate`

```json
{
  "title": "required",
  "rubric": "required",
  "angle": "optional",
  "source": "manual",
  "status": "draft",
  "priority": 0,
  "reusable": false,
  "recommended_channels": ["telegram", "instagram"],
  "legacy_topic_id": "optional"
}
```

### 5.4 `POST /topics/{id}/take`

**Request `TakeTopicRequest`:**

```json
{
  "planned_date": "2026-07-09",
  "slug": "optional-override",
  "source": "console"
}
```

**Response `PackResponse`** (201) — created draft pack.

**Behavior:**
1. Validate topic `status = approved` (strict mode).
2. Run duplicate check.
3. Create `marketing_publication_packs` status=draft.
4. Create empty `marketing_publication_texts` rows for recommended channels.

### 5.5 Fail-closed rules

| Condition | HTTP | Error code |
|-----------|------|------------|
| No topics in bank | 409 | `no_approved_topics` |
| Topic not approved | 409 | `topic_not_approved` |
| Duplicate blocked | 409 | `topic_duplicate_blocked` |
| Pack slug exists | 409 | `pack_slug_exists` |

---

## 6. Packs API

### 6.1 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/marketing/packs` | List |
| `POST` | `/marketing/packs` | Create draft |
| `GET` | `/marketing/packs/{pack_id}` | Full detail |
| `PATCH` | `/marketing/packs/{pack_id}` | Update header/metadata |
| `POST` | `/marketing/packs/{pack_id}/preflight` | Run preflight |
| `POST` | `/marketing/packs/{pack_id}/approve` | Approve |
| `POST` | `/marketing/packs/{pack_id}/reject` | Reject |
| `POST` | `/marketing/packs/{pack_id}/publish` | Publish now |
| `POST` | `/marketing/packs/{pack_id}/schedule` | Schedule (later) |
| `POST` | `/marketing/packs/{pack_id}/cancel-schedule` | Cancel schedule (later) |
| `GET` | `/marketing/packs/last` | Margosya `/last_content_pack` |

**List query params:**

| Param | Values |
|-------|--------|
| `status` | pack aggregate status |
| `approval_status` | draft, pending, approved, rejected |
| `publish_status` | not_started, partial, published, failed |
| `planned_date` | YYYY-MM-DD |
| `planned_date_from`, `planned_date_to` | range |
| `topic_id` | uuid |
| `source` | console, margosya, import |
| `search` | slug/title |

### 6.2 `PackResponse` (detail)

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "slug": "ai-v-gossektore",
  "pack_dir_name": "2026-07-07-ai-v-gossektore",
  "title": "AI в госсекторе",
  "planned_date": "2026-07-07",
  "status": "approved",
  "preflight_status": "passed",
  "preflight_at": "2026-07-08T12:00:00Z",
  "approval_status": "approved",
  "approved_at": "2026-07-08T12:50:00Z",
  "approved_by_user_id": "uuid",
  "publish_status": "partial",
  "source": "console",
  "topic": { "id": "uuid", "legacy_topic_id": "CB-...", "title": "..." },
  "campaign": null,
  "texts": [
    { "channel": "telegram", "text": "...", "status": "ready", "char_count": 1200, "version": 1 }
  ],
  "media_assets": [
    {
      "id": "uuid",
      "role": "instagram_feed",
      "file_name": "instagram-feed.png",
      "mime_type": "image/png",
      "storage_provider": "git_path",
      "storage_key": "landing/www/assets/social/.../instagram-feed.png",
      "public_url": "https://www.flexity.asia/assets/social/.../instagram-feed.png",
      "width": 1080,
      "height": 1080,
      "status": "stored"
    }
  ],
  "channel_publish_state": {
    "telegram": { "published_at": "...", "external_url": null, "external_post_id": "15" },
    "instagram": { "published_at": "...", "external_url": "...", "external_post_id": "..." },
    "threads": { "published_at": null },
    "insights": { "published_at": null, "external_url": null }
  },
  "preflight_report": { "status": "passed", "errors": [], "warnings": [] },
  "publish_logs": [],
  "legacy_git_path": "landing/content/content-packs/2026-07-07-ai-v-gossektore",
  "created_at": "...",
  "updated_at": "..."
}
```

### 6.3 `PackCreate`

```json
{
  "topic_id": "uuid-optional",
  "title": "required-if-no-topic",
  "slug": "required",
  "planned_date": "2026-07-09",
  "source": "console",
  "campaign_id": null
}
```

### 6.4 `PackUpdate`

```json
{
  "title": "optional",
  "planned_date": "optional",
  "slug": "optional-locked-after-publish"
}
```

**Rule:** editing texts/media after approval → see §10.3 invalidation.

### 6.5 Status transitions (pack aggregate)

```text
draft
  → POST /preflight (pass) → ready_for_approval
  → POST /preflight (fail) → preflight_failed
ready_for_approval
  → POST /approve → approved
  → POST /reject → draft
approved
  → POST /publish → publishing → published | failed
approved
  → POST /schedule → scheduled (later)
```

---

## 7. Publication texts API

### 7.1 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/marketing/packs/{pack_id}/texts` | All channel texts |
| `PUT` | `/marketing/packs/{pack_id}/texts/{channel}` | Replace text |
| `PATCH` | `/marketing/packs/{pack_id}/texts/{channel}` | Partial update |

**Channels (path enum):** `telegram` | `instagram` | `threads` | `insights`

**Later:** `facebook` | `tiktok` | `whatsapp`

### 7.2 `PublicationTextUpsert`

```json
{
  "text": "string",
  "status": "draft"
}
```

### 7.3 `PublicationTextResponse`

```json
{
  "id": "uuid",
  "pack_id": "uuid",
  "channel": "telegram",
  "text": "...",
  "status": "draft",
  "version": 2,
  "char_count": 1234,
  "updated_at": "..."
}
```

### 7.4 Validation

| Channel | Rule |
|---------|------|
| `telegram` | warn if `char_count > 4096` (warning in preflight, not hard block MVP) |
| `instagram` | required for IG publish |
| `threads` | optional for MVP publish |
| `insights` | required for insights publish |

### 7.5 Fail-closed

| Condition | Error |
|-----------|-------|
| Pack not found | `pack_not_found` |
| Pack published (immutable) | `pack_immutable` |
| Invalid channel | `invalid_channel` |

---

## 8. Media API

### 8.1 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/marketing/packs/{pack_id}/media` | Upload or register |
| `GET` | `/marketing/packs/{pack_id}/media` | List assets |
| `PATCH` | `/marketing/media/{asset_id}` | Update metadata |
| `DELETE` | `/marketing/media/{asset_id}` | Remove link |
| `GET` | `/marketing/media` | Pack-linked list (P2 UI) |

### 8.2 Upload `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| `file` | binary | one of file or reference |
| `role` | string | default `instagram_feed` |
| `storage_provider` | string | MVP: `git_path` after server save |
| `storage_key` | string | MVP alternative: register existing path |
| `public_url` | string | optional if derivable |

### 8.3 `MediaAssetResponse`

```json
{
  "id": "uuid",
  "pack_id": "uuid",
  "role": "instagram_feed",
  "file_name": "instagram-feed.png",
  "mime_type": "image/png",
  "storage_provider": "git_path",
  "storage_key": "landing/www/assets/social/2026-07-07-ai-v-gossektore/instagram-feed.png",
  "public_url": "https://www.flexity.asia/assets/social/.../instagram-feed.png",
  "preview_url": null,
  "width": 1080,
  "height": 1080,
  "status": "stored",
  "validation": {
    "format_ok": true,
    "dimensions_ok": true,
    "http_status": 200
  },
  "created_at": "..."
}
```

### 8.4 MVP storage modes

| Mode | Request | Behavior |
|------|---------|----------|
| **Upload** | `file` + role | Save to git_path location; normalize 1080×1080 |
| **Register path** | `storage_key` + `public_url` | Metadata only (import/migration) |

**Later:** `storage_provider=s3`, signed `preview_url`.

### 8.5 Validation metadata

Returned after upload:

| Check | MVP |
|-------|-----|
| PNG/JPG/WebP | ✅ |
| 1080×1080 | ✅ |
| Public HTTP 200 | ✅ optional async check |

---

## 9. Preflight contract

### 9.1 Endpoint

```http
POST /api/v1/marketing/packs/{pack_id}/preflight
```

**Request (optional):**

```json
{
  "channels": ["telegram", "instagram"],
  "strict": true
}
```

### 9.2 Checks performed

| # | Check | Severity | MVP |
|---|-------|----------|-----|
| 1 | Pack metadata complete (title, slug, date) | error | ✅ |
| 2 | `telegram` text not empty | error | ✅ |
| 3 | `instagram` text not empty | error | ✅ |
| 4 | `insights` text not empty if insights publish planned | warning | ✅ |
| 5 | `instagram_feed` media present | error | ✅ |
| 6 | Media 1080×1080 | error | ✅ |
| 7 | `public_url` HTTP 200 | error | ✅ |
| 8 | Topic approved / linked | error | ✅ |
| 9 | Anti-duplicate topic rule | error/warning | ✅ |
| 10 | Telegram length > 4096 | warning | ✅ |
| 11 | Git export / origin sync | warning | ✅ transition |
| 12 | Channel dry-run eligible (scripts) | warning | ✅ |
| 13 | Channel connection available | error | ⚠️ external env check |
| 14 | Insights article exists | warning | insights publish only |

### 9.3 `PreflightResponse`

```json
{
  "pack_id": "uuid",
  "status": "passed",
  "checked_at": "2026-07-08T12:00:00Z",
  "errors": [],
  "warnings": [
    {
      "code": "pack_not_on_origin_main",
      "message": "Pack not in origin/main — GHA publish may fail",
      "channel": null
    }
  ],
  "checks": [
    { "code": "telegram_text_present", "passed": true },
    { "code": "instagram_image_http_200", "passed": true }
  ],
  "channel_eligibility": {
    "telegram": true,
    "instagram": true,
    "threads": false,
    "insights": true
  }
}
```

`status`: `passed` | `failed` | `warning` (passed with warnings — approve allowed if no errors).

### 9.4 Rules

| Rule | Enforcement |
|------|-------------|
| **No approve if preflight failed** | `POST /approve` returns 409 `preflight_failed` |
| Persist report | `pack.preflight_report_json`, `preflight_status`, `preflight_at` |
| Re-run anytime | overwrites report |

---

## 10. Approval contract

### 10.1 Endpoints

```http
POST /api/v1/marketing/packs/{pack_id}/approve
POST /api/v1/marketing/packs/{pack_id}/reject
```

### 10.2 `ApproveRequest`

```json
{
  "note": "optional"
}
```

### 10.3 `RejectRequest`

```json
{
  "reason": "optional"
}
```

### 10.4 Rules

| Rule | Detail |
|------|--------|
| Approve requires | `preflight_status = passed` (no errors) |
| Reject sets | `approval_status = rejected`, `status = draft` |
| Approve sets | `approval_status = approved`, `status = approved` |
| Audit | user_id + timestamp |
| Publish gate | `approval_status must be approved` |
| **Edit after approve** | **MVP recommendation:** any text/media change → `approval_status = draft`, `preflight_status = not_run`, require re-preflight + re-approve |

### 10.5 `ApprovalResponse`

```json
{
  "pack_id": "uuid",
  "approval_status": "approved",
  "approved_at": "...",
  "approved_by_user_id": "uuid",
  "status": "approved"
}
```

---

## 11. Publish contract

### 11.1 Endpoints

```http
POST /api/v1/marketing/packs/{pack_id}/publish
POST /api/v1/marketing/packs/{pack_id}/schedule
POST /api/v1/marketing/packs/{pack_id}/cancel-schedule
```

### 11.2 `PublishRequest`

```json
{
  "channels": ["telegram", "instagram"],
  "mode": "now",
  "export_to_git": true,
  "insights_deploy": false
}
```

| Field | MVP | Notes |
|-------|-----|-------|
| `channels` | ✅ | default: eligible approved channels |
| `mode` | `now` only | `schedule` later |
| `export_to_git` | ✅ true default | T1 bridge |
| `insights_deploy` | ✅ | separate flag for insights pipeline |

Dedicated insights publish (Margosya parity):

```http
POST /api/v1/marketing/packs/{pack_id}/publish
{ "channels": ["insights"], "insights_deploy": true }
```

### 11.3 Rules

| Rule | Detail |
|------|--------|
| Publish allowed | `approval_status = approved` |
| Per-channel | skip already published unless `force=true` (later) |
| On start | `status = publishing`, append log `action=publish_requested` |
| On success | log `status=success`, update `channel_publish_state`, `publish_status` |
| On partial | `publish_status = partial` |
| On full success | `publish_status = published`, `status = published` |
| On error | log `status=failed`, `publish_status = failed`, persist `error_message` |
| Retry | call `/publish` again (MVP manual) |
| Topic used | increment `topic.used_count`, set `last_used_at` on success |

### 11.4 `PublishResponse`

```json
{
  "pack_id": "uuid",
  "status": "partial",
  "publish_status": "partial",
  "results": [
    {
      "channel": "telegram",
      "status": "success",
      "external_url": null,
      "external_post_id": "15",
      "published_at": "2026-07-08T13:25:50Z",
      "error_message": null
    },
    {
      "channel": "instagram",
      "status": "failed",
      "error_message": "GitHub Actions dispatch failed"
    }
  ],
  "export": {
    "git_exported": true,
    "git_path": "landing/content/content-packs/2026-07-07-ai-v-gossektore"
  }
}
```

### 11.5 MVP publish execution model

**Recommendation:** **async job** with **synchronous API poll** fallback.

```text
POST /publish
  → validate + export git
  → dispatch GitHub Actions (TG/IG) OR run scripts
  → return 202 Accepted + job_id (or 200 with results if fast)

GET /marketing/packs/{pack_id}  → poll publish_status
```

**MVP simplification:** synchronous `200` if dispatch < 30s; else `202` + poll.

**Deferred:** native Meta API from Marketing service.

### 11.6 Schedule (deferred)

`POST /schedule` returns `501 Not Implemented` in MVP or hidden.

---

## 12. Publish logs API

### 12.1 Endpoints

| Method | Path |
|--------|------|
| `GET` | `/marketing/publish-logs` |
| `GET` | `/marketing/packs/{pack_id}/logs` |

**List query:**

| Param | Type |
|-------|------|
| `pack_id` | uuid |
| `channel` | string |
| `status` | success \| failed |
| `since` | datetime |
| `skip`, `limit` | int |

### 12.2 `PublishLogResponse`

```json
{
  "id": "uuid",
  "pack_id": "uuid",
  "queue_item_id": null,
  "channel": "telegram",
  "action": "published",
  "status": "success",
  "external_url": null,
  "external_post_id": "15",
  "published_at": "2026-07-08T13:25:50Z",
  "error_message": null,
  "actor": "asem",
  "metadata_json": {},
  "created_at": "2026-07-08T13:25:50Z"
}
```

Append-only — no PATCH/DELETE.

---

## 13. Lead attribution API

### 13.1 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/marketing/lead-attribution` | List |
| `POST` | `/marketing/lead-attribution` | Create attribution |
| `PATCH` | `/marketing/lead-attribution/{id}` | Update notes/touch |
| `POST` | `/marketing/packs/{pack_id}/link-lead` | Link existing WorkItem |
| `POST` | `/marketing/packs/{pack_id}/create-core-lead` | Create Party+WorkItem + attribution |

### 13.2 `LeadAttributionCreate`

```json
{
  "pack_id": "uuid-optional",
  "topic_id": "uuid-optional",
  "campaign_id": null,
  "channel": "instagram",
  "source_type": "first_touch",
  "source_url": "https://instagram.com/...",
  "content_slug": "ai-v-gossektore",
  "notes": "Написала в DM после поста",
  "party_id": null,
  "work_item_id": null,
  "utm_json": {}
}
```

### 13.3 `LeadAttributionResponse`

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "party_id": "uuid-or-null",
  "work_item_id": "uuid-or-null",
  "pack_id": "uuid",
  "topic_id": "uuid",
  "campaign_id": null,
  "channel": "instagram",
  "source_type": "first_touch",
  "source_url": "...",
  "content_slug": "ai-v-gossektore",
  "first_touch_at": "...",
  "last_touch_at": "...",
  "notes": "...",
  "core_links": {
    "crm_url": "/workspace/flexity-sales/crm",
    "work_item_title": "Lead from Instagram DM",
    "party_display_name": "Иван"
  },
  "created_at": "..."
}
```

`core_links` — UI helpers only, not stored.

### 13.4 `POST /packs/{pack_id}/link-lead`

```json
{
  "work_item_id": "uuid",
  "party_id": "uuid-optional",
  "source_type": "assisted",
  "notes": "optional"
}
```

Validates work_item belongs to same tenant.

### 13.5 `POST /packs/{pack_id}/create-core-lead`

```json
{
  "display_name": "Иван",
  "contact": { "phone": "+7...", "telegram": "@user" },
  "title": "Lead from content: AI в госсекторе",
  "source": "marketing_content",
  "notes": "Instagram DM",
  "pipeline_code": "flexity_sales_default",
  "stage_code": "new_lead"
}
```

**Behavior:**
1. Call internal `PartyService.create_party`
2. Call internal `WorkflowService.create_work_item`
3. Set `work_items.source` + `custom_fields_json.marketing`
4. Create `marketing_lead_attribution` row

### 13.6 Rules

| Rule | Detail |
|------|--------|
| No duplicate CRM table | attribution only |
| Core owns conversion | Marketing never changes party_type |
| Tenant match | party/work_item same tenant |
| `create-core-lead` MVP | **defer to P1** — manual link first if risky |

**MVP recommendation:** `POST /lead-attribution` + `link-lead` only; `create-core-lead` behind feature flag.

---

## 14. Margosya API contract

### 14.1 Margosya MUST call (target)

| Margosya action | API |
|-----------------|-----|
| List/suggest topics | `GET /marketing/topics/suggested` |
| Take topic | `POST /marketing/topics/{id}/take` |
| Create pack draft | `POST /marketing/packs` |
| Submit channel text | `PUT /marketing/packs/{id}/texts/{channel}` |
| Upload media | `POST /marketing/packs/{id}/media` |
| Preflight | `POST /marketing/packs/{id}/preflight` |
| Approve | `POST /marketing/packs/{id}/approve` |
| Reject | `POST /marketing/packs/{id}/reject` |
| Publish | `POST /marketing/packs/{id}/publish` |
| Schedule | `POST /marketing/packs/{id}/schedule` (later) |
| Pack status | `GET /marketing/packs/{id}` |
| Latest pack | `GET /marketing/packs/last` |
| Recent logs | `GET /marketing/publish-logs?limit=1` |
| Reminders | `GET /marketing/reminders/pending` (later) |

### 14.2 Margosya request headers

```http
Authorization: Bearer <margosya-service-token>
X-Tenant-ID: <flexity-sales-uuid>
X-Client: margosya-bot/1.0
```

### 14.3 Margosya MUST NOT

| Forbidden | Reason |
|-----------|--------|
| Write `flexity-content-bank.md` | Cabinet owns topics |
| Write `pack.yml` / `*.md` as SoT | Cabinet owns packs |
| Append `publish_log.yml` directly | Cabinet owns logs |
| Bypass approve gate | fail-closed |
| Call publish without approve | 409 `approval_required` |
| Cross-tenant headers | security |

### 14.4 Step intake mapping (Telegram)

```text
Topic accepted
  → POST /topics/{id}/take  → pack_id

Step 1 telegram text
  → PUT /packs/{id}/texts/telegram

Step 2 instagram
  → PUT /packs/{id}/texts/instagram

Step 3 threads
  → PUT /packs/{id}/texts/threads

Step 4 insights
  → PUT /packs/{id}/texts/insights

Photo message
  → POST /packs/{id}/media (multipart)

Inline Preflight button
  → POST /packs/{id}/preflight

Inline Approve
  → POST /packs/{id}/approve

Inline Publish
  → POST /packs/{id}/publish
```

### 14.5 Failure notifications (later)

Webhook or poll:

```http
GET /marketing/margosya/status
```

Returns pending approvals, failed publishes for bot push — P2.

---

## 15. Git transition bridge

### 15.1 Phases

| Phase | SoT | Publish path |
|-------|-----|--------------|
| **T0 (now)** | git repo files | Margosya → filesystem → GHA |
| **T1 (M6)** | PostgreSQL | API → export git → GHA |
| **T2** | PostgreSQL | export on publish only |
| **T3** | PostgreSQL | native channel services |

### 15.2 Export trigger

Called internally on:
- `POST /packs/{id}/publish` when `export_to_git=true`
- optional `POST /packs/{id}/export` (admin)

### 15.3 Minimal export contract

**Input:** pack record from DB.

**Output directory:** `landing/content/content-packs/{pack_dir_name}/`

| File | Source |
|------|--------|
| `pack.yml` | pack metadata + statuses |
| `telegram.md` | texts.telegram |
| `instagram.md` | texts.instagram |
| `threads.md` | texts.threads |
| `insights.md` | texts.insights |
| `instagram.yml` | channel_config_json |
| `visual.yml` | media metadata |
| `publish_log.yml` | append-only export of DB logs |

**Export payload (internal DTO):**

```json
{
  "slug": "ai-v-gossektore",
  "pack_dir_name": "2026-07-07-ai-v-gossektore",
  "planned_date": "2026-07-07",
  "title": "...",
  "topic_legacy_id": "CB-2026-06-28-015",
  "status": "approved",
  "approved": true,
  "texts": {
    "telegram": "...",
    "instagram": "...",
    "threads": "...",
    "insights": "..."
  },
  "media": {
    "instagram_feed_path": "landing/www/assets/social/.../instagram-feed.png",
    "public_url": "https://..."
  }
}
```

### 15.4 Import (one-time)

```http
POST /api/v1/marketing/packs/import-from-git
```

Admin-only; idempotent by `(tenant_id, slug)`.

---

## 16. Core integration contract

### 16.1 Marketing → Core (internal service calls)

| Operation | Core service | Endpoint (existing) |
|-----------|--------------|-------------------|
| Create Party | `PartyService.create_party` | `POST /api/v1/parties` |
| Create WorkItem | `WorkflowService.create_work_item` | `POST /api/v1/work-items` |
| Get WorkItem | `WorkflowService.get_work_item` | `GET /api/v1/work-items/{id}` |
| Create follow-up Task | `WorkflowService.create_task` | work-items tasks API |
| Audit | `AuditRecorder` | internal |

Marketing module should prefer **internal service layer** calls (same transaction) over HTTP loopback.

### 16.2 Marketing stores only references

```json
{
  "tenant_id": "uuid",
  "party_id": "uuid-or-null",
  "work_item_id": "uuid-or-null",
  "pack_id": "uuid",
  "topic_id": "uuid",
  "channel": "instagram",
  "content_slug": "ai-v-gossektore",
  "utm_json": {}
}
```

### 16.3 Core WorkItem metadata bridge

On create/link, write to `work_items.custom_fields_json`:

```json
{
  "marketing": {
    "attribution_id": "uuid",
    "pack_id": "uuid",
    "topic_id": "uuid",
    "content_slug": "ai-v-gossektore",
    "channel": "instagram"
  }
}
```

### 16.4 Console deep links (UI, not API)

| Target | Path |
|--------|------|
| CRM | `/workspace/{slug}/crm` |
| WorkItem | future detail route or CRM card |
| Party | `/workspace/{slug}/clients/{partyId}` |

### 16.5 Demo access (later)

`POST /marketing/lead-attribution/{id}/demo-access` — deferred.

MVP: `notes` field on attribution.

---

## 17. Error model

### 17.1 HTTP mapping

| HTTP | When |
|------|------|
| 400 | validation error |
| 401 | unauthenticated |
| 403 | `unauthorized` / `cross_tenant_access_denied` / module disabled |
| 404 | not found |
| 409 | business rule / fail-closed |
| 422 | pydantic validation |
| 501 | not implemented (schedule MVP) |
| 502 | external publish dispatch failed |

### 17.2 Standard error body

```json
{
  "error": {
    "code": "preflight_failed",
    "message": "Human readable message",
    "details": {
      "pack_id": "uuid",
      "errors": [{ "code": "instagram_image_missing", "message": "..." }]
    }
  }
}
```

Align with existing `CoreOpsError` handlers.

### 17.3 Error codes

| Code | HTTP | When |
|------|------|------|
| `unauthorized` | 401/403 | no auth |
| `cross_tenant_access_denied` | 403 | wrong tenant |
| `module_disabled` | 403 | marketing module off |
| `topic_not_found` | 404 | |
| `no_approved_topics` | 409 | selector empty |
| `topic_not_approved` | 409 | take on non-approved |
| `topic_duplicate_blocked` | 409 | anti-duplicate |
| `pack_not_found` | 404 | |
| `pack_slug_exists` | 409 | unique constraint |
| `pack_immutable` | 409 | edit after published |
| `preflight_failed` | 409 | approve blocked |
| `approval_required` | 409 | publish without approve |
| `approval_invalidated` | 409 | needs re-preflight |
| `channel_not_connected` | 409 | token/env missing |
| `invalid_channel` | 400 | bad channel enum |
| `publish_failed` | 409/502 | dispatch failed |
| `media_validation_failed` | 422 | image rules |
| `core_lead_create_failed` | 502 | Core service error |
| `git_export_failed` | 502 | transition bridge |

---

## 18. MVP API scope

### 18.1 Included in M6 first implementation

| Area | Endpoints |
|------|-----------|
| Dashboard | `GET /marketing/dashboard` |
| Topics | list, create, get, patch, suggested, take, archive, mark-used, import-content-bank |
| Packs | list, create, get, patch, last, preflight, approve, reject, publish |
| Texts | get all, PUT per channel |
| Media | POST upload/register, GET by pack, PATCH metadata |
| Logs | GET global, GET by pack |
| Attribution | list, create, patch, link-lead |
| Export | internal on publish + optional admin import |

### 18.2 Deferred

| Area | Reason |
|------|--------|
| `POST /schedule`, cancel-schedule | no queue table |
| `GET /marketing/reminders` | no reminders table |
| Channel connections CRUD | tokens in env |
| Campaigns / offers CRUD | post-MVP |
| Content plan items API | P3 UI placeholder |
| `POST /create-core-lead` | risk; manual link first |
| Reports API | UI aggregates client-side MVP |
| `GET /marketing/margosya/status` | P2 |
| Native Meta/WhatsApp publish | later |
| Rate limiting | later |
| Idempotency keys | later |

### 18.3 M6 endpoint count

**~25 endpoints** (including import/admin).

---

## 19. Security notes

| Topic | Rule |
|-------|------|
| Auth | JWT for UI; service token for Margosya |
| Tenant | `X-Tenant-ID` required; validated membership |
| Tokens in response | never return channel secrets |
| Media URLs | public URLs OK; preview signed later |
| Audit | approve, publish, attribution create |
| Publish gate | approve + preflight pass |
| Bot separation | Margosya scoped credentials |
| Rate limit | publish endpoints — post-MVP |
| Input size | text max 64KB per channel; upload max 10MB MVP |
| CORS | same as Core API |

---

## 20. Open questions

| # | Question | M4 recommendation |
|---|----------|---------------------|
| 1 | `tenant_id` or `slug` in route? | **Header `X-Tenant-ID` only** (Core convention) |
| 2 | Native API publish vs GHA bridge MVP? | **GHA bridge + git export** |
| 3 | Media storage initially? | **git_path** register + optional upload |
| 4 | Margosya bot auth? | **Service bearer token** per env |
| 5 | `create-core-lead` in MVP? | **Defer** — link-lead + manual Core create |
| 6 | Approval invalidates on edit? | **Yes** — reset to draft + re-preflight |
| 7 | Publish async or sync MVP? | **Sync with 30s timeout**; 202 later |
| 8 | Flat list vs wrapped pagination? | **Flat array** (match Core) |
| 9 | Module code `marketing` vs `content_ops`? | **`marketing`** |
| 10 | Separate public API? | **No** — all authenticated |

---

## 21. Recommended next step

### 21.1 Path

```text
M0 ✅ → M1 ✅ → M2 ✅ → M3 ✅ → M4 ✅ → M5 implementation plan → HQ approval → M6 code
```

### 21.2 M4b trigger (optional)

**M4b — API cut review** if HQ wants:
- fewer than 25 endpoints in M6;
- drop `import-content-bank` from MVP;
- defer git export to manual admin only.

**Recommendation:** scope acceptable with M6 phased delivery (P0 endpoints first).

### 21.3 M5 inputs

M5 implementation plan should list:
- `backend/app/modules/marketing/` files
- Pydantic schemas per section
- Service layer + export bridge
- `platform-console` API client hooks
- Tests per fail-closed rule
- Alembic revision for 6 MVP tables

---

## 22. HQ summary

### 1. Path

```text
M0 → M1 → M2 → M3 → M4 (this doc) → M5 → M6
```

### 2. API namespace recommendation

```text
/api/v1/marketing/*
```

Tenant via **`X-Tenant-ID` header** (existing Core convention).  
Module guard: `require_module("marketing")`.

### 3. P0 endpoints

| Group | Key endpoints |
|-------|---------------|
| Dashboard | `GET /marketing/dashboard` |
| Topics | `GET/POST /topics`, `GET /topics/suggested`, `POST /topics/{id}/take` |
| Packs | `GET/POST /packs`, `GET /packs/{id}`, preflight/approve/reject/publish |
| Texts | `PUT /packs/{id}/texts/{channel}` |
| Media | `POST /packs/{id}/media` |
| Logs | `GET /packs/{id}/logs` |
| Attribution | `GET/POST /lead-attribution`, `POST /packs/{id}/link-lead` |

### 4. Margosya API contract

Service token + `X-Tenant-ID`; all actions via Marketing API; **no filesystem SoT**; step intake maps to take + PUT texts + POST media + preflight/approve/publish.

### 5. Core integration

Internal `PartyService` / `WorkflowService`; attribution stores `party_id` + `work_item_id`; optional `custom_fields_json.marketing` on WorkItem; no duplicate CRM.

### 6. Git transition bridge

T1: DB SoT → export to `landing/content/content-packs/` on publish → existing GHA/scripts unchanged.

### 7. MVP API scope

~25 endpoints; 6 DB tables; GHA publish bridge; defer schedule, reminders, campaigns, create-core-lead, native channel APIs.

### 8. Deferred API scope

Queue scheduler, channel token UI, reports API, Margosya status webhook, demo access API, Meta/WhatsApp native, idempotency, rate limits.

### 9. Main risks

| Risk | Mitigation |
|------|------------|
| GHA coupling | explicit export step; document in M5 |
| Async publish complexity | sync MVP first |
| create-core-lead scope creep | defer; link only |
| Approval invalidation UX | clear UI badges |
| Margosya/API dual run during T1 | feature flag |

### 10. Recommended next step

**M5 — MVP implementation plan** (exact files, migrations, tests, rollout phases).

Optional: **M4b API cut review** if HQ wants smaller first slice.

### 11. Implementation approval needed?

**Yes.** Code, migrations, and Margosya bot changes only after approved **M5**.

---

*Документ подготовлен без изменений кода, migrations, deploy, production, Margosya bot и Core public inbound.*
