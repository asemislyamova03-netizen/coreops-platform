/**
 * Marketing M7-C2 Preflight v2 helpers (RU labels + report normalize).
 * Run: npx tsx src/pages/workspace/marketing/marketingPreflight.test.ts
 */
import type {
  MarketingPreflightChannelCheck,
  MarketingPreflightCheck,
  MarketingPreflightIssue,
  MarketingPreflightMediaChecks,
  MarketingPreflightResponse,
  MarketingPreflightTopicContextSummary,
} from "../../../types/marketing";
import { marketingChannelLabel } from "./marketingLabels";
import { marketingFunnelLabel } from "./marketingTaxonomy";

export type PreflightSummaryTone = "failed" | "warning" | "passed" | "empty";

export interface NormalizedPreflightReport {
  version: string | null;
  passed: boolean | null;
  status: "passed" | "failed" | "warning" | null;
  checked_at: string | null;
  blockers: MarketingPreflightIssue[];
  warnings: MarketingPreflightIssue[];
  checklist: MarketingPreflightCheck[];
  topic_context_summary: MarketingPreflightTopicContextSummary | null;
  channel_checks: MarketingPreflightChannelCheck[];
  media_checks: MarketingPreflightMediaChecks | null;
  channel_eligibility: Record<string, boolean>;
  hasReport: boolean;
}

const BLOCKER_LABELS: Record<string, string> = {
  topic_missing: "У пака нет связанной темы",
  topic_not_approved: "Тема ещё не утверждена",
  no_publishable_text: "Нет текста для публикации",
  context_triple_missing: "Не заполнены аудитория, боль и CTA",
  all_texts_too_short: "Тексты слишком короткие для проверки",
  pack_metadata_incomplete: "Не заполнены название, slug или дата пака",
  channel_text_missing: "Нет строки текста для канала",
  media_invalid_mime: "Недопустимый тип медиа-файла",
};

const WARNING_LABELS: Record<string, string> = {
  insight_missing: "Не заполнен инсайт",
  source_ref_missing: "Нет источника или референса",
  cta_missing_for_funnel: "Для этого этапа воронки лучше указать CTA",
  media_missing: "Нет медиа-плана или медиа-метаданных",
  channel_text_short: "Некоторые тексты короткие",
  notes_missing: "Нет заметок для контекста",
  topic_planned_date_missing: "Не указана плановая дата темы",
  telegram_text_too_long: "Текст Telegram длиннее лимита",
  insights_text_empty: "Insights пустой (допустимо)",
  media_not_1080: "Медиа не 1080×1080",
};

const CHECK_LABELS: Record<string, string> = {
  pack_metadata_complete: "Метаданные пака",
  at_least_one_channel_text: "Есть текст хотя бы в одном канале",
  social_texts_min_length: "Минимальная длина social-текстов",
  topic_linked: "Тема связана",
  topic_approved: "Тема утверждена",
  context_triple: "Аудитория / боль / CTA",
  insight_present: "Инсайт",
  source_ref_present: "Источник / референс",
  cta_for_funnel: "CTA для этапа воронки",
  notes_present: "Заметки темы",
  topic_planned_date_present: "Плановая дата темы",
  media_present: "Медиа-метаданные",
  telegram_length_limit: "Лимит длины Telegram",
  telegram_row_exists: "Строка Telegram",
  telegram_text_present: "Текст Telegram",
  telegram_social_length_ok: "Длина Telegram",
  instagram_row_exists: "Строка Instagram",
  instagram_text_present: "Текст Instagram",
  instagram_social_length_ok: "Длина Instagram",
  threads_row_exists: "Строка Threads",
  threads_text_present: "Текст Threads",
  threads_social_length_ok: "Длина Threads",
  insights_row_exists: "Строка Insights",
  insights_text_present: "Текст Insights",
};

const SUMMARY_TITLES: Record<PreflightSummaryTone, string> = {
  failed: "Нужно исправить перед утверждением",
  warning: "Можно утверждать, но есть предупреждения",
  passed: "Проверка пройдена",
  empty: "Проверка ещё не запускалась",
};

