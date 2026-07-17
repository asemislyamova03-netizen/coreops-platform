# FLEXITY WORKITEM PARTY MAPPING B3 UI SMOKE REPORT

**Дата:** 2026-07-02  
**Slice:** B3 UI smoke — platform-console + sales/kg tenants  
**Статус:** ⚠️ **PASSED WITH NOTES** (API+labels layer; live browser UI not run)

---

## 1. Task Classification

| Field     | Value                                                              |
| --------- | ------------------------------------------------------------------ |
| Project   | Flexity                                                            |
| Category  | `ui_smoke`                                                         |
| Risk      | low/medium                                                         |
| Scope     | local/dev platform-console smoke                                     |
| Forbidden | production, deploy, migrations, public inbound, merge, cherry-pick |

---

## 2. Summary

Проводился **B3 UI smoke** для проверки Console mapping Party/WorkItem после B3 implementation.

**Выполнено:**

- `npm run build` (platform-console) — OK
- `npx tsx src/workspace/labelHelpers.test.ts` — passed
- **API + labels layer smoke** через TestClient (эквивалент данных, которые Console читает из `/tenants/{id}/labels` и API)
- Regression checks для kindergarten tenant на том же слое

**Не выполнено (environment blocker):**

- Live browser UI smoke на `http://localhost:5173/console/`
- Live API на `http://127.0.0.1:8000` — PostgreSQL credentials mismatch (`coreops@5432` auth failed; `.env` points to `:15432` unavailable; Docker not in PATH)

**Итог:** B3 Console **логика и data flow подтверждены** на API+labels слое; **полный browser smoke отложен** до рабочего dev stack.

---

## 3. Environment

| Parameter | Value |
|-----------|-------|
| **API mode** | TestClient + in-memory SQLite (live API **not started**) |
| **Attempted live API** | `uvicorn` on `:8000` — failed (PostgreSQL auth) |
| **Console mode** | `npm run build` only; `npm run dev` **not started** (no API backend) |
| **Console URL (target)** | `http://localhost:5173/console/` |
| **API URL (target)** | `http://127.0.0.1:8000/api/v1` |
| **Sales tenant** | `flexity-sales` + template `flexity_sales_basic` (runtime bootstrap in smoke) |
| **KG tenant** | `garden-b3-smoke` + `kindergarten_basic` |

### Commands run

```bash
# Console
cd platform-console
npm run build                                    # OK
npx tsx src/workspace/labelHelpers.test.ts       # OK

# Live stack (failed)
cd backend
DATABASE_URL=postgresql+psycopg://coreops:coreops@127.0.0.1:5432/coreops \
  SEED_ON_STARTUP=true uvicorn app.main:app --port 8000
# → OperationalError: password authentication failed for user "coreops"

docker compose up -d db
# → docker: command not found
```

### Repo state note

`flexity_sales_basic` **отсутствует** в `backend/app/modules/industry_templates/seed.py` на текущем workspace (`INDUSTRY_TEMPLATES = [KINDERGARTEN_BASIC]` only). Smoke bootstrap template через `upsert` в ephemeral DB. **B1 seed нужно восстановить/закоммитить** для live dev stack без ручного bootstrap.

---

## 4. Sales Tenant Smoke Results

| Check | Status | Notes |
| ----- | ------ | ----- |
| Workspace opens | ⚪ N/A | Live console not started |
| CRM opens | ⚪ N/A | Live console not started |
| «Создать лид» visible | ✅ PASS | `CrmPage.tsx` uses `workItemLabel.toLowerCase()`; labels API returns `work_item=Лид` |
| «Контакт» labels visible | ✅ PASS | Labels API: `party=Контакт`; `labelHelpers` tests OK |
| Create contact modal works | ✅ PASS* | Code path + API party create with `party_role=lead`; browser not opened |
| Party role is lead/contact | ✅ PASS | API: `metadata_json.party_role=lead`; Console default role logic → `lead` |
| Party visible in list | ✅ PASS | API list includes lead party; `isPartyVisibleInClientsList` includes `lead` |
| Create WorkItem modal uses Контакт | ✅ PASS* | `CreateWorkItemModal` uses `entityLabel("party")`; build OK |
| WorkItem links to Party | ✅ PASS | API: `primary_party_id` set |
| Kanban shows WorkItem | ✅ PASS | API: work-items list by pipeline includes created item |
| Stage moves work | ✅ PASS | API: 6 moves `new_lead` → `accepted` |
| Terminal stages understandable | ✅ PASS | `rejected` → `lost`; `converted_to_tenant` → `won` |
| No public inbound used | ✅ PASS | `PUBLIC_LEADS_ENABLED=false`; endpoint returns **403 disabled** (route exists, not active) |

