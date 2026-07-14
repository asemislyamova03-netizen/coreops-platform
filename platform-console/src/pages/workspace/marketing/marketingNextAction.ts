/**
 * Next-action resolver for Marketing pack detail workflow.
 * Run tests: npx tsx src/pages/workspace/marketing/marketingNextAction.test.ts
 */
import {
  MARKETING_PUBLISH_DISABLED_MESSAGE,
} from "./marketingLabels";

export type MarketingNextActionId =
  | "fill_texts"
  | "add_media"
  | "run_preflight"
  | "fix_preflight"
  | "approve"
  | "publish_disabled"
  | "fix_rejected";

export interface MarketingNextActionInput {
  status: string;
  approval_status: string;
  preflight_status: string;
  texts: Array<{ text: string }>;
  media_assets: Array<{ status: string }>;
}

export interface MarketingNextAction {
  id: MarketingNextActionId;
  message: string;
  tabHint?: "texts" | "media" | "preflight" | "approval" | "publish";
}

function hasNonEmptyText(texts: Array<{ text: string }>): boolean {
  return texts.some((row) => row.text.trim().length > 0);
}

function hasActiveMedia(media: Array<{ status: string }>): boolean {
  return media.some((asset) => asset.status !== "archived");
}

export function resolveMarketingNextAction(
  pack: MarketingNextActionInput,
): MarketingNextAction {
  if (pack.approval_status === "rejected") {
    return {
      id: "fix_rejected",
      message: "Исправьте замечания и снова запустите preflight.",
      tabHint: "texts",
    };
  }

  if (pack.approval_status === "approved" || pack.status === "approved") {
    return {
      id: "publish_disabled",
      message: `Пак готов. ${MARKETING_PUBLISH_DISABLED_MESSAGE}`,
      tabHint: "publish",
    };
  }

  if (!hasNonEmptyText(pack.texts)) {
    return {
      id: "fill_texts",
      message: "Заполните тексты для каналов.",
      tabHint: "texts",
    };
  }

  if (!hasActiveMedia(pack.media_assets)) {
    return {
      id: "add_media",
      message: "Добавьте медиа или укажите, что медиа не требуется.",
      tabHint: "media",
    };
  }

  if (pack.preflight_status === "failed" || pack.status === "preflight_failed") {
    return {
      id: "fix_preflight",
      message: "Исправьте ошибки preflight.",
      tabHint: "preflight",
    };
  }

  if (pack.preflight_status !== "passed") {
    return {
      id: "run_preflight",
      message: "Запустите preflight.",
      tabHint: "preflight",
    };
  }

  if (
    pack.status === "ready_for_approval" ||
    pack.approval_status === "pending" ||
    pack.approval_status === "draft"
  ) {
    return {
      id: "approve",
      message: "Можно отправить на approval.",
      tabHint: "approval",
    };
  }

  return {
    id: "approve",
    message: "Можно отправить на approval.",
    tabHint: "approval",
  };
}