const SUMMARY_SUBTITLES: Record<PreflightSummaryTone, string> = {
  failed: "Исправьте пункты ниже и запустите проверку снова.",
  warning: "Предупреждения не блокируют согласование.",
  passed: "Можно перейти на вкладку Согласование.",
  empty: "Запустите preflight, чтобы увидеть результаты проверки.",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function asString(value: unknown, fallback = ""): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function parseIssue(raw: unknown): MarketingPreflightIssue | null {
  if (typeof raw === "string") {
    const code = raw.trim();
    if (!code) return null;
    return { code, message: code };
  }
  if (!isRecord(raw)) return null;
  const code = asString(raw.code || raw.key).trim();
  if (!code) return null;
  return {
    code,
    message: asString(raw.message || raw.detail || raw.label, code),
    channel: raw.channel == null ? null : asString(raw.channel),
  };
}

function parseIssues(raw: unknown): MarketingPreflightIssue[] {
  if (!Array.isArray(raw)) return [];
  const out: MarketingPreflightIssue[] = [];
  for (const item of raw) {
    const parsed = parseIssue(item);
    if (parsed) out.push(parsed);
  }
  return out;
}

function parseCheck(raw: unknown): MarketingPreflightCheck | null {
  if (typeof raw === "string") {
    const code = raw.trim();
    if (!code) return null;
    return { code, passed: true, message: null };
  }
  if (!isRecord(raw)) return null;
  const code = asString(raw.code || raw.key).trim();
  if (!code) return null;
  const status = asString(raw.status).toLowerCase();
  let passed = asBoolean(raw.passed, true);
  if ("passed" in raw) {
    passed = asBoolean(raw.passed, true);
  } else if (status === "fail" || status === "failed" || status === "error") {
    passed = false;
  } else if (status === "warn" || status === "warning") {
    passed = false;
  } else if (status === "pass" || status === "passed" || status === "ok") {
    passed = true;
  }
  return {
    code,
    passed,
    message: raw.message == null ? null : asString(raw.message),
    channel: raw.channel == null ? null : asString(raw.channel),
  };
}

function parseChecks(raw: unknown): MarketingPreflightCheck[] {
  if (!Array.isArray(raw)) return [];
  const out: MarketingPreflightCheck[] = [];
  for (const item of raw) {
    const parsed = parseCheck(item);
    if (parsed) out.push(parsed);
  }
  return out;
}

function parseTopicSummary(raw: unknown): MarketingPreflightTopicContextSummary | null {
  if (!isRecord(raw)) return null;
  return {
    topic_id: raw.topic_id == null ? undefined : asString(raw.topic_id),
    title: raw.title == null ? null : asString(raw.title),
    status: raw.status == null ? null : asString(raw.status),
    audience: raw.audience == null ? null : asString(raw.audience),
    pain: raw.pain == null ? null : asString(raw.pain),
    insight: raw.insight == null ? null : asString(raw.insight),
    source_ref: raw.source_ref == null ? null : asString(raw.source_ref),
    cta: raw.cta == null ? null : asString(raw.cta),
    funnel_stage: raw.funnel_stage == null ? null : asString(raw.funnel_stage),
    notes: raw.notes == null ? null : asString(raw.notes),
    planned_date: raw.planned_date == null ? null : asString(raw.planned_date),
    has_audience: asBoolean(raw.has_audience),
    has_pain: asBoolean(raw.has_pain),
    has_insight: asBoolean(raw.has_insight),
    has_source_ref: asBoolean(raw.has_source_ref),
    has_cta: asBoolean(raw.has_cta),
    has_notes: asBoolean(raw.has_notes),
    has_planned_date: asBoolean(raw.has_planned_date),
  };
}

function parseChannelChecks(raw: unknown): MarketingPreflightChannelCheck[] {
  if (!Array.isArray(raw)) return [];
  const out: MarketingPreflightChannelCheck[] = [];
  for (const item of raw) {
    if (!isRecord(item)) continue;
    const channel = asString(item.channel).trim();
    if (!channel) continue;
    out.push({
      channel,
      present: asBoolean(item.present),
      length: asNumber(item.length),
      short_warn: asBoolean(item.short_warn),
      below_blocker_threshold: asBoolean(item.below_blocker_threshold),
    });
  }
  return out;
}

function parseMediaChecks(raw: unknown): MarketingPreflightMediaChecks | null {
  if (!isRecord(raw)) return null;
  return {
    count: asNumber(raw.count),
    missing: asBoolean(raw.missing, asNumber(raw.count) === 0),
  };
}

function parseEligibility(raw: unknown): Record<string, boolean> {
  if (!isRecord(raw)) return {};
  const out: Record<string, boolean> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value === "boolean") out[key] = value;
  }
  return out;
}

