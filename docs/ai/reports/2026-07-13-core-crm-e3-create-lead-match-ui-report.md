# Report: Core CRM E3 — CreateWorkItemModal contact match UI

**Дата:** 2026-07-13  
**Проект:** Flexity / `coreops-platform`  
**Тип:** Frontend local slice  
**Статус:** ✅ **IMPLEMENTED (local)** — deploy не выполнялся  
**Prerequisite:** E2 Match API (`docs/ai/reports/2026-07-13-core-crm-e2-party-match-api-report.md`)

---

## Goal

В CreateWorkItemModal при вводе контакта показывать совпадения из `POST /parties/match` и дать выбрать существующий Party или продолжить создание нового. Без auto-link / merge.

---

## Solution

### API client

`matchParties(payload)` → `POST /api/v1/parties/match` in `platform-console/src/api/parties.ts`

### Trigger

- Only in mode **«Новый контакт»**
- Debounce **500ms**
- Call only if:
  - phone digits ≥ 10, or
  - email contains `@` (len ≥ 5), or
  - name length ≥ 3
- Payload fields used now: **name, phone, email**
- Telegram / WhatsApp: **не в форме** — documented in UI hint; no big form redesign in E3

### Match warning UI

Panel «Похожий контакт найден» (exact) / «Возможно, это тот же человек» (weak only):

- display name
- match type label
- matched_on (телефон / email / …)
- recent work item title if present
- actions:
  - **Использовать этот контакт**
  - **Создать нового**

Top 3 matches (exact first).

### Use existing contact

1. Switch to `partyLinkMode = existing`
2. Set `partyId` to matched `party_id`
3. Keep title / source / description
4. Submit creates WorkItem with `primary_party_id` = existing Party (no `createParty`)
5. If party not in filtered select options — inject option with match name

### Continue as new

- Dismiss panel for current fingerprint
- Allow create new Party
- If dismissed exact match: subtle hint «Контакт с такими данными уже есть, но вы можете создать нового.»
- **No hard block**

### Error handling

Match API failure → non-blocking info Alert; lead create still works.

### Reset

Clears on: switch to existing mode, clear/change payload fingerprint, dismiss, modal close (unmount).

---

## Files changed

| File | Change |
|------|--------|
| `platform-console/src/api/parties.ts` | `matchParties` |
| `platform-console/src/types/party.ts` | Match request/response types |
| `platform-console/src/workspace/partyMatchUiHelpers.ts` | **New** — payload/trigger/labels |
| `platform-console/src/workspace/partyMatchUiHelpers.test.ts` | **New** |
| `platform-console/src/components/workspace/CreateWorkItemModal.tsx` | Match UI + use/dismiss flow |
| `platform-console/src/index.css` | Match panel styles |

---

## Tests / build

| Check | Result |
|-------|--------|
| `npm run build` | ✅ PASS |
| `partyMatchUiHelpers.test.ts` | ✅ passed |
| `crmPipelineBoardHelpers.test.ts` | (run with suite) |

---

## Not touched

- Backend / E2 code
- Migrations
- Deploy
- Public inbound
- Auto-merge / auto-link
- Telegram/WhatsApp form fields (documented gap)

---

## Risks

| Risk | Mitigation |
|------|------------|
| Exact match dismissed → duplicate Party | Soft warning after dismiss |
| Matched party hidden by role filter | Inject option into select |
| Match API down | Non-blocking; create continues |

---

## Next recommended step

1. Local smoke CreateWorkItemModal against local/staging API with E2 deployed  
2. Deploy order: **backend E2 first**, then console E3  
3. Later: telegram/whatsapp fields in create form (optional)

---

## HQ summary

| # | Item | Value |
|---|------|-------|
| 1 | **Status** | ✅ Implemented locally |
| 2 | **Files changed** | 6 files |
| 3 | **API client** | `matchParties()` → POST `/parties/match` |
| 4 | **Trigger** | debounce 500ms; phone≥10 digits / email@ / name≥3 |
| 5 | **Warning UI** | panel with matches + actions |
| 6 | **Exact** | strong panel; recommend use existing |
| 7 | **Weak** | softer «Возможно, это тот же человек» |
| 8 | **Use existing** | switch to existing mode + set partyId |
| 9 | **Continue new** | dismiss; soft hint if exact |
| 10 | **Social fields** | not in form yet (name/phone/email only) |
| 11 | **Errors** | non-blocking |
| 12 | **Build/tests** | build PASS; helper tests PASS |
| 13 | **Backend touched** | No |
| 14 | **Deploy needed** | Console after E2 backend deploy |
| 15 | **Not touched** | backend, inbound, migrations |
| 16 | **Risks** | Low–medium duplicates if user dismisses exact |
| 17 | **Next** | Deploy E2 backend → deploy E3 console; smoke |
