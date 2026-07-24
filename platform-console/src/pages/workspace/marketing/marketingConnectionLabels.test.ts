/**
 * Run: npx tsx src/pages/workspace/marketing/marketingConnectionLabels.test.ts
 */
import assert from "node:assert/strict";
import {
  CONNECTIONS_EMPTY_STATE,
  CONNECTIONS_WIZARD_NEXT_STAGE_NOTE,
  publishingConnectionErrorDisplay,
  publishingConnectionStatusLabel,
  publishingConnectionSummaryLabel,
  publishingProviderLabel,
  publishingTokenStatusLabel,
} from "./marketingConnectionLabels";

assert.equal(publishingProviderLabel("telegram"), "Telegram");
assert.equal(publishingProviderLabel("instagram"), "Instagram");
assert.equal(publishingProviderLabel("threads"), "Threads");
assert.equal(publishingProviderLabel("tiktok"), "TikTok");
assert.equal(publishingProviderLabel("other"), "other");

assert.equal(publishingConnectionStatusLabel("not_connected"), "Не подключено");
assert.equal(publishingConnectionStatusLabel("active"), "Подключено");
assert.equal(publishingConnectionStatusLabel("error"), "Ошибка подключения");
assert.equal(publishingConnectionStatusLabel("disabled"), "Отключено");
assert.equal(publishingConnectionStatusLabel("expired"), "Нужно переподключить");

assert.equal(publishingTokenStatusLabel("not_configured"), "Требуется проверка");
assert.equal(publishingTokenStatusLabel("valid"), "Подключено");
assert.equal(publishingTokenStatusLabel("expiring"), "Истекает срок");
assert.equal(publishingTokenStatusLabel("invalid"), "Нужно переподключить");

assert.equal(
  publishingConnectionSummaryLabel("active", "expiring"),
  "Истекает срок",
);
assert.equal(
  publishingConnectionSummaryLabel("active", "not_configured"),
  "Требуется проверка",
);
assert.equal(
  publishingConnectionSummaryLabel("not_connected", "not_configured"),
  "Не подключено",
);

assert.equal(publishingConnectionErrorDisplay(null, null), "—");
assert.equal(publishingConnectionErrorDisplay("unchecked_health", null), "unchecked_health");
assert.equal(
  publishingConnectionErrorDisplay("unchecked_health", "Health not verified"),
  "unchecked_health: Health not verified",
);

assert.ok(CONNECTIONS_EMPTY_STATE.includes("шаг за шагом"));
assert.ok(CONNECTIONS_WIZARD_NEXT_STAGE_NOTE.includes("следующем этапе"));
assert.ok(!CONNECTIONS_EMPTY_STATE.toLowerCase().includes("token"));
assert.ok(!CONNECTIONS_EMPTY_STATE.toLowerCase().includes("secret_ref"));

console.log("marketingConnectionLabels.test.ts: OK");