function isEmptyStoredReport(raw: Record<string, unknown>): boolean {
  const keys = Object.keys(raw);
  if (keys.length === 0) return true;
  const blockers = parseIssues(raw.blockers ?? raw.errors);
  const warnings = parseIssues(raw.warnings);
  const checks = parseChecks(raw.checklist ?? raw.checks);
  const hasStatus = typeof raw.status === "string" && raw.status.length > 0;
  const hasCheckedAt = typeof raw.checked_at === "string" && raw.checked_at.length > 0;
  return !hasStatus && !hasCheckedAt && blockers.length === 0 && warnings.length === 0 && checks.length === 0;
}

/**
 * Normalize API PreflightResponse or stored preflight_report_json.
 */
export function normalizePreflightReport(
  input: MarketingPreflightResponse | Record<string, unknown> | null | undefined,
): NormalizedPreflightReport {
  const empty: NormalizedPreflightReport = {
    version: null,
    passed: null,
    status: null,
    checked_at: null,
    blockers: [],
    warnings: [],
    checklist: [],
    topic_context_summary: null,
    channel_checks: [],
    media_checks: null,
    channel_eligibility: {},
    hasReport: false,
  };

  if (input == null) return empty;
  if (!isRecord(input)) return empty;
  if (isEmptyStoredReport(input)) return empty;

  const blockers = parseIssues(input.blockers ?? input.errors);
  const warnings = parseIssues(input.warnings);
  const checklist = parseChecks(input.checklist ?? input.checks);
  const statusRaw = asString(input.status).toLowerCase();
  const status =
    statusRaw === "passed" || statusRaw === "failed" || statusRaw === "warning"
      ? statusRaw
      : null;

  let passed: boolean | null = typeof input.passed === "boolean" ? input.passed : null;
  if (passed === null) {
    if (status === "failed" || blockers.length > 0) passed = false;
    else if (status === "passed" || status === "warning") passed = true;
  }

  return {
    version: typeof input.version === "string" ? input.version : null,
    passed,
    status,
    checked_at: typeof input.checked_at === "string" ? input.checked_at : null,
    blockers,
    warnings,
    checklist,
    topic_context_summary: parseTopicSummary(input.topic_context_summary),
    channel_checks: parseChannelChecks(input.channel_checks),
    media_checks: parseMediaChecks(input.media_checks),
    channel_eligibility: parseEligibility(input.channel_eligibility),
    hasReport: true,
  };
}

export function resolvePreflightSummaryTone(
  report: NormalizedPreflightReport | null | undefined,
): PreflightSummaryTone {
  if (!report || !report.hasReport) return "empty";
  if (report.blockers.length > 0 || report.status === "failed" || report.passed === false) {
    return "failed";
  }
  if (report.warnings.length > 0 || report.status === "warning") return "warning";
  return "passed";
}

export function preflightSummaryTitle(tone: PreflightSummaryTone): string {
  return SUMMARY_TITLES[tone];
}

export function preflightSummarySubtitle(tone: PreflightSummaryTone): string {
  return SUMMARY_SUBTITLES[tone];
}

