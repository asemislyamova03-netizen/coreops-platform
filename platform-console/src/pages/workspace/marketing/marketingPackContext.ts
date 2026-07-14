/**
 * Pack detail topic context helpers for Marketing M7-B.
 * Run: npx tsx src/pages/workspace/marketing/marketingPackContext.test.ts
 */
import type { MarketingPackDetail, MarketingTopicSummaryInPack } from "../../../types/marketing";
import {
  marketingFunnelLabel,
  marketingRubricLabel,
  priorityLabel,
} from "./marketingTaxonomy";

export const PACK_CONTEXT_EMPTY = "Не заполнено";

export type PackTopicContextFieldKey =
  | "title"
  | "rubric"
  | "angle"
  | "audience"
  | "pain"
  | "insight"
  | "source_ref"
  | "cta"
  | "funnel_stage"
  | "priority"
  | "planned_date"
  | "notes";

export interface PackTopicContextRow {
  key: PackTopicContextFieldKey;
  label: string;
  value: string;
  isEmpty: boolean;
}

export interface PackWritingBriefLine {
  key: string;
  label: string;
  value: string;
  isEmpty: boolean;
}

export interface PackCompletenessItem {
  key: string;
  label: string;
  filled: boolean;
}

export type PackContextCompletenessLevel = "full" | "partial" | "weak" | "none";

function displayValue(raw: string | null | undefined): { value: string; isEmpty: boolean } {
  const text = typeof raw === "string" ? raw.trim() : "";
  if (!text) return { value: PACK_CONTEXT_EMPTY, isEmpty: true };
  return { value: text, isEmpty: false };
}

export function buildPackTopicContextRows(
  topic: MarketingTopicSummaryInPack | null | undefined,
): PackTopicContextRow[] {
  if (!topic) {
    return [
      {
        key: "title",
        label: "Тема",
        value: PACK_CONTEXT_EMPTY,
        isEmpty: true,
      },
    ];
  }

  const funnelShown = topic.funnel_stage?.trim()
    ? displayValue(marketingFunnelLabel(topic.funnel_stage))
    : displayValue(null);
  const priorityShown =
    typeof topic.priority === "number"
      ? { value: priorityLabel(topic.priority), isEmpty: false }
      : displayValue(null);

  return [
    { key: "title", label: "Тема", ...displayValue(topic.title) },
    { key: "rubric", label: "Рубрика", ...displayValue(marketingRubricLabel(topic.rubric)) },
    { key: "angle", label: "Угол", ...displayValue(topic.angle) },
    { key: "audience", label: "Аудитория", ...displayValue(topic.audience) },
    { key: "pain", label: "Боль / проблема", ...displayValue(topic.pain) },
    { key: "insight", label: "Инсайт", ...displayValue(topic.insight) },
    { key: "source_ref", label: "Источник / референс", ...displayValue(topic.source_ref) },
    { key: "cta", label: "CTA", ...displayValue(topic.cta) },
    { key: "funnel_stage", label: "Этап воронки", ...funnelShown },
    { key: "priority", label: "Приоритет", ...priorityShown },
    { key: "planned_date", label: "Плановая дата темы", ...displayValue(topic.planned_date) },
    { key: "notes", label: "Заметки", ...displayValue(topic.notes) },
  ];
}

export function buildPackWritingBrief(
  topic: MarketingTopicSummaryInPack | null | undefined,
): PackWritingBriefLine[] {
  if (!topic) {
    return [
      { key: "audience", label: "Кому пишем", value: PACK_CONTEXT_EMPTY, isEmpty: true },
      { key: "pain", label: "Какая боль", value: PACK_CONTEXT_EMPTY, isEmpty: true },
      { key: "insight", label: "Главная мысль", value: PACK_CONTEXT_EMPTY, isEmpty: true },
      { key: "source", label: "На что опираемся", value: PACK_CONTEXT_EMPTY, isEmpty: true },
      { key: "cta", label: "Что должен сделать читатель", value: PACK_CONTEXT_EMPTY, isEmpty: true },
      { key: "tone", label: "Тон / угол подачи", value: PACK_CONTEXT_EMPTY, isEmpty: true },
    ];
  }

  const insightBits = [topic.insight?.trim(), topic.angle?.trim()].filter(Boolean);
  const toneBits = [
    topic.angle?.trim(),
    topic.rubric ? marketingRubricLabel(topic.rubric) : "",
    topic.funnel_stage ? marketingFunnelLabel(topic.funnel_stage) : "",
  ].filter(Boolean);

  const lines: Array<{ key: string; label: string; raw: string }> = [
    { key: "audience", label: "Кому пишем", raw: topic.audience?.trim() || "" },
    { key: "pain", label: "Какая боль", raw: topic.pain?.trim() || "" },
    { key: "insight", label: "Главная мысль", raw: insightBits.join(" · ") },
    { key: "source", label: "На что опираемся", raw: topic.source_ref?.trim() || "" },
    { key: "cta", label: "Что должен сделать читатель", raw: topic.cta?.trim() || "" },
    { key: "tone", label: "Тон / угол подачи", raw: toneBits.join(" · ") },
  ];

  return lines.map((line) => {
    const shown = displayValue(line.raw);
    return {
      key: line.key,
      label: line.label,
      value: shown.value,
      isEmpty: shown.isEmpty,
    };
  });
}

export function buildPackCompletenessItems(
  pack: Pick<MarketingPackDetail, "topic" | "texts" | "media_assets">,
): PackCompletenessItem[] {
  const topic = pack.topic;
  const hasAudience = Boolean(topic?.audience?.trim());
  const hasPain = Boolean(topic?.pain?.trim());
  const hasInsightOrSource = Boolean(topic?.insight?.trim() || topic?.source_ref?.trim());
  const hasCta = Boolean(topic?.cta?.trim());
  const hasText = pack.texts.some((row) => row.text.trim().length > 0);
  const hasMedia = pack.media_assets.some((asset) => asset.status !== "archived");

  return [
    { key: "audience", label: "Аудитория", filled: hasAudience },
    { key: "pain", label: "Боль", filled: hasPain },
    { key: "insight_source", label: "Инсайт / источник", filled: hasInsightOrSource },
    { key: "cta", label: "CTA", filled: hasCta },
    { key: "texts", label: "Текст каналов", filled: hasText },
    { key: "media", label: "Медиа", filled: hasMedia },
  ];
}

export function packContextCompletenessLevel(
  items: PackCompletenessItem[],
): PackContextCompletenessLevel {
  if (items.length === 0) return "none";
  const filled = items.filter((item) => item.filled).length;
  if (filled === 0) return "none";
  if (filled === items.length) return "full";
  if (filled <= 2) return "weak";
  return "partial";
}

export function packContextCompletenessLabel(level: PackContextCompletenessLevel): string {
  switch (level) {
    case "full":
      return "Контекст темы: полный";
    case "partial":
      return "Контекст темы: частичный";
    case "weak":
      return "Контекст темы: слабый";
    default:
      return "Контекст темы: не заполнен";
  }
}
