/**
 * Run: npx tsx src/workspace/partyMatchUiHelpers.test.ts
 */
import assert from "node:assert/strict";
import {
  buildPartyMatchPayload,
  formatMatchedOn,
  hasExactMatch,
  matchTypeLabel,
  partyMatchFingerprint,
  pickVisibleMatches,
} from "./partyMatchUiHelpers";
import type { PartyMatchHit } from "../types/party";

assert.equal(buildPartyMatchPayload({ name: "ab", phone: "123", email: "" }), null);
assert.deepEqual(buildPartyMatchPayload({ name: "Иван", phone: "", email: "" }), {
  name: "Иван",
  phone: null,
  email: null,
});
assert.ok(
  buildPartyMatchPayload({ name: "", phone: "+7 777 123 45 67", email: "" })?.phone,
);
assert.ok(
  buildPartyMatchPayload({ name: "", phone: "", email: "a@b.co" })?.email,
);

assert.equal(
  partyMatchFingerprint({ name: "Иван", phone: "+7 (777) 123-45-67", email: "A@B.C" }),
  partyMatchFingerprint({ name: "иван", phone: "77771234567", email: "a@b.c" }),
);

assert.equal(formatMatchedOn(["phone", "email"]), "телефон, email");
assert.equal(matchTypeLabel("exact"), "точное совпадение");
assert.equal(matchTypeLabel("weak"), "похожее имя");

const hits = [
  { party_id: "1", match_type: "weak", score: 30, matched_on: ["name"] },
  { party_id: "2", match_type: "exact", score: 90, matched_on: ["phone"] },
  { party_id: "3", match_type: "exact", score: 95, matched_on: ["email"] },
  { party_id: "4", match_type: "weak", score: 30, matched_on: ["name"] },
] as PartyMatchHit[];

const visible = pickVisibleMatches(hits);
assert.equal(visible.length, 3);
assert.equal(visible[0]?.match_type, "exact");
assert.equal(hasExactMatch(hits), true);

console.log("partyMatchUiHelpers.test.ts: all assertions passed");
