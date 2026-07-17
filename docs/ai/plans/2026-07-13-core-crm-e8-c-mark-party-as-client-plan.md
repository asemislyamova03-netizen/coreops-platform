# Plan: Core CRM E8-C — Mark Party as Client

**Дата:** 2026-07-13  
**Проект:** Flexity / `coreops-platform`  
**Тип:** documentation / audit planning only  
**Статус:** ⏸ **waiting for HQ approval** (код / deploy / env / миграции — не трогать)

**CRM:** https://flexity.asia/console/workspace/flexity-sales/crm  
**Related:** `docs/ai/plans/2026-07-13-core-crm-e8-accepted-lead-to-client-tenant-plan.md`  
**SOP:** `docs/FLEXITY_LEAD_PROCESSING_WORKFLOW.md`

---

## Goal

Спланировать самый маленький безопасный slice после `accepted`:

**«Сделать клиентом»** — пометка Party как клиента **без** создания tenant, без auto-move stage, без billing.

---

## Classification

| Field | Value |
|-------|-------|
| **Project** | Flexity |
| **Category** | `documentation_only` now → later `universal_module` CRM UI |
| **Risk** | low (если frontend-only) |
| **Forbidden now** | code, backend, deploy, env, migrations, tenant auto, convert button |

---

## 1. Audit — Party model

| Item | Fact |
|------|------|
| Поле `party_role` | ❌ не колонка БД |
| Хранение | `Party.metadata_json["party_role"]` (JSON) |
| Тип | свободная `str` (API), без SQL enum |
| Миграция для новых значений | **не нужна** |

### Допустимые / используемые значения

Нет жёсткого backend enum. По продукту/шаблонам:

| Value | Где встречается | Label (sales) |
|-------|-----------------|---------------|
| `lead` | public inbound create; sales labels | «Лид» |
| `client` | sales labels; finance/docs tests | «Клиент» |
| `contact` | sales labels | «Контакт» |
| `guardian` / `enrollee` / `staff` | kindergarten | — |

**Source of labels (sales):** `FLEXITY_SALES_BASIC.labels_config.party_roles` в `seed.py`.

**Public inbound:** при создании Party пишет `metadata_json.party_role = "lead"`.

**Frontend read:** `getPartyRole(party)` → `metadata_json.party_role`.

**Рекомендация E8-C:** использовать существующее значение **`client`**. Не invent `customer` / `prospect`.

---

## 2. Audit — Parties API

| Capability | Status |
|------------|--------|
| `PATCH /api/v1/parties/{id}` | ✅ |
| Body `party_role` | ✅ `PartyUpdate.party_role: str \| None` |
| Validation enum | ❌ нет — любая строка до разумной длины схемы |
| Module gate | ✅ `require_module("parties")` |
| Side effects | обновляет `metadata_json`; **не** создаёт tenant/subscription/project; **не** двигает WorkItem stage |
| Response | `party_role` в ответе **не** top-level; смотреть `metadata_json.party_role` |
| Filter list | `GET /parties?party_role=client` ✅ |

**Вывод:** backend **уже поддерживает** смену роли. Для E8-C отдельный backend slice **не нужен**.

---

## 3. Audit — Clients UI

| Item | Path / behavior |
|------|-----------------|
| List | `/workspace/:tenantSlug/clients` → `ClientsPage.tsx` |
| Detail | `/workspace/:tenantSlug/clients/:partyId` → `ClientDetailPage.tsx` |
| Data load | `listParties({ limit: 200 })` **без** фильтра `party_role=client` |
| Visibility | `isPartyVisibleInClientsList` — показывает `lead`, `client`, `contact`, `guardian` + keys из labels |
| Role display | Client detail: label роли в subtitle; list **не** показывает колонку role |

### Важно для HQ

Сейчас **лиды уже видны** в разделе «Клиенты».

«Сделать клиентом» **не** «впускает» Party в список впервые — Party с `lead` уже там.

**Ценность E8-C:**
- явная семантика: контакт = клиент (после согласия);
- badge/роль на detail и в CRM;
- возможность позже фильтровать `party_role=client` / отчёты;
- мост к будущему tenant convert без путаницы lead vs client.

Опциональный follow-up (не E8-C): фильтр списка «только клиенты» — отдельный product decision.

---

## 4. Audit — CRM / LeadDetailModal

| Item | Status |
|------|--------|
| Linked Party | ✅ `primary_party_id` → `getParty` |
| Edit contact | ✅ name/phone/email через `updateParty` в save |
| Show `party_role` | ❌ сейчас не показывается |
| Update только role | ❌ отдельного action нет (save не шлёт `party_role`) |
| Link to client card | ✅ «Открыть карточку…» |
| Stage help (E8-B) | ✅ для `accepted` / `converted_to_tenant` |
| Safe action place | после секции контакта / рядом с link на clients; или блок «Клиент» под стадией при `accepted` |

