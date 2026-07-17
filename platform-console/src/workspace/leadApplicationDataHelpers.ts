/**
 * Helpers for LeadDetailModal application/inbound data block (E7-A).
 * Reads WorkItem.custom_fields only — no backend changes.
 * Run: npx tsx src/workspace/leadApplicationDataHelpers.test.ts
 */

import type { WorkItem } from "../types/workflows";

export type ApplicationDataRow = {
  key: string;
  label: string;
  value: string;
  href?: string;
};

export type LeadApplicationDataView = {
  shouldShow: boolean;
  rows: ApplicationDataRow[];
};

function asTrimmedString(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return null;
}

function readField(
  customFields: Record<string, unknown> | undefined,
  ...keys: string[]
): string | null {
  if (!customFields) return null;
  for (const key of keys) {
    const value = asTrimmedString(customFields[key]);
    if (value) return value;
  }
  return null;
}

function readNonNegativeInt(
  customFields: Record<string, unknown> | undefined,
  key: string,
): number | null {
  if (!customFields) return null;
  const raw = customFields[key];
  if (typeof raw === "number" && Number.isFinite(raw) && raw >= 0) {
    return Math.floor(raw);
  }
  if (typeof raw === "string" && raw.trim()) {
    const parsed = Number(raw.trim());
    if (Number.isFinite(parsed) && parsed >= 0) return Math.floor(parsed);
  }
  return null;
}

function formatConsent(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  try {
    return date.toLocaleString("ru-RU");
  } catch {
    return value;
  }
}

function safeHttpHref(value: string): string | undefined {
  try {
    const url = new URL(value);
    if (url.protocol === "http:" || url.protocol === "https:") {
      return url.toString();
    }
  } catch {
    return undefined;
  }
  return undefined;
}

function shortenUrl(value: string, maxLen = 64): string {
  if (value.length <= maxLen) return value;
  return `${value.slice(0, maxLen - 1)}…`;
}

function buildMatchLine(
  customFields: Record<string, unknown> | undefined,
): string | null {
  const matchNote = readField(customFields, "match_note");
  if (matchNote) {
    return "Контакт найден автоматически";
  }
  const count = readNonNegativeInt(customFields, "possible_match_count");
  if (count !== null && count > 0) {
    return `Есть возможное совпадение: ${count}`;
  }
  return null;
}

function hasMeaningfulApplicationSignal(
  source: string | null | undefined,
  customFields: Record<string, unknown> | undefined,
): boolean {
  if ((source ?? "").trim() === "website_demo") return true;
  if (readField(customFields, "form_name")) return true;
  if (readField(customFields, "page_url", "source_page")) return true;
  if (readField(customFields, "utm_source")) return true;
  if (readField(customFields, "utm_medium")) return true;
  if (readField(customFields, "utm_campaign")) return true;
  if (readField(customFields, "utm_content")) return true;
  if (readField(customFields, "utm_term")) return true;
  if (readField(customFields, "consent_at", "consent_accepted_at")) return true;
  if (readField(customFields, "match_note")) return true;
  const count = readNonNegativeInt(customFields, "possible_match_count");
  if (count !== null) return true;
  return false;
}

/**
 * Build readonly application data rows for LeadDetailModal.
 * Does not expose possible_match_party_ids in the UI.
 */
export function buildLeadApplicationDataView(
  workItem: Pick<WorkItem, "source" | "custom_fields"> & {
    description?: string | null;
  },
  options?: {
    sourceLabel?: string | null;
  },
): LeadApplicationDataView {
  const customFields = workItem.custom_fields ?? {};
  const source = workItem.source ?? null;

  if (!hasMeaningfulApplicationSignal(source, customFields)) {
    return { shouldShow: false, rows: [] };
  }

  const rows: ApplicationDataRow[] = [];

  const formName = readField(customFields, "form_name");
  if (formName) {
    rows.push({ key: "form_name", label: "Форма", value: formName });
  }

  const pageUrl = readField(customFields, "page_url", "source_page");
  if (pageUrl) {
    rows.push({
      key: "page_url",
      label: "Страница",
      value: shortenUrl(pageUrl),
      href: safeHttpHref(pageUrl),
    });
  }

  const sourceCode = (source ?? "").trim();
  if (sourceCode) {
    const label = (options?.sourceLabel ?? "").trim();
    rows.push({
      key: "source",
      label: "Источник",
      value: label || sourceCode,
    });
  }

  const utmCampaign = readField(customFields, "utm_campaign");
  if (utmCampaign) {
    rows.push({ key: "utm_campaign", label: "Кампания", value: utmCampaign });
  }

  const utmSource = readField(customFields, "utm_source");
  if (utmSource) {
    rows.push({ key: "utm_source", label: "UTM source", value: utmSource });
  }

  const utmMedium = readField(customFields, "utm_medium");
  if (utmMedium) {
    rows.push({ key: "utm_medium", label: "UTM medium", value: utmMedium });
  }

  const utmContent = readField(customFields, "utm_content");
  if (utmContent) {
    rows.push({ key: "utm_content", label: "UTM content", value: utmContent });
  }

  const utmTerm = readField(customFields, "utm_term");
  if (utmTerm) {
    rows.push({ key: "utm_term", label: "UTM term", value: utmTerm });
  }

  const referrer = readField(customFields, "referrer");
  if (referrer) {
    rows.push({
      key: "referrer",
      label: "Referrer",
      value: shortenUrl(referrer),
      href: safeHttpHref(referrer),
    });
  }

  const consentAt = readField(customFields, "consent_at", "consent_accepted_at");
  if (consentAt) {
    rows.push({
      key: "consent_at",
      label: "Consent",
      value: formatConsent(consentAt),
    });
  }

  const matchLine = buildMatchLine(customFields);
  if (matchLine) {
    rows.push({ key: "match", label: "Match", value: matchLine });
  }

  return {
    shouldShow: rows.length > 0,
    rows,
  };
}