export function preflightIssueLabel(code: string): string {
  const key = code.trim();
  if (!key) return "Неизвестная проверка";
  return (
    BLOCKER_LABELS[key] ??
    WARNING_LABELS[key] ??
    CHECK_LABELS[key] ??
    `Неизвестная проверка: ${key}`
  );
}

export function preflightCheckLabel(code: string): string {
  const key = code.trim();
  if (!key) return "Неизвестная проверка";
  if (CHECK_LABELS[key]) return CHECK_LABELS[key];
  if (BLOCKER_LABELS[key] || WARNING_LABELS[key]) return preflightIssueLabel(key);
  if (key.startsWith("media_mime_")) return "MIME медиа-файла";
  return `Неизвестная проверка: ${key}`;
}

export function formatPreflightIssueLine(issue: MarketingPreflightIssue): string {
  const label = preflightIssueLabel(issue.code);
  const channel =
    issue.channel && issue.channel.trim()
      ? ` (${marketingChannelLabel(issue.channel)})`
      : "";
  return `${label}${channel}`;
}

export function channelCheckStatusLabel(check: MarketingPreflightChannelCheck): string {
  if (!check.present) return "Пусто";
  if (check.below_blocker_threshold) return "Слишком короткий";
  if (check.short_warn) return "Короткий";
  return "Ок";
}

export function topicContextHasAnyFilled(
  summary: MarketingPreflightTopicContextSummary | null,
): boolean {
  if (!summary) return false;
  const flags = [
    summary.has_audience,
    summary.has_pain,
    summary.has_insight,
    summary.has_source_ref,
    summary.has_cta,
    summary.has_notes,
    summary.has_planned_date,
  ];
  if (flags.some(Boolean)) return true;
  const values = [
    summary.audience,
    summary.pain,
    summary.insight,
    summary.source_ref,
    summary.cta,
    summary.notes,
    summary.planned_date,
    summary.funnel_stage,
  ];
  return values.some((value) => Boolean(value && String(value).trim()));
}

export function topicContextDisplayRows(
  summary: MarketingPreflightTopicContextSummary,
): Array<{ key: string; label: string; value: string; filled: boolean }> {
  const funnel = summary.funnel_stage?.trim()
    ? marketingFunnelLabel(summary.funnel_stage)
    : "";
  const rows: Array<{ key: string; label: string; value: string; filled: boolean }> = [
    {
      key: "audience",
      label: "Аудитория",
      value: (summary.audience ?? "").trim(),
      filled: Boolean(summary.has_audience || (summary.audience ?? "").trim()),
    },
    {
      key: "pain",
      label: "Боль",
      value: (summary.pain ?? "").trim(),
      filled: Boolean(summary.has_pain || (summary.pain ?? "").trim()),
    },
    {
      key: "insight",
      label: "Инсайт",
      value: (summary.insight ?? "").trim(),
      filled: Boolean(summary.has_insight || (summary.insight ?? "").trim()),
    },
    {
      key: "source_ref",
      label: "Источник",
      value: (summary.source_ref ?? "").trim(),
      filled: Boolean(summary.has_source_ref || (summary.source_ref ?? "").trim()),
    },
    {
      key: "cta",
      label: "CTA",
      value: (summary.cta ?? "").trim(),
      filled: Boolean(summary.has_cta || (summary.cta ?? "").trim()),
    },
    {
      key: "funnel_stage",
      label: "Этап воронки",
      value: funnel,
      filled: Boolean(funnel),
    },
    {
      key: "planned_date",
      label: "Плановая дата",
      value: (summary.planned_date ?? "").trim(),
      filled: Boolean(summary.has_planned_date || (summary.planned_date ?? "").trim()),
    },
  ];
  return rows;
}

export function getBlockers(report: NormalizedPreflightReport): MarketingPreflightIssue[] {
  return report.blockers;
}

export function getWarnings(report: NormalizedPreflightReport): MarketingPreflightIssue[] {
  return report.warnings;
}
