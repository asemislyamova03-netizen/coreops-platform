/**
 * Run: npx tsx src/pages/workspace/marketing/marketingPackContext.test.ts
 */
import assert from "node:assert/strict";
import {
  PACK_CONTEXT_EMPTY,
  buildPackCompletenessItems,
  buildPackTopicContextRows,
  buildPackWritingBrief,
  packContextCompletenessLabel,
  packContextCompletenessLevel,
} from "./marketingPackContext";

const richTopic = {
  id: "t1",
  legacy_topic_id: null,
  title: "Rich topic",
  rubric: "business_diagnosis",
  status: "approved" as const,
  angle: "Без хаоса",
  priority: 10,
  audience: "Основатели",
  pain: "Разрозненный учёт",
  insight: "Сначала процессы",
  source_ref: "Заявка demo",
  cta: "Запросить диагностику",
  funnel_stage: "diagnosis",
  notes: "Note",
  planned_date: "2026-07-22",
};

const rows = buildPackTopicContextRows(richTopic);
assert.equal(rows.find((row) => row.key === "audience")?.value, "Основатели");
assert.equal(rows.find((row) => row.key === "rubric")?.isEmpty, false);
assert.ok(String(rows.find((row) => row.key === "rubric")?.value).includes("диагностик"));

const emptyRows = buildPackTopicContextRows({
  id: "t2",
  legacy_topic_id: null,
  title: "Thin",
  rubric: "Vision",
  status: "draft",
});
assert.equal(emptyRows.find((row) => row.key === "cta")?.value, PACK_CONTEXT_EMPTY);
assert.equal(emptyRows.find((row) => row.key === "cta")?.isEmpty, true);

const brief = buildPackWritingBrief(richTopic);
assert.equal(brief.find((line) => line.key === "audience")?.value, "Основатели");
assert.equal(brief.find((line) => line.key === "cta")?.value, "Запросить диагностику");
assert.ok(String(brief.find((line) => line.key === "insight")?.value).includes("Сначала процессы"));

const items = buildPackCompletenessItems({
  topic: richTopic,
  texts: [{ id: "x", channel: "telegram", text: "Hello", status: "draft", char_count: 5, version: 1, created_at: "", updated_at: "" }],
  media_assets: [],
});
assert.equal(items.find((item) => item.key === "audience")?.filled, true);
assert.equal(items.find((item) => item.key === "media")?.filled, false);
assert.equal(items.find((item) => item.key === "texts")?.filled, true);
assert.equal(packContextCompletenessLevel(items), "partial");
assert.equal(packContextCompletenessLabel("full"), "Контекст темы: полный");

const noneItems = buildPackCompletenessItems({
  topic: null,
  texts: [{ id: "x", channel: "telegram", text: "   ", status: "draft", char_count: 0, version: 1, created_at: "", updated_at: "" }],
  media_assets: [],
});
assert.equal(packContextCompletenessLevel(noneItems), "none");

console.log("marketingPackContext.test.ts: ok");
