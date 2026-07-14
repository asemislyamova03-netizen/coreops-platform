/**
 * Run: npx tsx src/pages/workspace/marketing/marketingTaxonomy.test.ts
 */
import assert from "node:assert/strict";
import {
  MARKETING_FUNNEL_OPTIONS,
  MARKETING_PRIORITY_OPTIONS,
  MARKETING_RUBRIC_OPTIONS,
  buildTopicCreatePayload,
  buildTopicUpdatePayload,
  extractTopicEditorial,
  marketingFunnelLabel,
  marketingRubricLabel,
  priorityLabel,
  priorityLevelFromValue,
  priorityValueFromLevel,
} from "./marketingTaxonomy";

assert.equal(MARKETING_RUBRIC_OPTIONS.length, 10);
assert.equal(MARKETING_FUNNEL_OPTIONS.length, 6);
assert.equal(MARKETING_PRIORITY_OPTIONS.length, 3);

assert.equal(marketingRubricLabel("ai_employees"), "AI-сотрудники");
assert.equal(marketingRubricLabel("unknown_code"), "unknown_code");
assert.equal(marketingFunnelLabel("trust"), "Trust — доверие");
assert.equal(priorityLevelFromValue(0), "low");
assert.equal(priorityLevelFromValue(5), "normal");
assert.equal(priorityLevelFromValue(10), "high");
assert.equal(priorityValueFromLevel("high"), 10);
assert.equal(priorityLabel(10), "High");

const createPayload = buildTopicCreatePayload({
  title: "  Demo topic  ",
  rubric: "business_diagnosis",
  angle: " angle ",
  priority: 5,
  audience: " founders ",
  pain: "",
  insight: "insight",
  source_ref: "https://example.com",
  cta: "Запросить диагностику",
  funnel_stage: "diagnosis",
  notes: "",
  planned_date: "2026-07-20",
});
assert.equal(createPayload.title, "Demo topic");
assert.equal(createPayload.rubric, "business_diagnosis");
assert.equal(createPayload.angle, "angle");
assert.equal(createPayload.audience, "founders");
assert.equal(createPayload.insight, "insight");
assert.equal(createPayload.planned_date, "2026-07-20");
assert.equal("pain" in createPayload, false);
assert.equal("notes" in createPayload, false);

const updatePayload = buildTopicUpdatePayload({
  title: "Updated",
  rubric: "asem_column",
  angle: "",
  priority: 0,
  audience: "",
  pain: "pain",
  insight: "",
  source_ref: "",
  cta: "",
  funnel_stage: "awareness",
  notes: "note",
  planned_date: "",
});
assert.equal(updatePayload.angle, null);
assert.equal(updatePayload.audience, "");
assert.equal(updatePayload.pain, "pain");
assert.equal(updatePayload.funnel_stage, "awareness");

const editorial = extractTopicEditorial({
  audience: null,
  metadata_json: { audience: "from-meta", cta: "CTA" },
});
assert.equal(editorial.audience, "from-meta");
assert.equal(editorial.cta, "CTA");

console.log("marketingTaxonomy.test.ts: ok");
