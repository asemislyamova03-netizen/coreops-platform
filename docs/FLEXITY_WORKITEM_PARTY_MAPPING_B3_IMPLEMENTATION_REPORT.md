# FLEXITY WORKITEM PARTY MAPPING B3 IMPLEMENTATION REPORT

**Дата:** 2026-07-02  
**Slice:** B3 — Console Party/WorkItem sales mapping  
**Статус:** ✅ implementation complete (platform-console)

---

## 1. Task Classification

| Field     | Value                                                                       |
| --------- | --------------------------------------------------------------------------- |
| Project   | Flexity                                                                     |
| Category  | `console_ui_mapping`                                                        |
| Risk      | low/medium                                                                  |
| Scope     | platform-console Party/WorkItem labels and role mapping                     |
| Forbidden | backend, migrations, public inbound, deploy, production, merge, cherry-pick |

---

## 2. Summary

B3 выравнивает **manual sales flow** в Platform Console без новой CRM:

- Party создаётся с **динамическим `party_role`** из template `labels_config.party_roles` (`lead` для sales);
- UI copy использует template labels («Контакт», «Лид») вместо hardcoded «Клиент»;
- `lead` / `contact` и роли из template **видны** на странице Clients;
- WorkItem modal использует template-aware party label; participant API role = `other` для lead/contact;
- **Без hardcode** slug `flexity-sales` — всё label-driven;
- Kindergarten совместимость сохранена через `guardian` в section subtitle.

---

## 3. Files Changed

| File | Change |
|------|--------|
| `platform-console/src/workspace/labelHelpers.ts` | Helpers: `pickDefaultPartyRole`, visibility, participant role |
| `platform-console/src/workspace/WorkspaceLabelsContext.tsx` | Dynamic `clientsSectionTitle`, `defaultPartyRole` in context |
| `platform-console/src/components/workspace/CreateClientModal.tsx` | Dynamic role + template-aware copy |
| `platform-console/src/pages/workspace/ClientsPage.tsx` | Expanded filter + template-aware copy |
| `platform-console/src/components/workspace/CreateWorkItemModal.tsx` | Party label + participant role + party filter |
| `platform-console/src/pages/workspace/CrmPage.tsx` | CRM create button uses work_item label |
| `platform-console/src/i18n/ruUi.ts` | `lead`, `contact` fallbacks |
| `platform-console/tsconfig.json` | Exclude `*.test.ts` from production build |
| `platform-console/src/workspace/labelHelpers.test.ts` | Lightweight assertion tests |
| `docs/FLEXITY_WORKITEM_PARTY_MAPPING_B3_IMPLEMENTATION_REPORT.md` | This report |

---

## 4. What Was Changed

### Dynamic party role (`pickDefaultPartyRole`)

Priority from `labels.party_roles` keys:

1. `lead`
2. `contact`
3. `client`
4. fallback: `client`

**Sales tenant** (`flexity_sales_basic` labels): → `lead`  
**Kindergarten** (no lead/contact/client in party_roles): → `client`

### Labels-aware copy

| UI | Before | After (sales template) |
|----|--------|--------------------------|
| Create party modal title | «Создать клиента» | «Создать контакт» |
| Party field | «Имя клиента» | «Имя контакт» |
| Clients page button | «Создать клиента» | «Создать контакт» |
| WorkItem party select | «Клиент» | «Контакт» |
| CRM create button | «Создать заявку» | «Создать лид» |
| Section subtitle | hardcoded guardian | «Лид / Контакт» (from labels) |

### ClientsPage filtering

Visible roles: `client`, `guardian`, `lead`, `contact`, `null`, plus **all keys** from `labels.party_roles` (e.g. `enrollee` for kindergarten).

### WorkItem participant

- UI label: template `party` entity label
- API `participants[].role`: `other` when default party role is `lead` or `contact`; else `client` (enum-compatible)

### Fallback labels (`ruUi.ts`)

Added: `lead` → «Лид», `contact` → «Контакт»

---

## 5. What Was Not Changed

| Area | Status |
|------|--------|
| Backend | ❌ not touched |
| Migrations | ❌ none |
| Public inbound | ❌ not enabled |
| Deploy / production | ❌ not touched |
| Lead / Diagnosis / Project tables | ❌ none |
| `kindergarten_basic` seed | ❌ unchanged |
| Hardcoded `flexity-sales` slug | ❌ none |
| Cherry-pick / merge | ❌ not done |
| CrmPipelineBoard party name on card | ❌ out of scope |

---

## 6. Tests / Checks

| Command | Result |
|---------|--------|
| `npm run build` (platform-console) | ✅ tsc + vite build OK |
| `npx tsx src/workspace/labelHelpers.test.ts` | ✅ all assertions passed |

**Backend tests:** not run (backend unchanged).

---

## 7. Manual Verification Checklist

| # | Check | Expected |
|---|-------|----------|
| 1 | Sales tenant → Create party | `party_role=lead`, UI «Создать контакт» |
| 2 | Party appears in Clients list | ✅ visible |
| 3 | Create WorkItem → select party | Label «Контакт», links via `primary_party_id` |
| 4 | CRM kanban | WorkItem in `new_lead` column |
| 5 | Sidebar hints | CRM: «Лид / Воронка продаж»; Clients: «Лид / Контакт» |
| 6 | Kindergarten tenant | Subtitle «Родитель / Контрагент»; create still `client` role |
| 7 | Guardian/enrollee parties in kg | Still visible in list |
| 8 | No slug hardcode | Behavior driven only by `/tenants/{id}/labels` |

> Requires running dev API + `npm run dev` in platform-console — not executed in this slice.

---

## 8. Risks / Notes

| Risk | Note |
|------|------|
| UI smoke not run live | API B2a passed; console needs manual run |
| Kanban card no party name | Known gap; future slice |
| Participant role `other` vs `client` | Semantic only; no backend change |
| Nav item still «Клиенты» (`ui.clients`) | Global i18n key unchanged — hint shows template context |
| Existing sales parties with `client` role | Still visible; new creates use `lead` |

---

## 9. Recommended Next Step

1. **B3 UI smoke** — run platform-console against dev API on `flexity-sales` + one kindergarten tenant.
2. **HQ decision on B2b** — public inbound cherry-pick plan after console smoke passes.
3. Optional **B3.1** — show party name on CRM kanban cards.

---

## 10. HQ Summary

### 1. What is done

- Label-driven `party_role=lead` for sales templates
- Template-aware Console copy (Контакт / Лид)
- Clients list shows lead/contact + template roles
- WorkItem create uses correct labels + participant role
- Build + unit assertions green

### 2. What changed for sales tenant

- New contacts are **leads**, not premature «clients»
- UI speaks sales language from `flexity_sales_basic` labels
- Manual funnel Party → WorkItem → stages ready in Console

### 3. What remains

- Live console UI smoke
- Public inbound (B2b) — still disabled
- Party → client conversion on deal won (B6)
- Kanban party name display

### 4. Next recommended step

**B3 console UI smoke** on running dev stack → then **B2b public inbound** HQ review.

---

*Report v1.0 — B3 minimal console slice complete.*
