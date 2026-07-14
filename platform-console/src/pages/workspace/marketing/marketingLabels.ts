/**
 * RU labels for Marketing Cabinet statuses/channels.
 * Run tests: npx tsx src/pages/workspace/marketing/marketingLabels.test.ts
 */
import type {
  MarketingApprovalStatus,
  MarketingChannel,
  MarketingPackStatus,
  MarketingPreflightStatus,
  MarketingPublishStatus,
  MarketingTopicStatus,
} from "../../../types/marketing";

export const MARKETING_PUBLISH_DISABLED_MESSAGE =
  "Публикация пока выключена. Marketing Cabinet сейчас является source of truth для подготовки контента. Export/Margosya/publish будут отдельным этапом.";

const TOPIC_STATUS_LABELS: Record<MarketingTopicStatus, string> = {
  draft: "Черновик",
  approved: "Утверждена",
  used: "Использована",
  archived: "В архиве",
};

const PACK_STATUS_LABELS: Record<MarketingPackStatus, string> = {
  draft: "Черновик",
  preflight_failed: "Preflight с ошибками",
  ready_for_approval: "Готов к согласованию",
  approved: "Согласован",
  scheduled: "Запланирован",
  publishing: "Публикуется",
  published: "Опубликован",
  failed: "Ошибка публикации",
  archived: "В архиве",
};

const PREFLIGHT_STATUS_LABELS: Record<MarketingPreflightStatus, string> = {
  not_run: "Не запускался",
  passed: "Пройден",
  failed: "Не пройден",
};

const APPROVAL_STATUS_LABELS: Record<MarketingApprovalStatus, string> = {
  draft: "Черновик",
  pending: "Ожидает",
  approved: "Согласован",
  rejected: "Отклонён",
};

const PUBLISH_STATUS_LABELS: Record<MarketingPublishStatus, string> = {
  not_started: "Не начата",
  partial: "Частично",
  published: "Опубликован",
  failed: "Ошибка",
};

const CHANNEL_LABELS: Record<MarketingChannel, string> = {
  telegram: "Telegram",
  instagram: "Instagram",
  threads: "Threads",
  insights: "Insights",
};

export function marketingTopicStatusLabel(status: string): string {
  return TOPIC_STATUS_LABELS[status as MarketingTopicStatus] ?? status;
}

export function marketingPackStatusLabel(status: string): string {
  return PACK_STATUS_LABELS[status as MarketingPackStatus] ?? status;
}

export function marketingPreflightStatusLabel(status: string): string {
  return PREFLIGHT_STATUS_LABELS[status as MarketingPreflightStatus] ?? status;
}

export function marketingApprovalStatusLabel(status: string): string {
  return APPROVAL_STATUS_LABELS[status as MarketingApprovalStatus] ?? status;
}

export function marketingPublishStatusLabel(status: string): string {
  return PUBLISH_STATUS_LABELS[status as MarketingPublishStatus] ?? status;
}

export function marketingChannelLabel(channel: string): string {
  return CHANNEL_LABELS[channel as MarketingChannel] ?? channel;
}
