/**
 * Safe view for Marketing publishing connections (M8-B).
 * Vault material and provider tokens stay off this type on purpose.
 */

export type PublishingConnectionProvider =
  | "telegram"
  | "instagram"
  | "threads"
  | "tiktok";

export type PublishingConnectionStatus =
  | "not_connected"
  | "active"
  | "error"
  | "disabled"
  | "expired";

export type PublishingTokenStatus =
  | "not_configured"
  | "valid"
  | "expiring"
  | "invalid";

export type MarketingPublishingConnection = {
  id: string;
  provider: PublishingConnectionProvider | string;
  account_display_name: string;
  status: PublishingConnectionStatus | string;
  token_status: PublishingTokenStatus | string;
  has_secret: boolean;
  expires_at: string | null;
  last_checked_at: string | null;
  last_error_code: string | null;
  last_error_message_redacted: string | null;
};
