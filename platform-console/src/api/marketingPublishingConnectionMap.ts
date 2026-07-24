import type { MarketingPublishingConnection } from "../types/marketingPublishingConnection";

export const SAFE_PUBLISHING_CONNECTION_KEYS = [
  "id",
  "provider",
  "account_display_name",
  "status",
  "token_status",
  "has_secret",
  "expires_at",
  "last_checked_at",
  "last_error_code",
  "last_error_message_redacted",
] as const;

function asNullableString(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return null;
}

/** Map API row → safe FE view. Never copies vault/token fields into the typed object. */
export function toSafePublishingConnection(
  raw: Record<string, unknown>,
): MarketingPublishingConnection {
  return {
    id: String(raw.id ?? ""),
    provider: asNullableString(raw.provider) ?? "",
    account_display_name: asNullableString(raw.account_display_name) ?? "",
    status: asNullableString(raw.status) ?? "",
    token_status: asNullableString(raw.token_status) ?? "",
    has_secret: Boolean(raw.has_secret),
    expires_at: asNullableString(raw.expires_at),
    last_checked_at: asNullableString(raw.last_checked_at),
    last_error_code: asNullableString(raw.last_error_code),
    last_error_message_redacted: asNullableString(raw.last_error_message_redacted),
  };
}

export function connectionViewHasSensitiveKey(
  view: MarketingPublishingConnection,
  key: string,
): boolean {
  return Object.prototype.hasOwnProperty.call(view, key);
}
