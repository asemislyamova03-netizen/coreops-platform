/**
 * Rubric / funnel / priority helpers for Marketing.
 * Rubric SoT is tenant API (`GET /marketing/rubrics`).
 * `LEGACY_RUBRIC_LABELS` is display-only fallback for historical topic.rubric codes.
 * Run: npx tsx src/pages/workspace/marketing/marketingTaxonomy.test.ts
 */

import type {
  MarketingTopicCreatePayload,
  MarketingTopicUpdatePayload,
} from "../../../types/marketing";

export type MarketingFunnelStage =
  | "awareness"
  | "trust"
  | "diagnosis"
  | "consultation"
  | "product_education"
  | "objection_handling";

export type MarketingPriorityLevel = "low" | "normal" | "high";

export interface MarketingRubricOption {
  code: string;
  label: string;
}

export interface MarketingTopicEditorialFields {
  audience?: string | null;
  pain?: string | null;
  insight?: string | null;
  source_ref?: string | null;
  cta?: string | null;
  funnel_stage?: string | null;
  notes?: string | null;
  planned_date?: string | null;
}

/** @deprecated Not SoT — legacy labels only for historical codes. Prefer API rubrics. */
export const LEGACY_RUBRIC_LABELS: Record<string, string> = {
  asem_column: "Авторская колонка Асем",
  digital_organism: "Flexity как цифровой организм",
  erp_crm_future: "ERP/CRM будущего",
  ai_employees: "AI-сотрудники",
  business_diagnosis: "Бизнес-диагностика",
  sales_inbox_review: "Разбор заявок и продаж",
  client_journey: "Кейсы / путь клиента",
  marketing_contentops: "Marketing / ContentOps",
  industry_modules: "Clinic / Booking / отраслевые модули",
  founder_notes: "Founder notes / за кадром",
};

/** @deprecated Use listMarketingRubrics(); kept for test/legacy import compatibility. */
export const MARKETING_RUBRIC_OPTIONS: MarketingRubricOption[] = Object.entries(
  LEGACY_RUBRIC_LABELS,
).map(([code, label]) => ({ code, label }));

export const MARKETING_FUNNEL_OPTIONS: Array<{ code: MarketingFunnelStage; label: string }> = [
  { code: "awareness", label: "Awareness — узнаваемость" },
  { code: "trust", label: "Trust — доверие" },
  { code: "diagnosis", label: "Diagnosis — диагностика" },
  { code: "consultation", label: "Consultation — консультация" },
  { code: "product_education", label: "Product education" },
  { code: "objection_handling", label: "Objection handling" },
];

export const MARKETING_PRIORITY_OPTIONS: Array<{
  level: MarketingPriorityLevel;
  value: number;
  label: string;
}> = [
  { level: "low", value: 0, label: "Low" },
  { level: "normal", value: 5, label: "Normal" },
  { level: "high", value: 10, label: "High" },
];

const FUNNEL_LABELS = Object.fromEntries(
  MARKETING_FUNNEL_OPTIONS.map((item) => [item.code, item.label]),
) as Record<string, string>;

export function marketingRubricLabel(
  code: string | null | undefined,
  liveOptions?: MarketingRubricOption[],
): string {
  if (!code) return "—";
  const fromLive = liveOptions?.find((item) => item.code === code)?.label;
  if (fromLive) return fromLive;
  return LEGACY_RUBRIC_LABELS[code] ?? code;
}

export function marketingFunnelLabel(code: string | null | undefined): string {
  if (!code) return "—";
  return FUNNEL_LABELS[code] ?? code;
}

export function priorityLevelFromValue(priority: number): MarketingPriorityLevel {
  if (priority >= 10) return "high";
  if (priority <= 0) return "low";
  return "normal";
}

export function priorityValueFromLevel(level: MarketingPriorityLevel): number {
  const found = MARKETING_PRIORITY_OPTIONS.find((item) => item.level === level);
  return found?.value ?? 5;
}

export function priorityLabel(priority: number): string {
  const level = priorityLevelFromValue(priority);
  return MARKETING_PRIORITY_OPTIONS.find((item) => item.level === level)?.label ?? String(priority);
}

export function extractTopicEditorial(
  topic: {
    audience?: string | null;
    pain?: string | null;
    insight?: string | null;
    source_ref?: string | null;
    cta?: string | null;
    funnel_stage?: string | null;
    notes?: string | null;
    planned_date?: string | null;
    metadata_json?: Record<string, unknown>;
  },
): Required<{ [K in keyof MarketingTopicEditorialFields]: string }> {
  const meta = topic.metadata_json ?? {};
  const read = (key: keyof MarketingTopicEditorialFields): string => {
    const top = topic[key];
    if (typeof top === "string" && top.trim()) return top.trim();
    const fromMeta = meta[key];
    return typeof fromMeta === "string" ? fromMeta.trim() : "";
  };
  return {
    audience: read("audience"),
    pain: read("pain"),
    insight: read("insight"),
    source_ref: read("source_ref"),
    cta: read("cta"),
    funnel_stage: read("funnel_stage"),
    notes: read("notes"),
    planned_date: read("planned_date"),
  };
}

export function buildTopicCreatePayload(input: {
  title: string;
  rubric: string;
  angle: string;
  priority: number;
  audience: string;
  pain: string;
  insight: string;
  source_ref: string;
  cta: string;
  funnel_stage: string;
  notes: string;
  planned_date: string;
  status?: "draft" | "approved";
}): MarketingTopicCreatePayload {
  const payload: MarketingTopicCreatePayload = {
    title: input.title.trim(),
    rubric: input.rubric.trim() || "general",
    source: "console",
    status: input.status ?? "draft",
    priority: input.priority,
  };
  if (input.angle.trim()) payload.angle = input.angle.trim();
  if (input.audience.trim()) payload.audience = input.audience.trim();
  if (input.pain.trim()) payload.pain = input.pain.trim();
  if (input.insight.trim()) payload.insight = input.insight.trim();
  if (input.source_ref.trim()) payload.source_ref = input.source_ref.trim();
  if (input.cta.trim()) payload.cta = input.cta.trim();
  if (input.funnel_stage.trim()) payload.funnel_stage = input.funnel_stage.trim();
  if (input.notes.trim()) payload.notes = input.notes.trim();
  if (input.planned_date.trim()) payload.planned_date = input.planned_date.trim();
  return payload;
}

/** Partial update: empty strings clear editorial fields on backend. */
export function buildTopicUpdatePayload(input: {
  title: string;
  rubric: string;
  angle: string;
  priority: number;
  audience: string;
  pain: string;
  insight: string;
  source_ref: string;
  cta: string;
  funnel_stage: string;
  notes: string;
  planned_date: string;
}): MarketingTopicUpdatePayload {
  return {
    title: input.title.trim(),
    rubric: input.rubric.trim() || "general",
    angle: input.angle.trim() || null,
    priority: input.priority,
    audience: input.audience.trim(),
    pain: input.pain.trim(),
    insight: input.insight.trim(),
    source_ref: input.source_ref.trim(),
    cta: input.cta.trim(),
    funnel_stage: input.funnel_stage.trim(),
    notes: input.notes.trim(),
    planned_date: input.planned_date.trim(),
  };
}
