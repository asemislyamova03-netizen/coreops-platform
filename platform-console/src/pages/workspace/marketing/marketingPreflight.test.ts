/**
 * Run: npx tsx src/pages/workspace/marketing/marketingPreflight.test.ts
 */
import assert from "node:assert/strict";
import {
  formatPreflightIssueLine,
  normalizePreflightReport,
  preflightCheckLabel,
  preflightIssueLabel,
  preflightSummarySubtitle,
  preflightSummaryTitle,
  resolvePreflightSummaryTone,
  topicContextHasAnyFilled,
} from "./marketingPreflight";

// --- empty / no report ---
assert.equal(resolvePreflightSummaryTone(null), "empty");
assert.equal(resolvePreflightSummaryTone(normalizePreflightReport(null)), "empty");
assert.equal(resolvePreflightSummaryTone(normalizePreflightReport({})), "empty");
assert.equal(preflightSummaryTitle("empty"), "Проверка ещё не запускалась");

// --- blockers → fix ---
const failed = normalizePreflightReport({
  status: "failed",
  passed: false,
  errors: [{ code: "topic_missing", message: "Pack has no linked topic" }],
  warnings: [],
  checks: [],
});
assert.equal(failed.hasReport, true);
assert.equal(failed.blockers.length, 1);
assert.equal(resolvePreflightSummaryTone(failed), "failed");
assert.equal(preflightSummaryTitle("failed"), "Нужно исправить перед утверждением");

// --- warnings only → can approve with warnings ---
const warnOnly = normalizePreflightReport({
  status: "warning",
  passed: true,
  errors: [],
  blockers: [],
  warnings: [{ code: "insight_missing", message: "Topic insight is empty" }],
  checks: [],
});
assert.equal(resolvePreflightSummaryTone(warnOnly), "warning");
assert.equal(
  preflightSummaryTitle("warning"),
  "Можно утверждать, но есть предупреждения",
);
assert.match(preflightSummarySubtitle("warning"), /не блокируют/i);

// --- clean pass ---
const clean = normalizePreflightReport({
  status: "passed",
  passed: true,
  errors: [],
  warnings: [],
  checks: [{ code: "topic_linked", passed: true }],
  checked_at: "2026-07-14T12:00:00Z",
});
assert.equal(resolvePreflightSummaryTone(clean), "passed");
assert.equal(preflightSummaryTitle("passed"), "Проверка пройдена");

// --- code mapping blockers ---
assert.equal(preflightIssueLabel("topic_missing"), "У пака нет связанной темы");
assert.equal(preflightIssueLabel("topic_not_approved"), "Тема ещё не утверждена");
assert.equal(preflightIssueLabel("no_publishable_text"), "Нет текста для публикации");
assert.equal(
  preflightIssueLabel("context_triple_missing"),
  "Не заполнены аудитория, боль и CTA",
);
assert.equal(
  preflightIssueLabel("all_texts_too_short"),
  "Тексты слишком короткие для проверки",
);
assert.equal(
  preflightIssueLabel("pack_metadata_incomplete"),
  "Не заполнены название, slug или дата пака",
);

// --- code mapping warnings ---
assert.equal(preflightIssueLabel("insight_missing"), "Не заполнен инсайт");
assert.equal(preflightIssueLabel("source_ref_missing"), "Нет источника или референса");
assert.equal(
  preflightIssueLabel("cta_missing_for_funnel"),
  "Для этого этапа воронки лучше указать CTA",
);
assert.equal(
  preflightIssueLabel("media_missing"),
  "Нет медиа-плана или медиа-метаданных",
);
assert.equal(preflightIssueLabel("channel_text_short"), "Некоторые тексты короткие");
assert.equal(preflightIssueLabel("notes_missing"), "Нет заметок для контекста");
assert.equal(
  preflightIssueLabel("topic_planned_date_missing"),
  "Не указана плановая дата темы",
);

// --- unknown fallback ---
assert.equal(preflightIssueLabel("totally_unknown_xyz"), "Неизвестная проверка: totally_unknown_xyz");
assert.equal(preflightCheckLabel("weird_check"), "Неизвестная проверка: weird_check");

// --- old M6 report compatibility ---
const m6 = normalizePreflightReport({
  status: "failed",
  checked_at: "2026-07-01T10:00:00Z",
  errors: [
    { code: "no_publishable_text", message: "At least one channel must have non-empty text" },
  ],
  warnings: [{ code: "insights_text_empty", message: "Insights text is empty (allowed for MVP)" }],
  checks: [{ code: "at_least_one_channel_text", passed: false, message: "all channel texts are empty" }],
  channel_eligibility: { telegram: false },
});
assert.equal(m6.version, null);
assert.equal(m6.blockers[0]?.code, "no_publishable_text");
assert.equal(m6.warnings[0]?.code, "insights_text_empty");
assert.equal(m6.checklist[0]?.code, "at_least_one_channel_text");
assert.equal(m6.topic_context_summary, null);
assert.equal(m6.channel_checks.length, 0);
assert.equal(m6.media_checks, null);
assert.equal(resolvePreflightSummaryTone(m6), "failed");

// --- aliases: blockers / checklist preferred ---
const v2 = normalizePreflightReport({
  version: "m7-c1",
  status: "warning",
  passed: true,
  errors: [{ code: "should_not_win", message: "old" }],
  blockers: [{ code: "topic_missing", message: "Pack has no linked topic" }],
  warnings: [{ code: "media_missing", message: "Pack has no media metadata" }],
  checks: [{ code: "from_checks", passed: true }],
  checklist: [{ code: "from_checklist", passed: false, message: "prefer checklist" }],
  topic_context_summary: {
    topic_id: "t1",
    audience: "Основатели",
    pain: "",
    insight: "X",
    has_audience: true,
    has_pain: false,
    has_insight: true,
  },
  channel_checks: [
    {
      channel: "telegram",
      present: true,
      length: 12,
      short_warn: true,
      below_blocker_threshold: true,
    },
  ],
  media_checks: { count: 0, missing: true },
});
assert.equal(v2.version, "m7-c1");
assert.equal(v2.blockers[0]?.code, "topic_missing");
assert.equal(v2.checklist[0]?.code, "from_checklist");
assert.equal(v2.channel_checks[0]?.length, 12);
assert.equal(v2.media_checks?.missing, true);
assert.equal(topicContextHasAnyFilled(v2.topic_context_summary), true);
assert.equal(resolvePreflightSummaryTone(v2), "failed"); // blockers win over status=warning

// blockers via errors only (no blockers key)
const viaErrors = normalizePreflightReport({
  status: "failed",
  errors: [{ code: "channel_text_missing", message: "No text row", channel: "telegram" }],
  warnings: [],
});
assert.equal(viaErrors.blockers[0]?.code, "channel_text_missing");
assert.match(formatPreflightIssueLine(viaErrors.blockers[0]!), /строки текста/i);

// string array issues
const stringArr = normalizePreflightReport({
  status: "failed",
  errors: ["topic_missing"],
  warnings: ["insight_missing"],
  checks: ["topic_linked"],
});
assert.equal(stringArr.blockers[0]?.code, "topic_missing");
assert.equal(stringArr.warnings[0]?.code, "insight_missing");
assert.equal(stringArr.checklist[0]?.code, "topic_linked");

console.log("marketingPreflight.test.ts: all assertions passed");
