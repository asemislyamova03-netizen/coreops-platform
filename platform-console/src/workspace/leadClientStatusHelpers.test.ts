/**
 * Run: npx tsx src/workspace/leadClientStatusHelpers.test.ts
 */

import assert from "node:assert/strict";
import {
  buildMarkAsClientPayload,
  getLeadClientStatusView,
  MARK_AS_CLIENT_HELP,
} from "./leadClientStatusHelpers";

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`fail - ${name}`);
    throw error;
  }
}

test("no Party → hidden", () => {
  const view = getLeadClientStatusView({
    hasParty: false,
    stageCode: "accepted",
    partyRole: "lead",
  });
  assert.equal(view.shouldShowClientBlock, false);
  assert.equal(view.canMarkAsClient, false);
});

test("accepted + role lead → canMarkAsClient true", () => {
  const view = getLeadClientStatusView({
    hasParty: true,
    stageCode: "accepted",
    partyRole: "lead",
  });
  assert.equal(view.canMarkAsClient, true);
  assert.equal(view.shouldShowClientBlock, true);
  assert.equal(view.showClientBadge, false);
  assert.equal(view.helpText, MARK_AS_CLIENT_HELP);
});

test("accepted + role contact → canMarkAsClient true", () => {
  const view = getLeadClientStatusView({
    hasParty: true,
    stageCode: "accepted",
    partyRole: "contact",
  });
  assert.equal(view.canMarkAsClient, true);
});

test("accepted + missing role → canMarkAsClient true", () => {
  const view = getLeadClientStatusView({
    hasParty: true,
    stageCode: "accepted",
    partyRole: null,
  });
  assert.equal(view.canMarkAsClient, true);
  assert.equal(view.partyRole, null);
});

test("accepted + role client → already client badge", () => {
  const view = getLeadClientStatusView({
    hasParty: true,
    stageCode: "accepted",
    partyRole: "client",
  });
  assert.equal(view.isClient, true);
  assert.equal(view.canMarkAsClient, false);
  assert.equal(view.showClientBadge, true);
  assert.equal(view.shouldShowClientBlock, true);
});

test("non-accepted + role lead → no button", () => {
  const view = getLeadClientStatusView({
    hasParty: true,
    stageCode: "negotiation",
    partyRole: "lead",
  });
  assert.equal(view.canMarkAsClient, false);
  assert.equal(view.shouldShowClientBlock, false);
});

test("non-accepted + role client → badge allowed", () => {
  const view = getLeadClientStatusView({
    hasParty: true,
    stageCode: "converted_to_tenant",
    partyRole: "client",
  });
  assert.equal(view.showClientBadge, true);
  assert.equal(view.canMarkAsClient, false);
  assert.equal(view.shouldShowClientBlock, true);
});

test("action payload is { party_role: client }", () => {
  assert.deepEqual(buildMarkAsClientPayload(), { party_role: "client" });
});

console.log("All leadClientStatusHelpers tests passed.");