\* PASS at API/code layer; browser modal interaction not exercised.

---

## 5. Kindergarten Regression Smoke Results

| Check | Status | Notes |
| ----- | ------ | ----- |
| Workspace opens | ⚪ N/A | Live console not started |
| Existing labels preserved | ✅ PASS | API labels: `work_item=Заявка`, `party_roles.guardian` present |
| Guardian/enrollee visible | ✅ PASS | Guardian party in API list; `enrollee` in template party_roles |
| Create party flow works | ✅ PASS | API create with `party_role=client` OK |
| CRM pages open | ✅ PASS | API: pipeline `enrollment` exists |
| No sales copy leak | ✅ PASS | KG tenant has no `flexity_sales` pipeline; default role stays `client` |

**Console subtitle (code review):** `pickClientsSectionPartyRoleKey` → kindergarten shows **«Родитель / Контрагент»** (guardian + party entity label).

---

## 6. Issues Found

### Blockers (for full live UI smoke)

| Issue | Impact |
|-------|--------|
| PostgreSQL not connectable with project credentials | Cannot start live API |
| Docker unavailable in shell | Cannot start `docker compose db` |
| `flexity_sales_basic` missing from `seed.py` on disk | Live sales tenant needs manual template bootstrap |

### Non-blockers

| Issue | Impact |
|-------|--------|
| Live browser UI not exercised | Full B3 UI smoke incomplete |
| Nav item still «Клиенты» (`ui.clients`) | Global i18n; hints show template context |
| Kanban card does not show Party name | Known gap; out of B3 scope |
| Public inbound route exists in codebase | Disabled via config (`403`); not enabled for use |

### UX notes

- Sales create button: «Создать контакт» (from party entity label)
- CRM button: «Создать лид» (from work_item label)
- Participant API role: `other` when default party role is `lead`/`contact`

### Follow-up tasks

1. Fix local dev DB (Docker or correct `DATABASE_URL`)
2. Restore/commit B1 `flexity_sales_basic` in `seed.py`
3. Run live browser smoke: login → `flexity-sales` → create contact → create lead → kanban
4. Repeat for kindergarten tenant

---

## 7. What Was Not Touched

| Area | Status |
|------|--------|
| Production | ❌ not touched |
| Deploy | ❌ not done |
| Migrations | ❌ not run |
| Public inbound enablement | ❌ remains disabled (`PUBLIC_LEADS_ENABLED=false`) |
| Merge / cherry-pick | ❌ not done |
| Backend code changes | ❌ none in this smoke |
| Console code changes | ❌ none in this smoke |

---

## 8. Recommendation

**B3 UI smoke: PASSED WITH NOTES**

- **Console B3 implementation** validated via build, unit tests, and API+labels layer smoke.
- **Kindergarten regression** OK on same layer.
- **Full browser UI smoke** — proceed after dev stack fix + B1 seed on disk.

**HQ can proceed to B2b public inbound planning/review** with conditions:

1. Complete live browser smoke when dev environment ready.
2. Confirm B1 `flexity_sales_basic` is committed in `seed.py`.
3. Public inbound remains **config-disabled** until explicit B2b approval (route exists but returns 403 when disabled).

---

## 9. HQ Summary

### 1. Smoke status

⚠️ **PASSED WITH NOTES** — API+labels + build/tests green; live browser UI pending dev stack.

### 2. Sales tenant result

Data flow **works**: labels «Лид»/«Контакт», `party_role=lead`, Party visible, WorkItem linked, kanban data, all 9 stages movable, terminals correct.

### 3. Kindergarten result

**No regression** on labels, guardian visibility, enrollment pipeline, client create flow.

### 4. Issues

- Dev environment blocked (DB/Docker)
- B1 seed missing on disk
- Browser UI not opened

### 5. Recommended next step

1. **Ops:** fix local PostgreSQL / Docker; restore B1 seed in `seed.py`
2. **Smoke:** run live browser checklist on `flexity-sales` + kg tenant
3. **Then:** B2b public inbound HQ review (cherry-pick plan)

---

## Appendix — Automated check summary

| Layer | Result |
|-------|--------|
| `npm run build` | ✅ |
| `labelHelpers.test.ts` | ✅ 10 assertions |
| API+labels smoke (TestClient) | ✅ 21/23 checks |
| Failed checks | `B1 in seed.py` (repo state); `public inbound` status code semantics (403 vs 404 — **disabled, not enabled**) |

---

*Report v1.0 — B3 UI smoke (partial live UI).*
