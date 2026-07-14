/**
 * Run: npx tsx src/pages/workspace/marketing/marketingNextAction.test.ts
 */
import assert from "node:assert/strict";
import { MARKETING_PUBLISH_DISABLED_MESSAGE } from "./marketingLabels";
import { resolveMarketingNextAction } from "./marketingNextAction";

const base = {
  status: "draft",
  approval_status: "draft",
  preflight_status: "not_run",
  texts: [{ text: "" }, { text: "   " }],
  media_assets: [] as Array<{ status: string }>,
};

assert.equal(resolveMarketingNextAction(base).id, "fill_texts");
assert.match(resolveMarketingNextAction(base).message, /Заполните тексты/);

const withTexts = {
  ...base,
  texts: [{ text: "Hello telegram" }],
};
assert.equal(resolveMarketingNextAction(withTexts).id, "add_media");
assert.match(resolveMarketingNextAction(withTexts).message, /медиа/i);

const withMedia = {
  ...withTexts,
  media_assets: [{ status: "stored" }],
};
assert.equal(resolveMarketingNextAction(withMedia).id, "run_preflight");

const preflightFailed = {
  ...withMedia,
  preflight_status: "failed",
  status: "preflight_failed",
};
assert.equal(resolveMarketingNextAction(preflightFailed).id, "fix_preflight");
assert.match(resolveMarketingNextAction(preflightFailed).message, /Исправьте ошибки/);

const readyApproval = {
  ...withMedia,
  preflight_status: "passed",
  status: "ready_for_approval",
  approval_status: "pending",
};
assert.equal(resolveMarketingNextAction(readyApproval).id, "approve");
assert.match(resolveMarketingNextAction(readyApproval).message, /approval/);

const approved = {
  ...withMedia,
  preflight_status: "passed",
  status: "approved",
  approval_status: "approved",
};
const approvedAction = resolveMarketingNextAction(approved);
assert.equal(approvedAction.id, "publish_disabled");
assert.ok(approvedAction.message.includes(MARKETING_PUBLISH_DISABLED_MESSAGE));

const rejected = {
  ...withMedia,
  status: "draft",
  approval_status: "rejected",
  preflight_status: "passed",
};
assert.equal(resolveMarketingNextAction(rejected).id, "fix_rejected");

const archivedMediaOnly = {
  ...withTexts,
  media_assets: [{ status: "archived" }],
};
assert.equal(resolveMarketingNextAction(archivedMediaOnly).id, "add_media");

console.log("marketingNextAction.test.ts: ok");
