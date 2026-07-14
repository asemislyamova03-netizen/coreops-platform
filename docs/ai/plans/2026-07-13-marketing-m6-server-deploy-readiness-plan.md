# Implementation Plan: Marketing M6 server deploy readiness

**Дата:** 2026-07-13  
**Проект:** Flexity / `coreops-platform`  
**Категория:** `documentation_only`  
**Статус:** readiness plan — **код / deploy / migrations / env не менялись**  

**Аудит-отчёт:** [2026-07-13-marketing-m6-server-deploy-readiness-report.md](../reports/2026-07-13-marketing-m6-server-deploy-readiness-report.md)  
**Local smoke (после local 0015):** [2026-07-13-marketing-m6-local-0015-upgrade-and-fe3-smoke-report.md](../reports/2026-07-13-marketing-m6-local-0015-upgrade-and-fe3-smoke-report.md)

---

## Task Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `documentation_only` |
| **Risk level** | high (future production DB path includes 0013+0014+0015) |
| **Intended scope** | этот plan + readiness report |
| **Forbidden now** | code, deploy, migrations, env, module enable, DB writes, publish |

---

## Goal

Подготовить **safe server deploy readiness** для Marketing Cabinet M6 (BE1–BE5 + FE1–FE3), **без** выполнения deploy сейчас.

Ответить: что на сервере сейчас, что деплоить, риск миграций, module state, env, порядок, smoke, rollback, gates.

---

## Executive verdict (from read-only audit)

| Question | Answer |
|----------|--------|
| Marketing backend on server? | **No** — no `app/modules/marketing`, OpenAPI marketing paths = 0, `GET /api/v1/marketing/health` → **404** |
| Marketing tables on server? | **No** |
| Server alembic? | **`0012_booking_e1`** (not 0014) |
| Can jump straight to 0015? | **No** — chain is `0012 → 0013 → 0014 → 0015` |
| Console marketing UI? | **Partial FE1 only** (nav/routes/placeholders). **No FE2/FE3** (`Взять в работу`, next-action, publish honesty missing) |
| `flexity-sales` marketing module? | Tenant exists (`90553fe9-…`). **marketing not in** `module_definitions`; **not enabled** in `tenant_modules` |
| Env for Marketing MVP? | **None required** |
| Local Marketing code in git on server? | Server `main @ 1034ef8` has **no** marketing files; local Marketing mostly **untracked / not pushed** |

**Deploy is higher risk than CRM console-only slices** because it needs: backend package + **three** Alembic upgrades (0013 payment direction, 0014 branches, 0015 marketing) + console rebuild + module seed/enable.

---

## 1. Server current state (read-only)

| Item | Observed 2026-07-13 |
|------|---------------------|
| Host | `ip-172-26-3-31` / `flexity.asia` |
| Path | `/opt/flexity/coreops` |
| Git | `1034ef8` `main` — «Restore Flexity sales tenant template» |
| `coreops.service` | **active** (`uvicorn` via `/opt/flexity/envs/coreops/bin/python`, port 8005) |
| Health | `https://flexity.asia/api/v1/health` → **200** (`environment: staging` label, DB connected) |
| Marketing health | `https://flexity.asia/api/v1/marketing/health` → **404** `Not Found` |
| Alembic files on disk | only `0001`…`0011` present; **no** `0012`/`0013`/`0014`/`0015` files |
| Alembic DB stamp | **`0012_booking_e1`** |
| Marketing module dir | **absent** |
| Marketing in router/seed | **absent** |
| Console dist | `/opt/flexity/coreops/platform-console/dist/` active JS `index-CW_cVLb3.js` |
| Marketing UI markers | HIT: `marketing`, `Маркетинг`, `marketing/topics`, `M6-FE1`, `только просмотр` · MISS: FE3 strings |
| Marketing SPA URL | `/console/workspace/flexity-sales/marketing` → HTTP **200** (SPA shell; API will fail) |
| CRM URL | `/console/workspace/flexity-sales/crm` → **200** |

---

## 2. Tenant / module state

| Item | Value |
|------|--------|
| Tenant slug | `flexity-sales` |
| Tenant id | `90553fe9-22d1-458d-ab84-c7353f2d80e2` ✅ exists |
| Enabled modules (sample) | `accounting`, `ai`, `catalog`, `crm`, `documents`, `finance`, `integrations`, `parties` |
| `marketing` in `tenant_modules` | **no row** |
| `marketing` in `module_definitions` | **absent** |
| Access model | Marketing routes use `Depends(require_module("marketing"))` — API needs module **enabled** after code deploy |
| Enable path | Provider `enable_module` can `_get_or_create_tenant_module`; definition should be seeded from updated `MODULE_DEFINITIONS` (seed / startup / explicit seed call) |

**Do not enable marketing in this readiness task.** Gate after BE+migration.

---

## 3. Migration readiness

### 3.1 Target marketing migration

