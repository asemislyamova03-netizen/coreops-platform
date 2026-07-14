# Report: Production schema catch-up 0012→0015 audit (Gate A)

**Date:** 2026-07-14  
**Project:** Flexity / `coreops-platform`  
**Category:** documentation_only / read-only  
**Plan:** `docs/ai/plans/2026-07-13-production-schema-catchup-0012-to-0015-audit.md`

**Constraints honored:** no code, no migrations run, no deploy, no env, no DB writes, no module enable, no production smoke data.

---

## Status

**AUDIT COMPLETE.**  

**Recommended option: C** (hold Marketing deploy until code is committed/stabilized), then proceed with **B** (schema catch-up `0012→0014` separate from Marketing `0015`).

**Not recommended: A** (combined Marketing + 0013–0015 in one shot).

---

## 1. Migration chain

```text
Server now: 0012_booking_e1
         → 0013_c1c_payment_direction   (ALTER payments + direction)
         → 0014_core_branches_baseline  (CREATE branches + tenants.default_branch_id + backfill)
         → 0015_marketing_cabinet_mvp   (CREATE 6 marketing tables)  ← local head
```

Direct jump to 0015: **not allowed / not possible** on this graph.

---

## 2. 0013 summary

| Item | Detail |
|------|--------|
| Class | **Core/Finance** (Consulting C1c import readiness) |
| Marketing? | Chain dependency only |
| Booking/CRM/inbound? | No domain change |
| Change | ADD `payments.direction` NOT NULL + server_default `incoming` + index |
| Downgrade | Yes (drop column) |
| Prod note | `payments` count = **0** → low operational risk |

---

## 3. 0014 summary

| Item | Detail |
|------|--------|
| Class | **Core/Tenancy** (E3a branches baseline) |
| Marketing? | Chain dependency only |
| Change | CREATE `branches`; ADD nullable `tenants.default_branch_id` + FK; **backfill** default `main` per tenant |
| Downgrade | Yes (code exists) but **prod-risky** after use |
| Prod note | `tenants` count = **3** → small backfill |

---

## 4. 0015 summary

| Item | Detail |
|------|--------|
| Class | **Marketing only** |
| Change | Create 6 marketing tables; no CRM/inbound alters |
| Env | None |
| Downgrade | Yes (drop 6 tables) |
| Gaps | module definition/seed + enable still required after |

---

## 5. Production impact

| Rev | Impact |
|-----|--------|
| 0013 | Touches live `payments`; low lock risk now (empty table); wrong-order finance code deploy is the real danger |
| 0014 | Touches `tenants` + new `branches` + backfill; small N; CRM/inbound unlikely broken if old code kept |
| 0015 | Additive marketing schema only |

CRM / public inbound: **no intentional schema rewrite** in these three files. Residual risk is process (wrong package, long lock, bad deploy order), not Marketing SQL itself.

---

## 6. Current server code compatibility

| Fact | Value |
|------|--------|
| Server finance has `direction`? | **No** |
| Server tenants has `default_branch_id` / branches module? | **No** |
| Server marketing module? | **No** |
| Apply 0013+0014 with **current** server code | **Likely safe** |
| Deploy **local** finance/tenants/branches **before** migrations | **Unsafe** |
| Local tree already expects 0013/0014 | **Yes** |

---

## 7. Marketing code tracking risk

| Bucket | Paths |
|--------|--------|
| Untracked | entire `marketing/` module; `branches/`; alembic `0013`/`0014`/`0015` (+ `0012` file); FE marketing api/types/pages |
| Modified tracked | `router.py`, `models.py`, `module_registry/seed.py`, finance/*, tenants/*, console routes/sidebar/css, enums |
| Tracked marketing files | **0** (`git ls-files marketing` empty) |

**SCP from dirty local tree: not acceptable as primary method.**  
Safer: commit → review → deploy known SHA / allow-listed package.

---

## 8. Rollback reality

| Rev | Downgrade script | Safe? | Fallback |
|-----|------------------|-------|----------|
| 0013 | Yes | Conditional | backup restore; don’t ship direction-aware finance without path |
| 0014 | Yes | **Not easy** after use | backup restore preferred |
| 0015 | Yes | OK if data disposable | module disable + console rollback; or downgrade |

Full chain rollback **not** treated as easy.

---

## 9. Recommended option

**C** — Hold Marketing production deploy.

Then:

1. **Gate A1** — commit/stabilize clean package  
2. **Gate A2 / Option B** — schema catch-up `0012→0014` alone + smoke  
3. **Later** — Marketing `0015` + BE + module enable + FE2/FE3 console  

---

## 10. If split — recommended next slice

**Gate A1: commit/stabilize Marketing + migration chain artifacts**

Not yet run production `alembic upgrade`.  
Not yet enable marketing module.

Optional immediate alternate if HQ prefers risk-first:  
**Gate A1 = production schema catch-up readiness for 0012→0014 only** (still needs migration files on a clean package first).

---

## 11. Required backups (before future catch-up)

- Full DB dump of production `coreops`  
- Record alembic stamp + copy `alembic/versions`  
- Backend file backup under `/opt/flexity/backups/…`  
- Console backup only if console changes in same window (prefer **no** console change in A2)

---

## 12. Smoke after catch-up (0014 only)

- health 200  
- alembic = `0014_core_branches_baseline`  
- `branches` + `payments.direction` exist  
- flexity-sales CRM 200  
- kindergarten CRM 200  
- public inbound config unchanged  
- marketing health still 404 (expected until Marketing code)  

---

## 13. What was not touched

Code, migrations execution, deploy, env, DB writes, module enable, production smoke data, publish/export, Margosya, CRM/inbound changes, Booking/Clinic/Trailers implementation.

---

## 14. Risks

1. Untracked Marketing + mixed dirty tree → accidental wrong ship  
2. Combined Option A hides 0013/0014 failure under Marketing narrative  
3. Local finance/tenants expect schema server doesn’t have yet  
4. Server alembic **files** lag stamp (0012 file missing on disk)  
5. Downgrade of 0014 not a comfort blanket  

---

## 15. Next recommended step

HQ confirms **Option C**.  
Approve **Gate A1: commit/stabilize** clean branch/package for migrations + Marketing (scoped).  
Then separate approval for **schema catch-up 0012→0014**.

---

## HQ summary

1. **Status:** audit complete  
2. **Migration chain:** `0012 → 0013 → 0014 → 0015` (no direct jump)  
3. **0013:** finance `payments.direction` (Consulting C1c); not Marketing  
4. **0014:** core `branches` + `tenants.default_branch_id` + backfill; not Marketing  
5. **0015:** create-only 6 marketing tables; no CRM/inbound rewrite; no env  
6. **Production impact:** low row counts now (`payments=0`, `tenants=3`); risk is process/order/package  
7. **Server code compatibility:** old code + 0013/0014 OK; local dependent code without migrate = unsafe  
8. **Tracking risk:** marketing **0 tracked files**; SCP dirty tree **too risky**  
9. **Rollback reality:** 0015 OK-ish; 0013 conditional; 0014 **not easy**; prefer backup/feature disable  
10. **Recommended option:** **C** (then B)  
11. **Next slice:** Gate A1 commit/stabilize  
12. **Backups:** full DB dump + alembic/files backup before any upgrade  
13. **Smoke after catch-up:** health/CRM/kindergarten/inbound + alembic=0014  
14. **Not touched:** all production-changing actions  
15. **Risks:** dirty tree, combined deploy blast radius, file/stamp skew  
16. **Next:** HQ confirm C → Gate A1 stabilize package  
