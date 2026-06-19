import type { Pipeline } from "../types/workflows";

export function pickDefaultPipeline(pipelines: Pipeline[]): Pipeline | null {
  if (pipelines.length === 0) return null;
  return pipelines.find((p) => p.is_default) ?? pipelines[0];
}

export function formatMoney(amount: string | number, currency: string): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  if (Number.isNaN(value)) {
    return `${amount} ${currency || ""}`.trim();
  }
  try {
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${amount} ${currency || ""}`.trim();
  }
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  try {
    return date.toLocaleDateString("ru-RU");
  } catch {
    return "—";
  }
}
