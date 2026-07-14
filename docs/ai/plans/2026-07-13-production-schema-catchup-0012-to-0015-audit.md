# Gate A Audit: Production schema catch-up 0012→0015

**Дата:** 2026-07-14  
**Проект:** Flexity / `coreops-platform`  
**Категория:** `documentation_only`  
**Статус:** audit only — **код / deploy / migrations / env / DB не менялись**

**Родительские документы:**
- [2026-07-13-marketing-m6-server-deploy-readiness-plan.md](./2026-07-13-marketing-m6-server-deploy-readiness-plan.md)
- [2026-07-13-marketing-m6-server-deploy-readiness-report.md](../reports/2026-07-13-marketing-m6-server-deploy-readiness-report.md)
- [2026-07-13-marketing-m6-local-0015-upgrade-and-fe3-smoke-report.md](../reports/2026-07-13-marketing-m6-local-0015-upgrade-and-fe3-smoke-report.md)

---

## Task Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `documentation_only` |
| **Risk level** | high (future prod schema path) |
| **Intended scope** | этот plan + audit report |
| **Forbidden** | code, migrations run, deploy, env, DB writes, module enable |

---

## Goal

Понять риск production catch-up:

```text
0012_booking_e1 → 0013 → 0014 → 0015_marketing_cabinet_mvp
```

и выбрать:

- **A** — combined Marketing deploy с 0013–0015  
- **B** — schema catch-up 0012→0014 отдельно, Marketing 0015 позже  
- **C** — hold Marketing; сначала стабилизация кода / cleaner path  

---

## Executive recommendation

**Option C now**, then **Option B** for schema, then Marketing 0015.

| Priority | Why |
|----------|-----|
| 1. **C — Hold Marketing deploy** | Marketing/backend migrations largely **untracked**; SCP from dirty tree too risky; 0013/0014 are **not Marketing** |
| 2. Then **B — Split** | Catch-up `0012→0014` with own backup/smoke, isolated from Marketing UI/module enable |
| 3. **Not A** | Mixing Consulting finance + branches + Marketing + untracked FE in one shot raises blast radius |

**Next slice after this audit:**  
**Gate A1 — commit/stabilize Marketing + alembic 0013/0014/0015 (+ branches deps) into a clean deployable package** (branch/PR), then Gate A2 production schema catch-up 0012→0014.

---

## 1. Migration chain (inspected)

Local Alembic head: `0015_marketing_cabinet_mvp`  
Server DB stamp (read-only): `0012_booking_e1`

```text
0012_booking_e1
  → 0013_c1c_payment_direction
  → 0014_core_branches_baseline
  → 0015_marketing_cabinet_mvp (head)
```

Direct `0012 → 0015` **impossible** with current revision graph.

Server disk still has migration files only through `0011`; stamp is already `0012` (file for 0012 missing on server — catch-up deploy must copy **0013–0015** at minimum; include `0012` file for history consistency if absent).

---

## 2. Per-migration dossier

### 2.1 `0013_c1c_payment_direction`

| Field | Value |
|-------|--------|
| File | `backend/alembic/versions/20260708_0013_c1c_payment_direction.py` |
| Revision | `0013_c1c_payment_direction` |
| Down | `0012_booking_e1` |
| Branch/depends | none |
| Classification | **Core / Finance** — Consulting **C1c write-import readiness**, **not** Booking UI, **not** CRM/public inbound, **not** Marketing |
| Marketing dependency | **Chain only** (must exist so 0014/0015 can follow) |

**Upgrade:**
- `ALTER` existing table `payments`
- ADD column `direction` — enum string values `incoming|outgoing|needs_review`, **`nullable=False`**, **`server_default='incoming'`**
- INDEX `ix_payments_direction`

**Data migration:** none beyond server default for existing/new rows.

**Downgrade:** yes — drop index + drop column.

**Touches production tables?** **Yes** — `payments`.

**Code before/after:**
- Server code today: **no** `direction` in finance models (safe if migration applied alone).
- Local code: finance models/schemas/service + `PaymentDirection` enum **expect** column → deploying that finance code **before** 0013 is unsafe.

**Prod snapshot (read-only 2026-07-14):** `payments` row count = **0** → operational lock/backfill risk **low**.

---

### 2.2 `0014_core_branches_baseline`

| Field | Value |
|-------|--------|
| File | `backend/alembic/versions/20260709_0014_core_branches_baseline.py` |
| Revision | `0014_core_branches_baseline` |
| Down | `0013_c1c_payment_direction` |
| Classification | **Core / Tenancy** (E3a branches baseline; Consulting import / multi-branch groundwork). **Not** Marketing domain. **Not** CRM/public inbound. |

