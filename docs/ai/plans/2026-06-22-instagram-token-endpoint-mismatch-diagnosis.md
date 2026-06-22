# Diagnosis Plan: Instagram Token / API Endpoint Mismatch

## Goal

Зафиксировать причину падения GitHub Actions workflow `Publish first Instagram live post` на live step с ошибкой:

```text
Instagram API error during media container creation (HTTP 400):
Invalid OAuth access token - Cannot parse access token (code 190)
```

При этом dry-run проходил: `Done. Would publish: 1. Errors: 0`.

Этот документ — **read-only diagnosis**. Он не разрешает изменение кода, workflow, secrets, повторный `--live` run или API calls.

## Classification

- Project: Flexity
- Category: `documentation_only` / `research_only`
- Risk: **high** — credential mismatch + token exposure in chat
- Observed failure: workflow live step, media container creation
- Dry-run success: expected (no API contact)

## Incident Summary

| Signal | Interpretation |
|--------|----------------|
| Dry-run `Would publish: 1` | Local gates passed; publisher did not validate token type or API host |
| Secrets non-empty, masked in Actions | Secret **presence** OK; secret **type/host compatibility** not verified |
| HTTP 400, OAuth code 190 on create container | Token rejected by API host before business logic |
| User obtained token via Meta **Instagram API setup** with prefix `IGAA...` | Strong indicator of **Instagram Login** (Instagram User access token), not Facebook Graph Login token |
| Token pasted in chat (prefix only disclosed) | Token must be treated as **compromised** and rotated before any retry |

---

## 1. What the Code Uses Today

Source: `scripts/content/publish_instagram_live.py`

| Item | Current value |
|------|---------------|
| API host | **`graph.facebook.com` only** |
| API version | `v21.0` (constant `GRAPH_API_VERSION`) |
| Base URL | `https://graph.facebook.com/v21.0` |
| Media container path | `POST /{INSTAGRAM_USER_ID}/media` |
| Publish path | `POST /{INSTAGRAM_USER_ID}/media_publish` |
| `graph.instagram.com` | **not used** |
| Token transport | `access_token` form field in POST body |
| Dry-run | No HTTP; secrets optional |

Concrete URLs at runtime:

```text
POST https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media
POST https://graph.facebook.com/v21.0/{INSTAGRAM_USER_ID}/media_publish
```

---

## 2. What Documentation and Plans Assumed

### `docs/ai/plans/2026-06-22-instagram-meta-api-readiness-plan.md`

- Intended flow: **Page-connected** via Instagram Professional account + **Facebook Page**
- Explicit rule: *«Нельзя смешивать его с другим Instagram Login flow без отдельного решения»*
- Secrets:
  - `INSTAGRAM_USER_ID` — Instagram Professional account ID
  - `INSTAGRAM_ACCESS_TOKEN` — access token with publish rights for connected account/Page
- Token type not hard-coded in repo, but flow description matches **Instagram Graph API with Facebook Login**

### `docs/content/instagram-publishing.md`

- Documents same two-step flow: `POST /{INSTAGRAM_USER_ID}/media` then `media_publish`
- Does not name `graph.facebook.com` vs `graph.instagram.com` explicitly
- Lists secrets `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN`
- Notes Graph API version `v21.0` must be verified in Meta dashboard

### Other plan files (live publisher, first-live readiness, workflow)

- Same secret names
- Same publish paths (relative to user id)
- No mention of Instagram Login–specific host or `IGAA` token format
- Workflow passes secrets to publisher unchanged

### Official Meta platform model (for diagnosis, not verified by live call here)

Meta documents two supported Instagram Platform authentication paths:

| Flow | Typical token | API host |
|------|---------------|----------|
| **Instagram API with Instagram Login** (Business Login for Instagram) | Instagram User access token | **`graph.instagram.com`** |
| **Instagram API with Facebook Login** (Page-connected) | Facebook User or Page access token | **`graph.facebook.com`** |

Content publishing paths (`/{ig-user-id}/media`, `/{ig-user-id}/media_publish`) exist on **both** hosts, but **token type and host must match**.

---

## 3. Root Cause Hypothesis

**Most likely mismatch:** GitHub secret `INSTAGRAM_ACCESS_TOKEN` contains an **Instagram Login** token (`IGAA...` prefix observed by user), while publisher sends it to **`graph.facebook.com`**.

Meta error code **190** (*Invalid OAuth access token — Cannot parse access token*) is consistent with:

- wrong token family for the selected host;
- malformed/truncated token (less likely if copied from Meta UI intact);
- expired/revoked token (usually different subcode/message, but still possible).

**Why dry-run still passed:** dry-run only checks pack metadata and does not call Meta API or validate token compatibility with API host.

**Secondary checks still needed before retry (manual, in Meta dashboard):**

- `INSTAGRAM_USER_ID` matches the Instagram professional account that issued the token
- token has content-publish permission for the chosen flow
- Graph API version `v21.0` still supported for that app

---

## 4. Why `IGAA...` Token Likely Does Not Fit Current Endpoint

User reports token obtained through **Meta Instagram API setup** (Instagram Login path), prefix **`IGAA...`**.

For diagnosis (without using the token value):

- `IGAA...` aligns with **Instagram User access tokens** from Instagram Login / Business Login for Instagram
- Flexity publisher posts to **`graph.facebook.com`**, which expects **Facebook Login** token family (commonly `EAA...` User tokens or Page tokens derived from Page-connected setup)
- Sending Instagram Login token to Facebook Graph host commonly yields OAuth **190** at the first authenticated request — matching observed failure at **media container creation**

This is a **host/token-family mismatch**, not a content-pack or dry-run gate bug.

