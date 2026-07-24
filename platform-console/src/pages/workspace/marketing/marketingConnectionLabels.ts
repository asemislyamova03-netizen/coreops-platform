/**
 * RU labels for Marketing publishing connections (Connections UI-1).
 * Run: npx tsx src/pages/workspace/marketing/marketingConnectionLabels.test.ts
 */
import type {
  PublishingConnectionProvider,
  PublishingConnectionStatus,
  PublishingTokenStatus,
} from "../../../types/marketingPublishingConnection";

export const CONNECTIONS_EMPTY_STATE =
  "Здесь будут подключённые соцсети и сервисы. Flexity проведёт вас по настройке шаг за шагом.";

export const CONNECTIONS_WIZARD_NEXT_STAGE_NOTE =
  "Подключение будет доступно на следующем этапе.";

export const CONNECTIONS_PAGE_SUBTITLE =
  "Каналы и сервисы организации для публикаций. Секреты хранятся безопасно и никогда не показываются в этом списке.";

const PROVIDER_LABELS: Record<PublishingConnectionProvider, string> = {
  telegram: "Telegram",
  instagram: "Instagram",
  threads: "Threads",
  tiktok: "TikTok",
};

const CONNECTION_STATUS_LABELS: Record<PublishingConnectionStatus, string> = {
  not_connected: "Не подключено",
  active: "Подключено",
  error: "Ошибка подключения",
  disabled: "Отключено",
  expired: "Нужно переподключить",
};

const TOKEN_STATUS_LABELS: Record<PublishingTokenStatus, string> = {
  not_configured: "Требуется проверка",
  valid: "Подключено",
  expiring: "Истекает срок",
  invalid: "Нужно переподключить",
};

export function publishingProviderLabel(provider: string): string {
  return PROVIDER_LABELS[provider as PublishingConnectionProvider] ?? provider;
}

export function publishingConnectionStatusLabel(status: string): string {
  return (
    CONNECTION_STATUS_LABELS[status as PublishingConnectionStatus] ?? status
  );
}

export function publishingTokenStatusLabel(tokenStatus: string): string {
  return TOKEN_STATUS_LABELS[tokenStatus as PublishingTokenStatus] ?? tokenStatus;
}

/**
 * Single human summary combining connection + token status for banners/empty hints.
 * Table still shows both columns separately.
 */
export function publishingConnectionSummaryLabel(
  status: string,
  tokenStatus: string,
): string {
  if (status === "disabled") return CONNECTION_STATUS_LABELS.disabled;
  if (status === "error") return CONNECTION_STATUS_LABELS.error;
  if (status === "expired" || tokenStatus === "invalid") {
    return CONNECTION_STATUS_LABELS.expired;
  }
  if (status === "not_connected") return CONNECTION_STATUS_LABELS.not_connected;
  if (tokenStatus === "expiring") return TOKEN_STATUS_LABELS.expiring;
  if (tokenStatus === "not_configured") return TOKEN_STATUS_LABELS.not_configured;
  if (status === "active" && tokenStatus === "valid") {
    return CONNECTION_STATUS_LABELS.active;
  }
  if (status === "active") return TOKEN_STATUS_LABELS.not_configured;
  return publishingConnectionStatusLabel(status);
}

/** Safe error line: code only + optional redacted message (never raw provider payload). */
export function publishingConnectionErrorDisplay(
  code: string | null | undefined,
  redactedMessage: string | null | undefined,
): string {
  const safeCode = (code || "").trim();
  const safeMsg = (redactedMessage || "").trim();
  if (!safeCode && !safeMsg) return "—";
  if (safeCode && safeMsg) return `${safeCode}: ${safeMsg}`;
  return safeCode || safeMsg;
}