**Upgrade:**
1. CREATE `branches` (FK → `tenants`, unique `(tenant_id, code)`)
2. ADD `tenants.default_branch_id` **nullable** UUID + index
3. FK `tenants.default_branch_id` → `branches.id` ON DELETE SET NULL
4. **Backfill:** for every tenant with `default_branch_id IS NULL`, ensure default branch `code=main` and set `default_branch_id`

**Downgrade:** yes — null out FK, drop FK/index/column, drop `branches`.

**Touches production tables?** **Yes** — `tenants` (add nullable FK) + new `branches` + **data backfill**.

**Code before/after:**
- Server: no `branches` module, no `default_branch_id` on Tenant model — migration alone **safe** for old code.
- Local: `branches/**`, tenants model/service call `BranchService.ensure_default_branch` — deploying that code **without** 0014 can break tenant create / ORM.

**Prod snapshot:** `tenants` count = **3** → backfill tiny.

**Downtime:** typically short DDL + 3-row backfill; still schedule maintenance window.

---

### 2.3 `0015_marketing_cabinet_mvp`

| Field | Value |
|-------|--------|
| File | `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` |
| Revision | `0015_marketing_cabinet_mvp` |
| Down | `0014_core_branches_baseline` |
| Classification | **Marketing Cabinet** only |

**Creates (6):**
1. `marketing_content_topics`
2. `marketing_publication_packs`
3. `marketing_publication_texts`
4. `marketing_media_assets`
5. `marketing_publish_logs`
6. `marketing_lead_attribution`

**Alters existing CRM/public inbound tables?** **No** (FKs only to `tenants` / new marketing tables).

**Env?** **None** for MVP.

**Downgrade:** yes — drop 6 tables + string enums (checkfirst).

**Module gap:** migration does **not** seed `module_definitions` / enable tenant module — still need registry seed + enable gate.

---

## 3. Production impact matrix

| Migration | Large table lock? | Non-null alter? | FK on populated tables? | Backfill? | Downtime? | Break CRM/inbound? |
|-----------|-------------------|-----------------|-------------------------|-----------|-----------|--------------------|
| 0013 | Low now (`payments=0`) | Yes, but with `server_default` | Index only | Default only | Brief DDL | **Unlikely** if old code stays |
| 0014 | Low (`tenants=3`) | No (nullable column) | New FK nullable | **Yes** (3 tenants) | Brief | **Unlikely** if old code stays |
| 0015 | No (new empty tables) | N/A | FK to tenants only | No | Brief | **No** |

---

## 4. Server code compatibility

| Scenario | Verdict |
|----------|---------|
| Keep current server code; apply 0013+0014 only | **Likely safe** — old ORM ignores new columns/tables |
| Deploy local finance/tenants/branches **before** 0013/0014 | **Unsafe** |
| Deploy Marketing code before 0015 | health may register routes; CRUD → DB errors |
| Deploy Marketing FE3 before Marketing BE+0015 | worse broken UX (FE1 already partial live) |
| Does current **server** code already expect 0013/0014? | **No** |
| Does local tree expect 0013/0014? | **Yes** (finance direction + branches/tenants) |

**Ordering rule for any future deploy of local backend slices:**  
**migrations first (or simultaneous package: files on disk → upgrade → restart)**, then serve code that depends on new schema.

---

## 5. Marketing 0015 readiness (narrow)

| Check | Result |
|-------|--------|
| Create-only marketing tables | ✅ |
| No CRM/inbound table rewrite | ✅ |
| Env required | ❌ none |
| Downgrade support | ✅ drop tables |
| Module registry/seed gap | ⚠️ still required after upgrade |
| Chain prerequisite | ⚠️ needs 0014 present |

---

## 6. Untracked / dirty-tree risk

### Untracked (must be committed or explicitly packaged)

| Path | Role |
|------|------|
| `backend/app/modules/marketing/**` | Marketing BE |
| `backend/alembic/versions/20260708_0013_*.py` | 0013 |
| `backend/alembic/versions/20260709_0014_*.py` | 0014 |
| `backend/alembic/versions/20260709_0015_*.py` | 0015 |
| `backend/alembic/versions/20250702_0012_*.py` | 0012 file (history) |
| `backend/app/modules/branches/**` | 0014 ORM companion |
| `platform-console/src/api/marketing.ts` | FE client |
| `platform-console/src/types/marketing.ts` | FE types |
| `platform-console/src/pages/workspace/marketing/**` | FE1–FE3 |

