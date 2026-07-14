# M6-FE3 — Local smoke report (Marketing workflow)

**Date:** 2026-07-13  
**Slice:** M6-FE3 local smoke  
**Scope:** local only — no deploy / env edit / migrations / backend code / publish  

**Implementation report:** `docs/ai/reports/2026-07-13-marketing-m6-fe3-workflow-polish-report.md`  
**Plan:** `docs/ai/plans/2026-07-13-marketing-m6-fe3-workflow-polish-plan.md`

---

## Smoke status

**PARTIAL / BLOCKED on local DB schema** — not an FE3 code bug.

| Layer | Result |
|-------|--------|
| Local FE (`:5173`) | ✅ up, `/console/` → 200 |
| Local BE (`:8000`) | ✅ up, login OK |
| Marketing module enable on `flexity-sales` | ✅ enabled via API |
| Marketing health | ✅ `{"status":"ok","module":"marketing"}` |
| Live create topic → take → pack… | ❌ blocked: table `marketing_content_topics` missing |
| Backend marketing pytest (sqlite TestClient) | ✅ **52 passed** |
| FE helper tests + build | ✅ ok |
| FE static publish honesty / next-action / nav | ✅ ok |
| FE code bugfix | ❌ none (no FE change) |

---

## Local URLs

| Service | URL |
|---------|-----|
| FE console | http://127.0.0.1:5173/console/ |
| Marketing dashboard (tenant `flexity-sales`) | http://127.0.0.1:5173/console/workspace/flexity-sales/marketing |
| Topics | http://127.0.0.1:5173/console/workspace/flexity-sales/marketing/topics |
| Packs | http://127.0.0.1:5173/console/workspace/flexity-sales/marketing/packs |
| BE API | http://127.0.0.1:8000/api/v1 |

Started for this smoke (local only):

- `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- `npm run dev -- --host 127.0.0.1 --port 5173`

Smoke helper (untracked): `.ai_local/m6_fe3_local_smoke.py`

---

## Live API smoke steps

| # | Step | Result |
|---|------|--------|
| 1 | Login local owner | ✅ 200 |
| 2 | Pick tenant `flexity-sales` | ✅ `7e92404f-…` |
| 3 | Enable module `marketing` | ✅ status `enabled` |
| 4 | `GET /marketing/health` | ✅ ok |
| 5 | Create topic `M6-FE3 Smoke Topic` | ❌ **500** `UndefinedTable: marketing_content_topics` |

**Root cause (infra):** local Postgres alembic head is `0014_core_branches_baseline`.  
Migration `20260709_0015_marketing_cabinet_mvp.py` **not applied**.  
`to_regclass('marketing_content_topics')` → `None`.

HQ forbid migrations in this smoke → **did not run `alembic upgrade`**.

Therefore steps 5–20 of the live browser/API workflow could not be completed against the real local DB.

---

## Contract verification (pytest, sqlite)

Ran without touching production/local postgres schema:

```bash
cd backend
python -m pytest \
  tests/test_marketing_topics.py \
  tests/test_marketing_packs.py \
  tests/test_marketing_texts_media.py \
  tests/test_marketing_preflight_approval.py -q
```

**Result:** `52 passed` in ~76s.

This covers the same BE contract FE3 uses: topics create/patch/take, packs, texts/media PATCH, preflight, approve/reject.

---

## FE verification (no interactive browser automation)

No browser MCP/Playwright in this agent session. Verified:

| Check | Result |
|-------|--------|
| Topics create → approve → take UI code present | ✅ FE3 implementation |
| Next-action helper matrix | ✅ `marketingNextAction.test.ts` ok |
| RU labels / publish disabled constant | ✅ `marketingLabels.test.ts` ok |
| Publish tab has **no** «Опубликовать» button | ✅ static scan |
| «Следующее действие» block in pack detail | ✅ present |
| Sidebar nav `marketing` | ✅ present |
| `npm run build` | ✅ |

---

## Step-by-step HQ checklist (answered)

1. **Smoke status:** PARTIAL — blocked by missing marketing tables on local Postgres (`0014`, need `0015`).  
2. **Local URLs:** see table above.  
3. **Topic create (live DB):** FAIL — table missing.  
4. **Topic approve/take (live DB):** not reached.  
5. **Pack opened (live DB):** not reached.  
6. **Text edit (live DB):** not reached; covered by pytest.  
7. **Media add/edit (live DB):** not reached; covered by pytest.  
8. **Preflight (live DB):** not reached; covered by pytest.  
9. **Approval (live DB):** not reached; covered by pytest.  
10. **Next-action behavior:** helper tests ✅; live UI not exercised.  
11. **Packs list/filter:** live not reached; FE code + client filter logic present.  
12. **Publish disabled:** static ✅ — honesty message, no fake publish button.  
13. **Console/runtime errors:** live BE 500 on create topic (schema); FE console loads 200. No FE runtime bug found.  
14. **Bugs fixed:** none (blocker is migration gap, not FE).  
15. **Build/tests rerun:** helper tests ✅; `npm run build` ✅; marketing pytest 52 ✅.  
16. **Not touched:** backend code, migrations, env files, deploy, publish/export, Margosya, CRM code.  
17. **Risks:** local DB behind marketing MVP migration; module `marketing` was enabled on local `flexity-sales` during smoke; full browser smoke still pending after `0015`.  
18. **Next recommended step:** HQ approve **local-only** `alembic upgrade` to `0015` (or head including marketing), then rerun this smoke (API + browser checklist). After green local smoke → separate deploy gate if desired.

---

## Side effects of this smoke

| Action | Notes |
|--------|--------|
| Started local uvicorn + vite | local processes |
| Enabled `marketing` on tenant `flexity-sales` | local DB module row |
| Attempted INSERT topic | failed; no lasting topic row |
| No publish/export | none |
| No migration | none |

---

## Bugs fixed

**None.** No FE3 code change.

---

## HQ summary

1. **Smoke status:** PARTIAL / blocked on local schema (`0014`, no marketing tables)  
2. **Local URLs:** FE `http://127.0.0.1:5173/console/` · BE `http://127.0.0.1:8000/api/v1` · workspace `/workspace/flexity-sales/marketing`  
3. **Topic create:** live ❌ missing table; pytest contract ✅  
4. **Topic approve/take:** live not reached; pytest ✅  
5. **Pack opened:** live not reached; pytest ✅  
6. **Text edit:** live not reached; pytest ✅  
7. **Media add/edit:** live not reached; pytest ✅  
8. **Preflight:** live not reached; pytest ✅  
9. **Approval:** live not reached; pytest ✅  
10. **Next-action:** helper tests ✅  
11. **Packs list/filter:** live not reached; FE present  
12. **Publish disabled:** static verified ✅  
13. **Console/runtime:** FE 200; BE 500 only on missing table  
14. **Bugs fixed:** none  
15. **Build/tests:** helpers ✅ · build ✅ · marketing pytest 52 ✅  
16. **Not touched:** backend code, migrations, env, deploy, publish, Margosya, CRM  
17. **Risks:** local DB lag; marketing module now enabled locally  
18. **Next:** HQ approve local `alembic upgrade` to marketing `0015`, then rerun full smoke  
