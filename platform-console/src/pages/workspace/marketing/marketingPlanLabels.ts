import type {
  MarketingContentPlanItemStatus,
  MarketingContentPlanStatus,
} from "../../../types/marketing";

export function marketingContentPlanStatusLabel(status: MarketingContentPlanStatus): string {
  switch (status) {
    case "draft":
      return "Черновик";
    case "approved":
      return "Утверждён";
    case "archived":
      return "В архиве";
    default:
      return status;
  }
}

export function marketingContentPlanItemStatusLabel(
  status: MarketingContentPlanItemStatus,
): string {
  switch (status) {
    case "draft":
      return "Черновик";
    case "approved":
      return "Утверждена";
    case "topic_created":
      return "Тема создана";
    case "cancelled":
      return "Отменена";
    default:
      return status;
  }
}

export const PLAN_CHANNEL_OPTIONS = [
  "telegram",
  "instagram",
  "threads",
  "insights",
] as const;