### Modified tracked (careful scope)

| Path | Notes |
|------|--------|
| `backend/app/api/v1/router.py` | marketing include (may mix other local edits) |
| `backend/app/modules/models.py` | marketing imports |
| `backend/app/modules/module_registry/seed.py` | marketing definition |
| `backend/app/modules/finance/*` | **0013-related**, not Marketing |
| `backend/app/modules/tenants/models.py` (+ service) | **0014-related** |
| `backend/app/core/enums.py` | `PaymentDirection` |
| `platform-console` routes/sidebar/css | Marketing FE shell |

### Deploy method

| Method | Verdict |
|--------|---------|
| SCP / rsync from dirty local tree | **Too risky** — easy to ship CRM/booking/consulting extras |
| Git commit → PR → review → deploy from known SHA | **Recommended** |
| Explicit allow-list file package from clean branch | Acceptable if HQ insists (second choice) |

---

## 7. Option comparison

| Option | Summary | Pros | Cons |
|--------|---------|------|------|
| **A Combined** | BE + 0013–0015 + module + console in one gate | One maintenance window | Max blast radius; mixes finance/branches/Marketing; hard rollback story |
| **B Split** | First 0012→0014 (+needed companion code if any), smoke; later Marketing 0015+FE | Isolates Core schema from Marketing product | Two windows; Marketing still waits |
| **C Hold** | No prod Marketing until package clean | Avoids SCP disaster; forces commit | Delay |

**Recommendation:** **C → then B → then Marketing 0015** (not A).

---

## 8. If split — next slices

### Gate A1 (immediate) — Commit / stabilize

- Create clean branch with only:
  - migrations 0013/0014/0015 (+ 0012 file if needed for history)
  - marketing module + router/seed/models wiring
  - branches + minimal tenants/finance bits **only if** included in catch-up plan scope
- Exclude unrelated dirty CRM/booking leftovers
- Local tests for marketing + migration tests

### Gate A2 — Production schema catch-up 0012→0014

- DB backup + backend migration-file backup  
- Copy migration files to server  
- `alembic upgrade 0014_core_branches_baseline` (not through 0015 yet)  
- Restart if needed  
- Smoke: health, CRM, kindergarten, inbound status, alembic=`0014`  
- **Do not** enable marketing yet  

### Gate A3 — Marketing 0015 + BE + module + console

- Separate HQ approval  
- upgrade to 0015 + marketing code + enable + FE3 build  

---

## 9. Rollback reality

| Rev | Downgrade code? | Safe prod downgrade? | Practical fallback |
|-----|-----------------|----------------------|--------------------|
| 0013 | Yes | **Maybe** if `direction` unused and no reliant code; else restore backup | Disable new finance code; DB restore from backup |
| 0014 | Yes | **Risky** after backfill/use — drops all branches | Prefer feature freeze + backup restore |
| 0015 | Yes | **OK** if marketing data disposable | Drop via downgrade **or** disable module + console rollback |

**Do not claim full chain rollback is easy.** Prefer: **console restore + module disable + backend file rollback**; DB restore only if schema catch-up fails badly.

---

## 10. Smoke after schema catch-up only (0014)

| # | Check | Expect |
|---|--------|--------|
| 1 | `GET /api/v1/health` | 200 |
| 2 | Alembic current | `0014_core_branches_baseline` |
| 3 | `branches` exists; each tenant has `default_branch_id` | yes |
| 4 | `payments.direction` exists | yes |
| 5 | flexity-sales CRM | 200 |
| 6 | kindergarten CRM | 200 |
| 7 | Public inbound config unchanged | still current HQ state |
| 8 | Marketing health | still 404 **until** Marketing code (expected) |
| 9 | Booking | no new booking deploy in this slice; confirm no regression on existing APIs |

---

## 11. Required backups (before any future catch-up)

1. **Postgres dump** (schema+data) of production `coreops`  
2. Copy server `alembic/versions/` + record current stamp  
3. Backend allow-list file backup under `/opt/flexity/backups/backend-schema-catchup-<ts>/`  
4. Console dist backup (if console also changes in same window — prefer not for A2)

---

## Approval

| Gate | Status |
|------|--------|
| This audit (Gate A docs) | waiting HQ review |
| Schema catch-up on server | **not approved** |
| Marketing deploy | **not approved** |

---

## Next safe step

1. HQ confirms **Option C** (hold Marketing).  
2. Approve **Gate A1**: commit/stabilize clean package.  
3. Then separate HQ for **Gate A2** schema catch-up 0012→0014.
