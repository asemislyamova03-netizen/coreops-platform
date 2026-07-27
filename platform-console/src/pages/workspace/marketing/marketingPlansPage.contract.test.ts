/**
 * Route/API contract smoke for M7.5-D Content Plans UI (no React render).
 * Run: npx tsx src/pages/workspace/marketing/marketingPlansPage.contract.test.ts
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const consoleRoot = join(here, "../../..");

const routesSrc = readFileSync(join(consoleRoot, "routes.tsx"), "utf8");
const apiSrc = readFileSync(join(consoleRoot, "api/marketing.ts"), "utf8");
const headerSrc = readFileSync(join(here, "MarketingPageHeader.tsx"), "utf8");
const dashboardSrc = readFileSync(join(here, "MarketingDashboardPage.tsx"), "utf8");
const plansSrc = readFileSync(join(here, "MarketingPlansPage.tsx"), "utf8");
const detailSrc = readFileSync(join(here, "MarketingPlanDetailPage.tsx"), "utf8");
const promptSrc = readFileSync(join(here, "MarketingPlanPromptPage.tsx"), "utf8");
const importSrc = readFileSync(join(here, "MarketingPlanImportPage.tsx"), "utf8");
const topicsSrc = readFileSync(join(here, "MarketingTopicsPage.tsx"), "utf8");
const taxonomySrc = readFileSync(join(here, "marketingTaxonomy.ts"), "utf8");
const ruUiSrc = readFileSync(join(consoleRoot, "i18n/ruUi.ts"), "utf8");

assert.match(routesSrc, /marketing\/plans/);
assert.match(routesSrc, /MarketingPlansPage/);
assert.match(routesSrc, /MarketingPlanDetailPage/);
assert.match(routesSrc, /MarketingPlanPromptPage/);
assert.match(routesSrc, /MarketingPlanImportPage/);
assert.match(routesSrc, /marketing\/plans\/prompt/);
assert.match(routesSrc, /marketing\/plans\/import/);

assert.match(headerSrc, /\$\{base\}\/plans/);
assert.match(headerSrc, /marketingPlans/);
assert.match(dashboardSrc, /to=["']plans["']/);
assert.match(ruUiSrc, /marketingPlans:\s*"Контент-планы"/);

assert.match(apiSrc, /listMarketingContentPlans/);
assert.match(apiSrc, /exportMarketingContentPlanPrompt/);
assert.match(apiSrc, /previewMarketingContentPlanImport/);
assert.match(apiSrc, /commitMarketingContentPlanImport/);
assert.match(apiSrc, /createTopicFromContentPlanItem/);
assert.doesNotMatch(apiSrc, /openai|anthropic|generateContent/i);

assert.match(plansSrc, /createMarketingContentPlan/);
assert.match(plansSrc, /Сформировать промпт/);
assert.match(plansSrc, /Импорт JSON/);

assert.match(detailSrc, /approveMarketingContentPlan/);
assert.match(detailSrc, /createTopicFromContentPlanItem/);
assert.match(detailSrc, /Создать тему/);
assert.match(detailSrc, /window\.confirm/);

assert.match(promptSrc, /exportMarketingContentPlanPrompt/);
assert.match(promptSrc, /Копировать промпт/);
assert.match(promptSrc, /navigator\.clipboard\.writeText/);
assert.match(promptSrc, /сам модели не вызывает/);
assert.match(promptSrc, /getActiveMarketingGuide/);

assert.match(importSrc, /previewMarketingContentPlanImport/);
assert.match(importSrc, /commitMarketingContentPlanImport/);
assert.match(importSrc, /unknown_rubric_codes/);
assert.match(importSrc, /type=["']file["']/);
assert.match(importSrc, /fingerprint_already_imported/);
assert.doesNotMatch(importSrc, /FormData|upload.*s3|fetch\(["']https?:\/\//i);

assert.doesNotMatch(topicsSrc, /MARKETING_RUBRIC_OPTIONS/);
assert.match(topicsSrc, /Открыть рубрики/);
assert.match(taxonomySrc, /@deprecated/);
assert.match(taxonomySrc, /Not SoT/);

console.log("marketingPlansPage.contract.test.ts: OK");
