/**
 * Run: npx tsx src/workspace/leadStageHelpHelpers.test.ts
 */

import assert from "node:assert/strict";
import { getLeadStageHelp } from "./leadStageHelpHelpers";

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`fail - ${name}`);
    throw error;
  }
}

test("returns help for accepted", () => {
  const help = getLeadStageHelp("accepted");
  assert.ok(help);
  assert.equal(help.title, "Согласовано");
  assert.match(help.help, /Tenant создавать не обязательно/);
  assert.match(help.help, /консультация|аудит|пилот|внедрение/);
});

test("returns help for converted_to_tenant", () => {
  const help = getLeadStageHelp("converted_to_tenant");
  assert.ok(help);
  assert.equal(help.title, "Переведён в клиентский контур");
  assert.match(help.help, /реально создан/);
  assert.match(help.help, /won|delivery/i);
});

test("returns null for other stages", () => {
  assert.equal(getLeadStageHelp("new_lead"), null);
  assert.equal(getLeadStageHelp("negotiation"), null);
  assert.equal(getLeadStageHelp(null), null);
  assert.equal(getLeadStageHelp(undefined), null);
  assert.equal(getLeadStageHelp(""), null);
});

console.log("All leadStageHelpHelpers tests passed.");
