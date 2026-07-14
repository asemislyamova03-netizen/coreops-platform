/**
 * Run: npx tsx src/pages/workspace/marketing/marketingLabels.test.ts
 */
import assert from "node:assert/strict";
import {
  MARKETING_PUBLISH_DISABLED_MESSAGE,
  marketingApprovalStatusLabel,
  marketingChannelLabel,
  marketingPackStatusLabel,
  marketingPreflightStatusLabel,
  marketingTopicStatusLabel,
} from "./marketingLabels";

assert.equal(marketingTopicStatusLabel("draft"), "Черновик");
assert.equal(marketingTopicStatusLabel("approved"), "Утверждена");
assert.equal(marketingTopicStatusLabel("used"), "Использована");
assert.equal(marketingTopicStatusLabel("archived"), "В архиве");
assert.equal(marketingTopicStatusLabel("unknown"), "unknown");

assert.equal(marketingPackStatusLabel("draft"), "Черновик");
assert.equal(marketingPackStatusLabel("ready_for_approval"), "Готов к согласованию");
assert.equal(marketingPackStatusLabel("preflight_failed"), "Preflight с ошибками");
assert.equal(marketingPackStatusLabel("approved"), "Согласован");

assert.equal(marketingPreflightStatusLabel("not_run"), "Не запускался");
assert.equal(marketingPreflightStatusLabel("passed"), "Пройден");
assert.equal(marketingPreflightStatusLabel("failed"), "Не пройден");

assert.equal(marketingApprovalStatusLabel("draft"), "Черновик");
assert.equal(marketingApprovalStatusLabel("pending"), "Ожидает");
assert.equal(marketingApprovalStatusLabel("approved"), "Согласован");
assert.equal(marketingApprovalStatusLabel("rejected"), "Отклонён");

assert.equal(marketingChannelLabel("telegram"), "Telegram");
assert.equal(marketingChannelLabel("instagram"), "Instagram");

assert.ok(MARKETING_PUBLISH_DISABLED_MESSAGE.includes("Публикация пока выключена"));
assert.ok(MARKETING_PUBLISH_DISABLED_MESSAGE.includes("source of truth"));

console.log("marketingLabels.test.ts: ok");
