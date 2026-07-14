export type MarketingTopicStatus = "draft" | "approved" | "used" | "archived";

export type MarketingPackStatus =
  | "draft"
  | "preflight_failed"
  | "ready_for_approval"
  | "approved"
  | "scheduled"
  | "publishing"
  | "published"
  | "failed"
  | "archived";

export type MarketingPreflightStatus = "not_run" | "passed" | "failed";

export type MarketingApprovalStatus = "draft" | "pending" | "approved" | "rejected";

export type MarketingPublishStatus = "not_started" | "partial" | "published" | "failed";

export type MarketingChannel = "telegram" | "instagram" | "threads" | "insights";

export const MARKETING_CHANNELS: MarketingChannel[] = [
  "telegram",
  "instagram",
  "threads",
  "insights",
];

export interface MarketingHealth {
  status: string;
  module: string;
}

export interface MarketingTopic {
  id: string;
  tenant_id: string;
  legacy_topic_id: string | null;
  title: string;
  rubric: string;
  angle: string | null;
  source: string;
  status: MarketingTopicStatus;
  priority: number;
  reusable: boolean;
  recommended_channels: string[];
  used_count: number;
  last_used_at: string | null;
  slug_hint: string | null;
  metadata_json: Record<string, unknown>;
  audience?: string | null;
  pain?: string | null;
  insight?: string | null;
  source_ref?: string | null;
  cta?: string | null;
  funnel_stage?: string | null;
  notes?: string | null;
  planned_date?: string | null;
  created_at: string;
  updated_at: string;
  duplicate_status?: "ok" | "warning" | "blocked" | null;
  duplicate_detail?: string | null;
}

export interface MarketingTopicSummaryInPack {
  id: string;
  legacy_topic_id: string | null;
  title: string;
  rubric: string;
  status: MarketingTopicStatus;
  angle?: string | null;
  priority?: number;
  audience?: string | null;
  pain?: string | null;
  insight?: string | null;
  source_ref?: string | null;
  cta?: string | null;
  funnel_stage?: string | null;
  notes?: string | null;
  planned_date?: string | null;
}

export interface MarketingPackSummary {
  id: string;
  tenant_id: string;
  topic_id: string | null;
  slug: string;
  pack_dir_name: string | null;
  title: string;
  planned_date: string;
  status: MarketingPackStatus;
  preflight_status: MarketingPreflightStatus;
  approval_status: MarketingApprovalStatus;
  publish_status: MarketingPublishStatus;
  source: string;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  topic: MarketingTopicSummaryInPack | null;
}

export interface MarketingPackDetail extends MarketingPackSummary {
  campaign_id: string | null;
  plan_item_id: string | null;
  preflight_at: string | null;
  /** Stored last preflight report (M6 or M7-C1 v2). Optional until backend deploy. */
  preflight_report_json?: Record<string, unknown>;
  approved_at: string | null;
  approved_by_user_id: string | null;
  channel_config_json: Record<string, unknown>;
  legacy_git_path: string | null;
  metadata_json: Record<string, unknown>;
  texts: MarketingPackText[];
  media_assets: MarketingMediaAsset[];
  publish_logs: Array<{
    id: string;
    channel: string;
    action: string;
    status: string;
    published_at: string | null;
    created_at: string;
  }>;
}

