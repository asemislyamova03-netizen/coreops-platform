# Report: Marketing M6 server deploy readiness (audit only)

**Date:** 2026-07-13  
**Project:** Flexity / `coreops-platform`  
**Category:** documentation_only / read-only server audit  
**Plan:** `docs/ai/plans/2026-07-13-marketing-m6-server-deploy-readiness-plan.md`

**HQ constraints honored:** no code, no deploy, no migrations, no env edits, no module enable, no DB writes, no production smoke data.

---

## Status

**READYNESS DOC COMPLETE — NOT DEPLOY-READY WITHOUT GATES**

Server Marketing backend is **absent**. Server DB is at **`0012_booking_e1`**, not 0014. Reaching marketing `0015` requires **0013 + 0014 + 0015**. Console has **FE1 shell only**. `flexity-sales` has **no marketing module**. Env: **none needed** for MVP.

---

## 1. Server backend marketing state

| Check | Result |
|-------|--------|
| Git | `1034ef8` on `main` |
| `app/modules/marketing` | **missing** |
| Router marketing include | **missing** |
| Seed `marketing` definition | **missing** on server |
| OpenAPI marketing paths | **0** |
| `GET /api/v1/marketing/health` | **404** `{"detail":"Not Found"}` |
| `coreops.service` | **active** |

## 2. Server alembic version

| Item | Value |
|------|--------|
| DB `alembic_version` | **`0012_booking_e1`** |
| Files on disk under `alembic/versions/` | `0001`…`0011` only (no 0012–0015 files present) |
| Local head | `0015_marketing_cabinet_mvp` |

**Note:** stamp is ahead of files on disk for 0012; `booking_orders` table exists; booking app module dir absent.

## 3. Server marketing tables

All **absent**:

- `marketing_content_topics`  
- `marketing_publication_packs`  
- `marketing_publication_texts`  
- `marketing_media_assets`  
- `marketing_publish_logs`  
- `marketing_lead_attribution`

Also: `branches` absent; `tenants.default_branch_id` absent; `payments.direction` absent → **0013/0014 not applied**.

## 4. Server console marketing state

| Check | Result |
|-------|--------|
| Active asset | `index-CW_cVLb3.js` |
| URL `/console/workspace/flexity-sales/marketing` | HTTP **200** (SPA) |
| FE1 markers (`Маркетинг`, routes, `M6-FE1`, «только просмотр») | **present** |
| FE3 markers (`Взять в работу`, «Следующее действие», publish honesty) | **absent** |
| FE2 client methods (`approveMarketingPack`, `takeMarketingTopic`, …) | **absent** |

**Verdict:** partial **FE1 shell** already in production console **without** backend — Marketing nav can look present but API will 404/403.

## 5. flexity-sales marketing module state

| Check | Result |
|-------|--------|
| Tenant | exists `90553fe9-22d1-458d-ab84-c7353f2d80e2` |
| `module_definitions` has `marketing` | **no** |
| `tenant_modules` marketing row | **no** |
| Other modules present | parties/crm/documents/finance/… |

## 6. Migration readiness

| Question | Answer |
|----------|--------|
| Revision 0015 | `0015_marketing_cabinet_mvp` ← `0014_core_branches_baseline` |
| Tables | 6 create-only; downgrade drops them |
| Direct 0012→0015? | **No** |
| Required path | **0012 → 0013 → 0014 → 0015** |
| Later than 0015 locally? | **No** (head=0015) |
| Server at 0014? | **No** (at **0012**) |

**Inherited risk:** Marketing deploy currently pulls in **payments.direction (0013)** and **branches baseline (0014)**.

## 7. Backend deploy requirements

Must package/copy (local mostly untracked):

- `backend/app/modules/marketing/**`  
- router + `models.py` + module_registry seed  
- alembic `0013`, `0014`, `0015`  
- branches/tenants pieces needed for 0014 consistency  

No Marketing-specific env keys.

## 8. Frontend deploy requirements

- Full FE1+FE2+FE3 marketing sources  
- Build: `VITE_API_BASE_URL=https://flexity.asia/api/v1 npm run build`  
- Deploy `platform-console/dist` with backup under `/opt/flexity/backups/console-dist-m6-marketing-<ts>/`

## 9. Env requirements

**None** for Marketing MVP. Do not touch public inbound / Margosya / publish tokens.

## 10. Recommended deploy order

1. Gate A — approve readiness + chain strategy  
2. Package/commit Marketing-only scope  
3. Backups (DB + backend + console)  
4. Gate B — backend files → `alembic upgrade head` → restart → health  
5. Gate B2 — seed/enable marketing on `flexity-sales`  
6. Gate C — console dist  
7. Gate D — smoke  
8. Gate E — keep or rollback  

## 11. Smoke plan

Health → marketing health → UI → create `M6 Server Smoke Topic` → approve/take → texts/media → preflight → approve → packs filters → publish disabled → CRM/kindergarten regression → no publish/export.

## 12. Rollback plan

| Layer | Strategy |
|-------|----------|
| Console | restore dist backup |
| Backend | restore file backup + restart |
| Feature | disable marketing module |
| DB 0015 | downgrade to 0014 **if** marketing data disposable |
| DB 0013/0014 | **do not assume safe downgrade** after use; prefer feature-disable |

## 13. Risks

1. **High:** production must traverse 0013+0014 before 0015.  
2. **High:** Marketing code not on server git — packaging required.  
3. **Medium:** FE1 already live without API.  
4. **Medium:** module seed/enable required after BE.  
5. **Low:** empty marketing tables; publish remains disabled.  
6. **High:** dirty local workspace — risk of shipping unrelated files.

## 14. Decision gates

- **A** readiness / chain choice  
- **B** backend + migrations  
- **B2** module enable  
- **C** console  
- **D** smoke  
- **E** keep/rollback  

## 15. What was not touched

Code, deploy, migrations, env, module enable, DB writes, production smoke data, publish/export, Margosya, CRM, public inbound, landing, Booking/Clinic/Trailers.

## 16. Next recommended step

HQ **Gate A**: confirm whether Marketing server deploy may include **0013+0014+0015**, or whether schema catch-up (0013/0014) is a **separate** approved deploy first. Then package Marketing-only artifacts for Gate B.

---

## HQ summary

1. **Status:** readiness docs done; **not** deploy-ready without gates  
2. **Server backend marketing:** absent (health 404)  
3. **Server alembic:** **`0012_booking_e1`**  
4. **Server marketing tables:** none  
5. **Server console marketing:** FE1 shell only (no FE2/FE3)  
6. **flexity-sales marketing module:** not defined / not enabled  
7. **Migration readiness:** need **0013→0014→0015**; cannot jump to 0015  
8. **Backend deploy requirements:** marketing module + router/seed/models + migrations 0013–0015 (+ branches deps)  
9. **Frontend deploy requirements:** full FE1–FE3 build to `dist` with backup  
10. **Env requirements:** none  
11. **Recommended deploy order:** backup → BE+migrate+restart → enable module → console → smoke  
12. **Smoke plan:** documented (Gate D)  
13. **Rollback plan:** console/files easy; DB full chain **not** easy  
14. **Risks:** 0013/0014 on prod; untracked local code; FE1 without BE  
15. **Decision gates:** A→B→B2→C→D→E  
16. **Not touched:** everything production-changing  
17. **Next:** HQ Gate A on migration chain strategy  
