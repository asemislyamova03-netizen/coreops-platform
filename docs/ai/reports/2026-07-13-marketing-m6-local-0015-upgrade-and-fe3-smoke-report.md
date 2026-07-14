# M6 — Local alembic 0015 upgrade + FE3 smoke rerun

**Date:** 2026-07-13  
**Scope:** local Postgres only  
**HQ approval:** local DB migration upgrade + FE3 smoke rerun  

**Prior partial smoke:** `docs/ai/reports/2026-07-13-marketing-m6-fe3-local-smoke-report.md`  
**FE3 implementation:** `docs/ai/reports/2026-07-13-marketing-m6-fe3-workflow-polish-report.md`

---

## Status

**PASS** — local `0014` → `0015_marketing_cabinet_mvp` upgrade succeeded; marketing tables present; full FE3 API workflow smoke green; approve after preflight warning OK; publish not executed.

No production/server. No env changes. No code changes. No new migrations.

---

## 1. Local DB target (before)

| Field | Value |
|-------|--------|
| Host | `127.0.0.1:5432` |
| Database | `coreops` |
| Alembic before | `0014_core_branches_baseline` |
| Marketing tables | none |

## 2. Migration chain

| Field | Value |
|-------|--------|
| File | `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` |
| Revision | `0015_marketing_cabinet_mvp` |
| Revises | `0014_core_branches_baseline` |
| Alembic head | `0015_marketing_cabinet_mvp` (confirmed) |

**Tables created by 0015:**

1. `marketing_content_topics`  
2. `marketing_publication_packs`  
3. `marketing_publication_texts`  
4. `marketing_media_assets`  
5. `marketing_publish_logs`  
6. `marketing_lead_attribution`

(Not the alternate names `marketing_content_packs` / `marketing_content_texts`.)

## 3. Backup / rollback note

| Artifact | Path |
|----------|------|
| Table list + alembic stamp | `.ai_local/backups/coreops_pre_0015_20260713T135929Z.txt` |
| Schema-only `pg_dump` | `.ai_local/backups/coreops_schema_pre_0015_20260713T135930Z.sql` (~131 KB) |

**Rollback (local only, if HQ requests):**  
`alembic downgrade 0014_core_branches_baseline`

## 4. Migration run

```bash
cd backend
python -m alembic upgrade head
```

```text
Running upgrade 0014_core_branches_baseline -> 0015_marketing_cabinet_mvp
```

**Result:** success.

## 5. After upgrade

| Check | Result |
|-------|--------|
| Alembic current | `0015_marketing_cabinet_mvp (head)` |
| All 6 marketing tables | present (`to_regclass` OK) |
| Backend (`:8000`) | still up / docs 200 |
| Frontend (`:5173`) | still up / console 200 |

---

## 6–17. FE3 smoke rerun (local API + FE static)

Tenant: `flexity-sales` (`7e92404f-…`)  
Topic: `M6-FE3 Smoke Topic` (`88930d0c-…`)  
Pack: `6bc61db6-…`

| Step | Result |
|------|--------|
| Marketing health | ✅ 200 `ok` |
| List topics | ✅ 200 |
| Create topic | ✅ 201 |
| Approve topic (`PATCH status=approved`) | ✅ 200 |
| Take topic → pack + 4 empty texts | ✅ 201 |
| Pack detail open | ✅ 200 |
| Next-action after take | ✅ `fill_texts` |
| Text edit (telegram + instagram/threads) | ✅ 200 |
| Media add metadata | ✅ 201 |
| Media edit (`alt_text` / `public_url`) | ✅ 200 |
| Preflight | ✅ 200, response status `warning` (insights empty), pack `preflight_status=passed`, `status=ready_for_approval` |
| Approve pack | ✅ 200 (follow-up call; pack ended `approved`) |
| Next-action after approve | ✅ expected `publish_disabled` |
| Packs list + topic column data | ✅ pack present with topic title |
| Client-side filters (status/approval/preflight) | ✅ pack matches |
| Publish disabled (FE static) | ✅ no «Опубликовать» button; honesty copy present |
| Publish/export side effects | none attempted |

### Local URLs

- http://127.0.0.1:5173/console/workspace/flexity-sales/marketing  
- http://127.0.0.1:5173/console/workspace/flexity-sales/marketing/topics  
- http://127.0.0.1:5173/console/workspace/flexity-sales/marketing/packs/6bc61db6-fc11-484f-9895-c3f1bc8d15fc  
- http://127.0.0.1:8000/api/v1  

### Note on preflight `warning`

API preflight body can return `status: "warning"` while pack `preflight_status` becomes `passed`. Approve is gated on pack `preflight_status === "passed"` (FE behavior). Smoke first pass skipped approve due to checking response `status == "passed"`; immediate retry approve succeeded — **not an FE bug**.

Interactive browser automation was not available; smoke used live local API matching FE client calls + FE static checks for publish/next-action/nav. FE console reachable (200).

CRM soft check: `GET /workflows/work-items` → 404 on this route shape (unchanged; not treated as Marketing failure).

---

## 18. Tests / build

| Check | Result |
|-------|--------|
| `marketingLabels.test.ts` | ✅ ok |
| `marketingNextAction.test.ts` | ✅ ok |
| `pytest tests/test_marketing_preflight_approval.py` | ✅ 11 passed |
| `npm run build` | ✅ |

(No code changes; build re-run for confirmation.)

## 19. Bugs fixed

**None.**

## 20. What was not touched

- Production / server  
- Deploy  
- `.env`  
- Application code  
- New migrations  
- Publish/export  
- Margosya  
- CRM feature code  

## 21. Risks

1. Local DB only — production still needs separate HQ gate for `0015`.  
2. Smoke created real local topic/pack/media rows on `flexity-sales`.  
3. Preflight `warning` vs pack `passed` can confuse scripts/operators if they look only at response `status`.  
4. Full click-path browser smoke still manual (agent had no browser MCP).

## 22. Next recommended step

1. Optional: manual browser click-through on the URLs above (Asem daily path).  
2. Separate HQ: Marketing **deploy gate** (BE migration + FE console) when ready.  
3. Parallel later: M6-BE6 publish/export planning — still fail-closed.

---

## HQ summary

1. **Status:** PASS  
2. **Local DB before version:** `0014_core_branches_baseline`  
3. **Local DB after version:** `0015_marketing_cabinet_mvp` (head)  
4. **Migration run:** `alembic upgrade head` ✅  
5. **Marketing tables verified:** 6/6 present  
6. **Backend health:** ✅ up  
7. **Marketing health/list:** ✅  
8. **Topic create:** ✅  
9. **Topic approve/take:** ✅  
10. **Pack opened:** ✅  
11. **Text edit:** ✅  
12. **Media add/edit:** ✅  
13. **Preflight:** ✅ (`warning` body / pack `passed`)  
14. **Approval:** ✅  
15. **Next-action:** ✅ take→fill_texts; after approve→publish_disabled  
16. **Packs list/filter:** ✅  
17. **Publish disabled:** ✅  
18. **Tests/build:** helpers ✅ · pytest 11 ✅ · build ✅  
19. **Bugs fixed:** none  
20. **Not touched:** prod, deploy, env, code, publish, Margosya, CRM  
21. **Risks:** local-only schema; smoke data left; warning vs passed nuance  
22. **Next:** optional manual browser smoke → separate deploy HQ  