`updateParty` уже импортирован — новый API client не нужен.

---

## 5. Audit — Existing tests

| Area | Coverage |
|------|----------|
| Backend create + `metadata_json.party_role` | ✅ `test_parties.py` |
| Backend list `?party_role=` | ✅ |
| Backend dedicated PATCH `party_role` only | ⚠️ нет узкого теста (create/update path в service есть) |
| Frontend `isPartyVisibleInClientsList` | ✅ `labelHelpers.test.ts` (lead visible) |
| Frontend mark-as-client helper/UI | ❌ нет |
| LeadDetailModal contact save | есть в продукте; отдельного unit-теста modal нет |

---

## 6. Product recommendation

### Recommended role value

**`client`** — уже в sales `labels_config`, уже в коде/тестах, без миграции.

### Backend changes needed?

**No** — для минимального E8-C.

### Recommended E8-C slice (frontend-only)

**Scope:**

1. Helper (например `partyClientRoleHelpers.ts`):
   - `isPartyClient(role)` → `role === "client"`
   - `shouldShowMarkAsClientAction({ hasParty, stageCode, role })`
2. В `LeadDetailModal`, если есть linked Party:
   - блок **«Клиент»**
   - help: *«Это только пометка контакта как клиента. Tenant создаётся отдельно, если нужен рабочий контур.»*
   - если role ≠ `client` и stage = `accepted` (primary): кнопка **«Сделать клиентом»**
   - если уже `client`: badge **«Клиент»** (+ optional link to clients detail)
3. Click → `updateParty(id, { party_role: "client" })` → invalidate party/clients queries → success/error в modal
4. **Не** трогать WorkItem stage / save form / close/reopen / tenant APIs

**Visibility (рекомендация):**

| Condition | UI |
|-----------|-----|
| Нет Party | блок скрыт |
| Stage `accepted`, role ≠ client | кнопка + help |
| Stage `accepted`, role = client | badge only |
| Другая стадия, role ≠ client | optional: только readonly «Роль: Лид» **без** кнопки (меньше шума) **или** кнопка тоже (HQ) |
| Другая стадия, role = client | badge |

**Draft HQ default:** кнопка **только на `accepted`**; на других стадиях — показать текущую роль readonly, если Party есть.

---

## 7. UX rules (зафиксировать)

1. «Сделать клиентом» **не** создаёт tenant.  
2. **Не** двигает стадию (остаётся `accepted` или любая текущая).  
3. **Не** создаёт subscription / project / documents.  
4. Без linked Party — нет action.  
5. Уже `client` — только статус, без повторного PATCH.  
6. Help text обязателен (см. выше).  
7. Confirm dialog — optional (low risk; можно без confirm для MVP).

---

## 8. Tests plan (на реализацию)

1. Helper: non-client → needs action; client → no action.  
2. Helper: no party → hide.  
3. Helper: accepted + lead → show button.  
4. Helper: negotiation + lead → hide button (если выбран strict mode).  
5. Click payload = `{ party_role: "client" }` (unit/mock).  
6. Stage / WorkItem не меняются.  
7. Tenant API не вызывается.  
8. Error state (ApiError).  
9. `npm run build`.

Optional backend (не блокер): один тест `PATCH party_role lead→client`.

---

## 9. Out of scope

- automatic tenant creation  
- `converted_tenant_id`  
- convert button «Создать клиентский контур»  
- billing / subscription  
- Project / Onboarding entities  
- document generation  
- client portal / AI employees  
- merge duplicates  
- смена seed stage names  
- фильтр Clients list «только client» (отдельный decision)  
- Marketing / Margosya / Booking / Clinic / Trailers / currency  

---

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Ожидание «появится в Клиентах» | Документировать: уже виден; меняется роль/badge |
| Случайный mark до оплаты | Кнопка только на `accepted` + help |
| Kindergarten confusion | Action только в sales CRM modal; role `client` не трогает guardian flow |
| PATCH без confirm | Low; можно добавить confirm |
| `party_role` free string typos | Hardcode `"client"` в helper, не user input |

---

## 11. Implementation file sketch (после approval)

| File | Change |
|------|--------|
| `platform-console/src/workspace/partyClientRoleHelpers.ts` | new + tests |
| `platform-console/src/components/workspace/LeadDetailModal.tsx` | block + mutation |
| `platform-console/src/index.css` | compact styles |
| `docs/FLEXITY_LEAD_PROCESSING_WORKFLOW.md` | 1 абзац в «После accepted» |
| report | после реализации |

**Не трогать:** backend, seed, tenants, inbound, workflows move-stage.

---

## 12. Next recommended step

**HQ approve E8-C frontend-only** с правилами:

1. role value = `client`  
2. кнопка только на `accepted`  
3. no stage move / no tenant  

Затем implement local → tests/build → console deploy (отдельный HQ).

---

## Approval

**Status:** waiting for HQ approval  
**Code / deploy:** not requested
