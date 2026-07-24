/**
 * Run: npx tsx src/api/marketingPublishingConnectionMap.test.ts
 */
import assert from "node:assert/strict";
import {
  SAFE_PUBLISHING_CONNECTION_KEYS,
  connectionViewHasSensitiveKey,
  toSafePublishingConnection,
} from "./marketingPublishingConnectionMap";

const poisoned = {
  id: "11111111-1111-1111-1111-111111111111",
  provider: "telegram",
  account_display_name: "Demo Bot",
  status: "active",
  token_status: "valid",
  has_secret: true,
  expires_at: "2026-12-01T00:00:00Z",
  last_checked_at: "2026-07-24T12:00:00Z",
  last_error_code: null,
  last_error_message_redacted: null,
  secret_ref: "secret://marketing/tenants/x/publishing-connections/y/versions/1",
  secret: "SHOULD_NEVER_APPEAR",
  access_token: "SHOULD_NEVER_APPEAR",
  credentials_json: { token: "nope" },
  ciphertext: "AAAA",
};

const view = toSafePublishingConnection(poisoned);

assert.equal(view.id, poisoned.id);
assert.equal(view.provider, "telegram");
assert.equal(view.account_display_name, "Demo Bot");
assert.equal(view.status, "active");
assert.equal(view.token_status, "valid");
assert.equal(view.has_secret, true);
assert.equal(view.expires_at, poisoned.expires_at);
assert.equal(view.last_checked_at, poisoned.last_checked_at);

for (const key of [
  "secret_ref",
  "secret",
  "access_token",
  "credentials_json",
  "ciphertext",
  "token",
]) {
  assert.equal(
    connectionViewHasSensitiveKey(view, key),
    false,
    `safe view must not expose ${key}`,
  );
}

const keys = Object.keys(view).sort();
assert.deepEqual(keys, [...SAFE_PUBLISHING_CONNECTION_KEYS].sort());

const emptyListMapped = ([] as Record<string, unknown>[]).map((row) =>
  toSafePublishingConnection(row),
);
assert.equal(emptyListMapped.length, 0);

const populated = [
  toSafePublishingConnection(poisoned),
  toSafePublishingConnection({
    id: "22222222-2222-2222-2222-222222222222",
    provider: "instagram",
    account_display_name: "Asem IG",
    status: "not_connected",
    token_status: "not_configured",
    has_secret: false,
    expires_at: null,
    last_checked_at: null,
    last_error_code: "unchecked_health",
    last_error_message_redacted: "Health not verified",
  }),
];
assert.equal(populated.length, 2);
assert.equal(populated[1].has_secret, false);
assert.equal(populated[1].last_error_code, "unchecked_health");

console.log("marketingPublishingConnectionMap.test.ts: OK");