---

## 5. Two Fix Paths

### Path A — Keep code on Facebook Graph endpoint (recommended for first publish)

**Action:** Obtain credentials matching existing implementation.

1. Confirm Instagram Professional account is linked to a Facebook Page
2. In Meta Developer App, use **Instagram API with Facebook Login** / Page-connected publishing setup
3. Generate **long-lived Facebook User token** (or appropriate Page token per Meta docs) with Instagram content publishing permissions for the connected account
4. Store in GitHub Secrets:
   - `INSTAGRAM_USER_ID` = Instagram Business/Creator user id (IG id)
   - `INSTAGRAM_ACCESS_TOKEN` = **Facebook Graph–compatible** token (not `IGAA...` Instagram Login token)
5. **Revoke and replace** the compromised `IGAA...` token
6. Re-run workflow (after separate approval)

**Code changes:** none required for host mismatch (optional: document token type in docs; optional: validate token prefix/host in publisher — separate plan)

**Pros:**

- Matches all existing plans and implemented publisher
- Smallest change surface for first publish
- Workflow unchanged

**Cons:**

- Requires Facebook Page linkage and Facebook Login token issuance (more setup steps)

### Path B — Adapt code to Instagram Login token / `graph.instagram.com`

**Action:** Change publisher to Instagram Login host and permissions model.

Likely changes:

| Area | Change |
|------|--------|
| `publish_instagram_live.py` | `GRAPH_API_BASE` → `https://graph.instagram.com/{version}` (or configurable host) |
| Permissions docs | `instagram_business_basic`, `instagram_business_content_publish` (Instagram Login names per Meta docs) |
| Tests | mock `graph.instagram.com` URLs |
| `docs/content/instagram-publishing.md` | document Instagram Login flow explicitly |
| Plans | update meta-api-readiness assumptions |
| Workflow | possibly unchanged if same secret names, but document expected token type |

**Pros:**

- Aligns with how user already obtained `IGAA...` token
- No Facebook Page token exchange if Instagram Login is sufficient for their app product

**Cons:**

- Requires **approved implementation plan** + code change + tests
- Diverges from all prior Flexity plans (Facebook Login / Page-connected)
- Higher risk for first publish (new code path untested in production)
- Must still rotate compromised token and re-issue Instagram Login token after fix

---

## 6. Safer Choice for First Publish

**Recommend Path A** for the first successful publish.

Reasons:

1. Publisher, tests, docs, and workflow were designed for **Facebook Graph host**
2. Meta readiness plan explicitly chose Page-connected flow and warned against mixing Instagram Login without a separate decision
3. Path A is primarily **credential correction**, not a new code path
4. Path B needs new implementation approval and retesting before workflow retry

Path B remains valid if business decision is to standardize on Instagram Login only — but it should be a **separate implementation plan**, not a quick secret swap.

---

## 7. Required Changes by Path (future work, not in this diagnosis)

### Path A (credentials only)

| Artifact | Change |
|----------|--------|
| GitHub Secrets | Rotate `INSTAGRAM_ACCESS_TOKEN` to Facebook Graph–compatible token; verify `INSTAGRAM_USER_ID` |
| Code | none (preferred) |
| Docs | optional note: token must match `graph.facebook.com` / Facebook Login flow |
| Workflow | none |

### Path B (Instagram Login adaptation)

| Artifact | Change |
|----------|--------|
| `scripts/content/publish_instagram_live.py` | configurable API host; default or branch for `graph.instagram.com` |
| `tests/scripts/content/test_publish_instagram_live.py` | update mocked URLs and cases |
| `docs/content/instagram-publishing.md` | Instagram Login flow, host, permission names |
| `docs/ai/plans/*` | align readiness assumptions |
| `.github/workflows/instagram-live-publish.yml` | likely unchanged secret names; document token type in plan |
| GitHub Secrets | new Instagram Login long-lived token after revoke |

---

## 8. Token Compromise — Mandatory Rotation

Regardless of Path A or B:

- User disclosed token **prefix** (`IGAA...`) in chat → treat token as **exposed**
- **Do not reuse** the same token value in GitHub Secrets
- In Meta dashboard / Instagram API setup:
  1. Revoke the exposed token / regenerate credentials
  2. Issue a new token using the **chosen** flow (A or B)
  3. Update `INSTAGRAM_ACCESS_TOKEN` in GitHub Secrets only via UI
- Never commit token values; never paste full token in chat, logs, or workflow output

---

## 9. Pre-Retry Checklist (no API from this task)

Before next workflow run (after fix approval):

- [ ] Old `IGAA...` token revoked
- [ ] New token type matches chosen path (A: Facebook Graph token; B: new Instagram Login token + code deployed)
- [ ] `INSTAGRAM_USER_ID` matches target professional account
- [ ] `gh secret list` shows secret names only; values updated in GitHub UI
- [ ] Local dry-run still `Would publish: 1` (pack still approved, not published)
- [ ] Meta dashboard: permissions + API version confirmed
- [ ] Separate explicit approval for workflow re-run

---

## 10. Forbidden (this diagnosis)

- Meta / Instagram API calls
- `--live` locally or in Actions
- Reading or printing secret values
- Changing GitHub secrets from this task
- Changing publisher code, workflow, or content-packs

---

## Approval

Status: **waiting for approval**

After approval of this diagnosis, next safe step is **choose Path A or Path B**, rotate token, then either:

- **Path A:** re-run workflow with corrected Facebook Graph token (no code change), or
- **Path B:** create implementation plan for `graph.instagram.com` support, then rotate token and deploy

This diagnosis file alone does not authorize workflow re-run.
