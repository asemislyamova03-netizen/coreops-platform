/**
 * Lightweight assertions for labelHelpers — run: npx tsx src/workspace/labelHelpers.test.ts
 */
import assert from "node:assert/strict";
import { DEFAULT_WORKSPACE_LABELS, type TenantLabelsConfig } from "../types/labels";
import {
  collectVisiblePartyRoles,
  isPartyVisibleInClientsList,
  pickClientsSectionPartyRoleKey,
  pickDefaultPartyRole,
  pickWorkItemParticipantRole,
} from "./labelHelpers";

const salesLabels: TenantLabelsConfig = {
  entities: { work_item: "Лид", party: "Контакт", pipeline: "Воронка продаж" },
  party_roles: { lead: "Лид", client: "Клиент", contact: "Контакт" },
};

const kgLabels: TenantLabelsConfig = {
  entities: { work_item: "Заявка", party: "Контрагент" },
  party_roles: { enrollee: "Ребёнок", guardian: "Родитель", staff: "Сотрудник" },
};

assert.equal(pickDefaultPartyRole(salesLabels), "lead");
assert.equal(pickDefaultPartyRole(kgLabels), "client");
assert.equal(pickDefaultPartyRole(DEFAULT_WORKSPACE_LABELS), "client");

assert.equal(pickClientsSectionPartyRoleKey(salesLabels), "lead");
assert.equal(pickClientsSectionPartyRoleKey(kgLabels), "guardian");

assert.equal(isPartyVisibleInClientsList("lead", salesLabels), true);
assert.equal(isPartyVisibleInClientsList("enrollee", kgLabels), true);
assert.equal(isPartyVisibleInClientsList("supplier", salesLabels), false);

assert.ok(collectVisiblePartyRoles(salesLabels).has("lead"));
assert.ok(collectVisiblePartyRoles(kgLabels).has("enrollee"));

assert.equal(pickWorkItemParticipantRole("lead"), "other");
assert.equal(pickWorkItemParticipantRole("contact"), "other");
assert.equal(pickWorkItemParticipantRole("client"), "client");

console.log("labelHelpers.test.ts: all assertions passed");
