/**
 * Run: npx tsx src/workspace/partyWorkItemHistoryHelpers.test.ts
 */
import assert from "node:assert/strict";
import {
  PARTY_HISTORY_DISPLAY_LIMIT,
  selectPartyHistoryItems,
} from "./partyWorkItemHistoryHelpers";
import type { WorkItem } from "../types/workflows";

function stub(id: string): WorkItem {
  return {
    id,
    tenant_id: "t",
    pipeline_id: "p",
    stage_id: "s",
    work_item_type: "lead",
    title: id,
    description: null,
    primary_party_id: "party",
    status: "in_progress",
    amount: null,
    currency: null,
    source: "manual",
    custom_fields: {},
    participants: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    created_by_user_id: null,
    updated_by_user_id: null,
  };
}

const items = [stub("a"), stub("b"), stub("c"), stub("d"), stub("e"), stub("f"), stub("g")];

assert.deepEqual(
  selectPartyHistoryItems(items, "a").map((i) => i.id),
  ["b", "c", "d", "e", "f"],
);
assert.equal(selectPartyHistoryItems(items, "a").length, PARTY_HISTORY_DISPLAY_LIMIT);
assert.deepEqual(selectPartyHistoryItems([stub("only")], "only"), []);
assert.deepEqual(
  selectPartyHistoryItems(items, "missing").map((i) => i.id),
  ["a", "b", "c", "d", "e"],
);
assert.deepEqual(
  selectPartyHistoryItems(items, "c", 2).map((i) => i.id),
  ["a", "b"],
);

console.log("partyWorkItemHistoryHelpers.test.ts: all assertions passed");
