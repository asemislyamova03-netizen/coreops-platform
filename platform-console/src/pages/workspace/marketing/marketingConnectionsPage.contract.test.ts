/**
 * Route/API contract smoke for Connections UI-1 (no React render).
 * Run: npx tsx src/pages/workspace/marketing/marketingConnectionsPage.contract.test.ts
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  CONNECTIONS_EMPTY_STATE,
  CONNECTIONS_WIZARD_NEXT_STAGE_NOTE,
} from "./marketingConnectionLabels";

const here = dirname(fileURLToPath(import.meta.url));
const consoleRoot = join(here, "../../..");

const pageSrc = readFileSync(
  join(here, "MarketingConnectionsPage.tsx"),
  "utf8",
);
const routesSrc = readFileSync(join(consoleRoot, "routes.tsx"), "utf8");
const apiSrc = readFileSync(
  join(consoleRoot, "api/marketingPublishingConnections.ts"),
  "utf8",
);
const typesSrc = readFileSync(
  join(consoleRoot, "types/marketingPublishingConnection.ts"),
  "utf8",
);
const dashboardSrc = readFileSync(
  join(here, "MarketingDashboardPage.tsx"),
  "utf8",
);
const headerSrc = readFileSync(join(here, "MarketingPageHeader.tsx"), "utf8");
const mapSrc = readFileSync(
  join(consoleRoot, "api/marketingPublishingConnectionMap.ts"),
  "utf8",
);

assert.match(routesSrc, /marketing\/connections/);
assert.match(routesSrc, /MarketingConnectionsPage/);
assert.match(apiSrc, /\/marketing\/publishing-connections/);
assert.match(apiSrc, /listMarketingPublishingConnections/);
assert.match(apiSrc, /toSafePublishingConnection/);
assert.doesNotMatch(apiSrc, /\/connect|\/rotate|\/disconnect/);

assert.doesNotMatch(mapSrc, /\.secret_ref|\.access_token|\.ciphertext|\.credentials/);
assert.match(mapSrc, /has_secret/);

assert.match(pageSrc, /listMarketingPublishingConnections/);
assert.match(pageSrc, /CONNECTIONS_EMPTY_STATE/);
assert.match(pageSrc, /CONNECTIONS_WIZARD_NEXT_STAGE_NOTE/);
assert.doesNotMatch(pageSrc, /type=["']password["']/);
assert.doesNotMatch(pageSrc, /\bsecret_ref\b/);
assert.doesNotMatch(pageSrc, /\baccess_token\b/);
assert.doesNotMatch(pageSrc, /onConnect|rotateSecret|disconnect/);

assert.doesNotMatch(typesSrc, /\bsecret_ref\b|\bciphertext\b|\bcredentials\b|\baccess_token\b/);
assert.match(typesSrc, /has_secret/);

assert.match(dashboardSrc, /to=["']connections["']/);
assert.match(headerSrc, /\$\{base\}\/connections/);
assert.match(headerSrc, /marketingConnections/);

assert.ok(CONNECTIONS_EMPTY_STATE.includes("шаг за шагом"));
assert.ok(CONNECTIONS_WIZARD_NEXT_STAGE_NOTE.includes("следующем этапе"));

console.log("marketingConnectionsPage.contract.test.ts: OK");
