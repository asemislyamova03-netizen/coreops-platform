/**
 * Contract + helper tests for generic client signup (D1–D3).
 * Run: npx tsx src/pages/clientSignup.contract.test.ts
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildConsoleMarketingGuidePath,
  buildMarketingGuidePath,
  isValidTenantSlug,
  mapSignupError,
  slugifyTenantName,
} from "./clientSignupHelpers.ts";

const here = dirname(fileURLToPath(import.meta.url));
const srcRoot = join(here, "..");

assert.equal(slugifyTenantName("My Company!"), "my-company");
assert.equal(isValidTenantSlug("my-company"), true);
assert.equal(isValidTenantSlug("Bad_Slug"), false);
assert.equal(buildMarketingGuidePath("acme"), "/workspace/acme/marketing/guide");
assert.equal(
  buildConsoleMarketingGuidePath("acme"),
  "/console/workspace/acme/marketing/guide",
);
assert.match(mapSignupError(409, "Email already registered"), /email/i);
assert.match(mapSignupError(409, "Tenant slug already exists"), /slug|занят/i);

const routesSrc = readFileSync(join(srcRoot, "routes.tsx"), "utf8");
assert.match(routesSrc, /path="\/register"/);
assert.match(routesSrc, /ClientSignupPage/);

const apiSrc = readFileSync(join(srcRoot, "api/clientOnboarding.ts"), "utf8");
assert.match(apiSrc, /\/client-onboarding\/signup/);
assert.match(apiSrc, /Idempotency-Key/);
assert.match(apiSrc, /skipAuth:\s*true/);

const pageSrc = readFileSync(join(here, "ClientSignupPage.tsx"), "utf8");
assert.match(pageSrc, /full_name/);
assert.match(pageSrc, /tenant_slug/);
assert.match(pageSrc, /setTokens/);
assert.match(pageSrc, /refreshMe/);
assert.match(pageSrc, /submitting/);
assert.match(pageSrc, /idempotencyKeyRef/);
assert.match(pageSrc, /redirect_path|buildMarketingGuidePath/);

const loginSrc = readFileSync(join(here, "LoginPage.tsx"), "utf8");
assert.match(loginSrc, /to="\/register"/);

const mainSrc = readFileSync(join(srcRoot, "main.tsx"), "utf8");
assert.match(mainSrc, /basename="\/console"/);

console.log("clientSignup.contract.test.ts: OK");
