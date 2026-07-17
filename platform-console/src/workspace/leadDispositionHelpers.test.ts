/**
 * Lightweight assertions — run: npx tsx src/workspace/leadDispositionHelpers.test.ts
 */
import assert from "node:assert/strict";
import {
  getDispositionLabel,
  isRejectedWithMissingDisposition,
  readDisposition,
  readDispositionNote,
} from "./leadDispositionHelpers";

assert.equal(getDispositionLabel("spam"), "Спам");
assert.equal(getDispositionLabel("off_topic"), "Не по теме");
assert.equal(getDispositionLabel(null), null);

assert.equal(readDisposition({ disposition: "test" }), "test");
assert.equal(readDisposition({}), null);

assert.equal(readDispositionNote({ disposition_note: "note" }), "note");

assert.equal(isRejectedWithMissingDisposition({}, "rejected"), true);
assert.equal(
  isRejectedWithMissingDisposition({ disposition: "spam" }, "rejected"),
  false,
);
assert.equal(isRejectedWithMissingDisposition({}, "new_lead"), false);

console.log("leadDispositionHelpers.test.ts: all assertions passed");