| Field | Value |
|-------|--------|
| File | `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` |
| Revision | `0015_marketing_cabinet_mvp` |
| Down revision | `0014_core_branches_baseline` |
| Local head | `0015_marketing_cabinet_mvp` |
| Touches existing tables? | **No** (create-only 6 tables + indexes/FKs to `tenants` / pack/topic) |
| Downgrade | **Yes** — drops 6 tables + enum cleanup |

**Tables:**

1. `marketing_content_topics`  
2. `marketing_publication_packs`  
3. `marketing_publication_texts`  
4. `marketing_media_assets`  
5. `marketing_publish_logs`  
6. `marketing_lead_attribution`

### 3.2 Production chain gap (critical)

Local / required chain:

```text
0012_booking_e1
  → 0013_c1c_payment_direction   (ADD payments.direction)
  → 0014_core_branches_baseline  (CREATE branches + tenants.default_branch_id + backfill)
  → 0015_marketing_cabinet_mvp   (CREATE 6 marketing tables)
```

| Check | Server |
|-------|--------|
| Stamp | `0012_booking_e1` |
| `payments.direction` (0013) | **missing** |
| `branches` / `tenants.default_branch_id` (0014) | **missing** |
| Marketing tables (0015) | **missing** |
| Direct `0012 → 0015`? | **Impossible** with current revision graph |

**Risk:** Marketing deploy **inherits** production risk of **0013 + 0014**, which are not Marketing-specific.

| Migration | Risk | Notes |
|-----------|------|--------|
| 0013 | medium | alters live `payments` |
| 0014 | **high** | new `branches`, FK on `tenants`, backfill per tenant |
| 0015 | medium | new empty tables only; downgrade relatively clean |

### 3.3 Answers required by HQ

| Question | Answer |
|----------|--------|
| Can server upgrade from current version to 0015 directly? | **No** — must apply **0013 then 0014 then 0015** |
| Later local migrations after 0015? | **No** — head = 0015 |
| Is server at 0014? | **No** — server at **0012** |
| Is head = 0015? | **Yes** (local) |

### 3.4 Alternative (needs separate HQ Change Request — not default)

Create a **one-off** marketing-only migration with `down_revision = 0012_booking_e1` to skip 0013/0014.  
**Not recommended** without explicit HQ: forks Alembic history, still leaves branches/payment gaps for Consulting import.

---

## 4. Backend deploy requirements

### 4.1 Must deploy (Marketing MVP)

| Area | Paths |
|------|--------|
| Module | `backend/app/modules/marketing/**` |
| Router | `backend/app/api/v1/router.py` (include marketing) |
| Models import | `backend/app/modules/models.py` |
| Registry seed | `backend/app/modules/module_registry/seed.py` (+ service if local diffs required) |
| Migrations | `0013`, `0014`, `0015` files onto server `alembic/versions/` |
| Branches support for 0014 consistency | `backend/app/modules/branches/**`, `tenants/models.py` (default_branch_id) as needed by app after 0014 |

### 4.2 Packaging constraint

Local Marketing is largely **untracked / not on server git**. Deploy cannot be «git pull only». Use explicit file package / commit-first gate (like prior CRM backend deploys under `/opt/flexity/backups/backend-…`).

### 4.3 Config / env

| Item | Needed? |
|------|---------|
| New `.env` keys for Marketing MVP | **No** |
| Publish/export tokens | **No** (publish disabled) |
| Margosya | **No** |
| Binary upload / S3 | **No** (metadata only) |
| `SEED_ON_STARTUP` | Prefer **not** flipping env; seed marketing definition via controlled service call / one-shot after deploy |

### 4.4 Local verification already done

- Marketing pytest suite (topics/packs/texts/preflight) previously green  
- Local DB upgraded to 0015 + FE3 API smoke PASS  

---

## 5. Frontend deploy requirements

| Item | Detail |
|------|--------|
| Routes / nav | `platform-console/src/routes.tsx`, `WorkspaceSidebar.tsx` |
| FE1–FE3 pages | `platform-console/src/pages/workspace/marketing/**` |
| API/types | `src/api/marketing.ts`, `src/types/marketing.ts` |
| CSS | `src/index.css` (marketing section) |
| Build | `VITE_API_BASE_URL=https://flexity.asia/api/v1 npm run build` |
| Target | `/opt/flexity/coreops/platform-console/dist/` |
| Backup pattern | `/opt/flexity/backups/console-dist-m6-marketing-<timestamp>/` |

Server today: **FE1 shell only**. Need full FE2+FE3 bundle for usable workflow.

---

## 6. Env readiness

**Confirmed:** Marketing MVP needs **no new env vars**.  
Keep publish/export off. Do not add Margosya tokens. Do not change public inbound env in this deploy.

---

## 7. Recommended deploy order (after gates)

**Safest recommended sequence:**

1. **Gate A** — approve this readiness (and decide: full chain 0013→0015 vs CR fork).  
2. **Commit / package** Marketing + required migrations/deps (no dirty mixed CRM deploy).  
3. **Backup**  
   - DB snapshot / `pg_dump` (schema+data preferred)  
   - backend files to `/opt/flexity/backups/backend-m6-marketing-<ts>/`  
   - console dist to `/opt/flexity/backups/console-dist-m6-marketing-<ts>/`  