export interface MarketingPackText {
  id: string;
  channel: MarketingChannel | string;
  text: string;
  status: string;
  char_count: number;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface MarketingMediaAsset {
  id: string;
  role: string;
  file_name: string;
  mime_type: string;
  storage_provider: string;
  storage_key: string;
  public_url: string | null;
  preview_url: string | null;
  width: number | null;
  height: number | null;
  alt_text: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PackTextUpsertPayload {
  text: string;
  status?: string;
}

export interface MarketingMediaCreatePayload {
  file_name: string;
  mime_type: string;
  storage_provider: string;
  storage_key: string;
  preview_url?: string;
  width?: number;
  height?: number;
  role?: string;
  public_url?: string;
  alt_text?: string;
}

export interface MarketingMediaUpdatePayload {
  file_name?: string;
  mime_type?: string;
  storage_provider?: string;
  storage_key?: string;
  preview_url?: string;
  width?: number;
  height?: number;
  role?: string;
  public_url?: string;
  alt_text?: string;
}

export interface MarketingPreflightIssue {
  code: string;
  message: string;
  channel?: string | null;
}

export interface MarketingPreflightCheck {
  code: string;
  passed: boolean;
  message?: string | null;
  channel?: string | null;
}

/** M7-C1 topic_context_summary (additive). */
export interface MarketingPreflightTopicContextSummary {
  topic_id?: string;
  title?: string | null;
  status?: string | null;
  audience?: string | null;
  pain?: string | null;
  insight?: string | null;
  source_ref?: string | null;
  cta?: string | null;
  funnel_stage?: string | null;
  notes?: string | null;
  planned_date?: string | null;
  has_audience?: boolean;
  has_pain?: boolean;
  has_insight?: boolean;
  has_source_ref?: boolean;
  has_cta?: boolean;
  has_notes?: boolean;
  has_planned_date?: boolean;
}

export interface MarketingPreflightChannelCheck {
  channel: string;
  present: boolean;
  length: number;
  short_warn?: boolean;
  below_blocker_threshold?: boolean;
}

export interface MarketingPreflightMediaChecks {
  count: number;
  missing: boolean;
}

export interface MarketingPreflightResponse {
  pack_id: string;
  status: "passed" | "failed" | "warning";
  checked_at: string;
  errors: MarketingPreflightIssue[];
  warnings: MarketingPreflightIssue[];
  checks: MarketingPreflightCheck[];
  channel_eligibility: Record<string, boolean>;
  pack_status: MarketingPackStatus;
  preflight_status: MarketingPreflightStatus;
  approval_status: MarketingApprovalStatus;
  /** M7-C1 report v2 (optional for M6 compatibility). */
  version?: string;
  passed?: boolean;
  blockers?: MarketingPreflightIssue[];
  checklist?: MarketingPreflightCheck[];
  topic_context_summary?: MarketingPreflightTopicContextSummary | null;
  channel_checks?: MarketingPreflightChannelCheck[];
  media_checks?: MarketingPreflightMediaChecks;
}

export interface ListMarketingTopicsParams {
  status?: MarketingTopicStatus;
  rubric?: string;
  search?: string;
  include_archived?: boolean;
  skip?: number;
  limit?: number;
}

export interface ListMarketingPacksParams {
  status?: MarketingPackStatus;
  topic_id?: string;
  planned_date?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface MarketingTopicCreatePayload {
  title: string;
  rubric: string;
  angle?: string;
  source?: string;
  status?: MarketingTopicStatus;
  priority?: number;
  reusable?: boolean;
  recommended_channels?: string[];
  slug_hint?: string;
  metadata_json?: Record<string, unknown>;
  audience?: string;
  pain?: string;
  insight?: string;
  source_ref?: string;
  cta?: string;
  funnel_stage?: string;
  notes?: string;
  planned_date?: string;
}

export interface MarketingTopicUpdatePayload {
  title?: string;
  rubric?: string;
  angle?: string | null;
  source?: string;
  status?: MarketingTopicStatus;
  priority?: number;
  reusable?: boolean;
  recommended_channels?: string[];
  slug_hint?: string | null;
  metadata_json?: Record<string, unknown>;
  audience?: string | null;
  pain?: string | null;
  insight?: string | null;
  source_ref?: string | null;
  cta?: string | null;
  funnel_stage?: string | null;
  notes?: string | null;
  planned_date?: string | null;
}

export interface MarketingTakeTopicPayload {
  planned_date?: string;
  slug?: string;
  source?: string;
}

export interface MarketingTakeTopicPackText {
  id: string;
  channel: MarketingChannel | string;
  text: string;
  status: string;
  char_count: number;
  version: number;
}

export interface MarketingTakeTopicPackResponse {
  id: string;
  tenant_id: string;
  topic_id: string | null;
  slug: string;
  pack_dir_name: string | null;
  title: string;
  planned_date: string;
  status: string;
  approval_status: string;
  publish_status: string;
  source: string;
  texts: MarketingTakeTopicPackText[];
}
