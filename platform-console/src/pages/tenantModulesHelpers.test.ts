/**
 * Lightweight assertions for tenant modules UI helpers —
 * run: npx tsx src/pages/tenantModulesHelpers.test.ts
 */
import assert from "node:assert/strict";
import type { ModuleDefinition, TenantModule } from "../types/module";
import {
  activeDependentsOf,
  buildTenantModuleRows,
  disableBlockedMessage,
  isModuleActive,
  requiredDependenciesOf,
} from "./tenantModulesHelpers";

const registry: ModuleDefinition[] = [
  {
    id: "1",
    code: "parties",
    name: "Parties",
    description: "Contacts",
    default_mode: "internal",
    dependencies_json: { required: [], recommended: [] },
    is_active: true,
  },
  {
    id: "2",
    code: "crm",
    name: "CRM",
    description: "Pipeline",
    default_mode: "internal",
    dependencies_json: { required: ["parties"], recommended: [] },
    is_active: true,
  },
  {
    id: "3",
    code: "booking",
    name: "Booking",
    description: null,
    default_mode: "internal",
    dependencies_json: { required: ["parties"], recommended: ["finance"] },
    is_active: true,
  },
];

const tenantModules: TenantModule[] = [
  {
    id: "t1",
    tenant_id: "tenant",
    module_code: "parties",
    status: "enabled",
    mode: "internal",
    external_provider_code: null,
    settings_json: {},
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "t2",
    tenant_id: "tenant",
    module_code: "crm",
    status: "enabled",
    mode: "internal",
    external_provider_code: null,
    settings_json: {},
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "t3",
    tenant_id: "tenant",
    module_code: "booking",
    status: "disabled",
    mode: "disabled",
    external_provider_code: null,
    settings_json: {},
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

assert.equal(isModuleActive("enabled"), true);
assert.equal(isModuleActive("trial"), true);
assert.equal(isModuleActive("disabled"), false);

assert.deepEqual(requiredDependenciesOf(registry[1]), ["parties"]);
assert.deepEqual(activeDependentsOf("parties", registry, tenantModules), ["crm"]);
assert.deepEqual(activeDependentsOf("crm", registry, tenantModules), []);

const rows = buildTenantModuleRows(tenantModules, registry);
const parties = rows.find((row) => row.module_code === "parties");
assert.ok(parties);
assert.equal(parties.name, "Parties");
assert.deepEqual(parties.required_dependencies, []);
assert.deepEqual(parties.active_dependents, ["crm"]);

const crm = rows.find((row) => row.module_code === "crm");
assert.ok(crm);
assert.deepEqual(crm.required_dependencies, ["parties"]);
assert.deepEqual(crm.active_dependents, []);

const msg = disableBlockedMessage("parties", ["crm", "booking"]);
assert.match(msg, /parties/);
assert.match(msg, /crm/);
assert.match(msg, /booking/);

console.log("tenantModulesHelpers.test.ts: OK");