4. **Gate B — Backend + migrations**  
   - Copy migration files `0013`–`0015` + marketing module + router/seed/models/branches as scoped  
   - `alembic upgrade head` on server (expect `0012→0013→0014→0015`)  
   - `systemctl restart coreops`  
   - Verify `/api/v1/health` + `/api/v1/marketing/health`  
5. **Seed + enable marketing for `flexity-sales`** (explicit HQ sub-gate)  
6. **Gate C — Console**  
   - Build with production API base  
   - Backup + replace `platform-console/dist`  
7. **Gate D — Production smoke** (controlled test topic; publish stays disabled)  
8. **Gate E — Keep / rollback**

**Why not migrate before backend code?**  
Migration files must be on disk first; app code should be present before traffic hits new routes. Prefer: **files on disk → migrate → restart → verify health → enable module → console**.

**Why not console before BE?**  
Server already has FE1 shell without API — shipping FE3 first worsens broken UX.

---

## 8. Smoke plan (Gate D only — not now)

| # | Check | Expect |
|---|--------|--------|
| 1 | `GET /api/v1/health` | 200 |
| 2 | `GET /api/v1/marketing/health` (+ tenant header if required) | 200 |
| 3 | Open `/console/workspace/flexity-sales/marketing` | UI loads |
| 4 | Create topic `M6 Server Smoke Topic` | 201 |
| 5 | Approve topic → Take | pack created, detail opens |
| 6 | Edit one text channel | saved |
| 7 | Add + edit media metadata | OK |
| 8 | Preflight | report visible; pack may `passed` with warning |
| 9 | Approve pack | `approval_status=approved` |
| 10 | Packs list + filters | smoke pack visible |
| 11 | Publish tab | disabled honesty; **no** publish action |
| 12 | CRM `/crm` | 200 |
| 13 | Kindergarten workspace CRM | 200 |
| 14 | Public inbound remains as currently configured | no accidental disable; no marketing side effects |
| 15 | No publish/export / Margosya / binary upload | none |

Use a clearly named smoke topic; archive afterward if desired.

---

## 9. Rollback plan

| Layer | Action | Feasibility |
|-------|--------|-------------|
| Console | Restore `/opt/flexity/backups/console-dist-m6-marketing-<ts>/` → `dist/` | **Easy** (static) |
| Backend files | Restore backup tree; restart `coreops` | **Easy/medium** |
| Module | Disable `marketing` for tenant / leave definitions | **Easy** (stops API use) |
| DB 0015 only | `alembic downgrade 0014_core_branches_baseline` drops marketing tables | **Possible** if no precious marketing data |
| DB 0014 | Downgrade drops `branches` / column — **risk** if anything started using branches | **Hard / unsafe** if used |
| DB 0013 | Downgrade drops `payments.direction` — **risk** if rows written | **Medium/hard** |
| Full chain rollback to 0012 | Only with HQ + verified backups | **Do not assume easy** |

**Honest policy:** if 0013/0014 already applied and used, prefer **feature disable** (module off + console rollback) over DB downgrade.

---

## 10. Risk classification

| Risk | Level | Mitigation |
|------|-------|------------|
| Production alembic chain 0013+0014+0015 | **High** | Separate HQ; DB backup; consider splitting gates (0013/0014 first) |
| Local code not in server git | **High** | Explicit package / commit gate before deploy |
| Module not seeded/enabled | **Medium** | Seed definitions + enable only after health |
| Console FE1 without BE already live | **Medium** | Deploy BE before FE3; expect interim broken Marketing nav |
| Empty marketing tables | Low | Expected |
| Smoke data in production | Low | Named smoke topic; archive |
| Publish/export accidental enable | Low | Keep tab disabled; no BE6 |
| Client-side filters limit 200 | Low | Accept MVP |
| Dirty local tree mixes CRM+marketing+booking | **High** | Deploy **only** approved Marketing scope files |

---

## 11. Decision gates

| Gate | Meaning | Unlocks |
|------|---------|---------|
| **A** | Readiness approved; choose full chain vs CR fork | Packaging |
| **B** | Backend files + alembic upgrade + restart | Marketing API |
| **B2** (sub) | Seed/enable `marketing` on `flexity-sales` | Tenant access |
| **C** | Console dist deploy | Usable UI |
| **D** | Production smoke | Confidence |
| **E** | Keep enabled **or** rollback | Steady state |

**No Gate B/C/D/E in this task.**

---

## 12. Approval

| Gate | Status |
|------|--------|
| Documentation readiness (this plan) | waiting HQ review |
| Server deploy | **not approved** |
| Migrations on server | **not approved** |
| Module enable | **not approved** |

---

## Next safe step

1. HQ review Gate A.  
2. Decide: run **0013→0014→0015** as part of Marketing deploy, **or** split «schema catch-up» deploy first.  
3. Commit/package Marketing-only artifacts (no mixed unrelated dirty tree).  
4. Only then approve Gate B.
