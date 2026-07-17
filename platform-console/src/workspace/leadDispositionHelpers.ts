import type { DispositionCode } from "../types/workflows";

export const DISPOSITION_CODES: DispositionCode[] = [
  "spam",
  "off_topic",
  "duplicate",
  "test",
  "no_response",
  "other",
];

export const DISPOSITION_LABELS: Record<DispositionCode, string> = {
  spam: "Спам",
  off_topic: "Не по теме",
  duplicate: "Дубль",
  test: "Тест",
  no_response: "Нет ответа",
  other: "Другое",
};

export function getDispositionLabel(code: string | null | undefined): string | null {
  if (!code) {
    return null;
  }
  if (code in DISPOSITION_LABELS) {
    return DISPOSITION_LABELS[code as DispositionCode];
  }
  return code;
}

export function readDisposition(customFields: Record<string, unknown>): string | null {
  const value = customFields.disposition;
  return typeof value === "string" && value.trim() ? value : null;
}

export function readDispositionNote(customFields: Record<string, unknown>): string {
  const value = customFields.disposition_note;
  return typeof value === "string" ? value : "";
}

export function isRejectedWithMissingDisposition(
  customFields: Record<string, unknown>,
  stageCode: string | null | undefined,
): boolean {
  return stageCode === "rejected" && !readDisposition(customFields);
}

export function getDispositionBadgeClass(code: string | null | undefined): string {
  if (!code) {
    return "badge";
  }
  return `badge badge-disposition badge-disposition-${code}`;
}

export function isNoteRecommendedForDisposition(code: string): boolean {
  return code === "other";
}
