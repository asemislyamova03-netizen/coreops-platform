import { formatApiErrorMessage } from "../../../../i18n/ruUi";

const marketingApiErrorsRu: Record<string, string> = {
  preflight_not_passed: "Preflight не пройден. Сначала запустите проверку и исправьте ошибки.",
  invalid_mime_type: "Недопустимый MIME-тип файла.",
  unsupported_channel: "Неподдерживаемый канал.",
  pack_slug_exists: "Pack с таким slug уже существует.",
  topic_not_approved: "Взять тему можно только после её утверждения (status = approved).",
  topic_duplicate_blocked: "Тему нельзя взять: уже есть активный pack или тема уже использована.",
};

export function formatMarketingApiError(error: unknown, fallback: string): string {
  if (error instanceof Error) {
    const mapped = marketingApiErrorsRu[error.message] ?? formatApiErrorMessage(error.message);
    if (mapped !== error.message) {
      return mapped;
    }
    if (error.message.includes("preflight_not_passed")) {
      return marketingApiErrorsRu.preflight_not_passed;
    }
    if (error.message.includes("topic_not_approved")) {
      return marketingApiErrorsRu.topic_not_approved;
    }
    if (error.message.includes("topic_duplicate_blocked")) {
      return marketingApiErrorsRu.topic_duplicate_blocked;
    }
    if (error.message.includes("pack_slug_exists")) {
      return marketingApiErrorsRu.pack_slug_exists;
    }
    return error.message || fallback;
  }
  return fallback;
}
