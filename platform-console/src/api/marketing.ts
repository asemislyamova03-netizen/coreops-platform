import type {
  ListMarketingPacksParams,
  ListMarketingTopicsParams,
  MarketingContentPlan,
  MarketingContentPlanCreatePayload,
  MarketingContentPlanCreateTopicResponse,
  MarketingContentPlanImportCommitResponse,
  MarketingContentPlanImportPreviewResponse,
  MarketingContentPlanItem,
  MarketingContentPlanItemCreatePayload,
  MarketingContentPlanItemUpdatePayload,
  MarketingContentPlanPromptExportPayload,
  MarketingContentPlanPromptExportResponse,
  MarketingContentPlanStatus,
  MarketingGuide,
  MarketingGuideCreatePayload,
  MarketingGuideUpdatePayload,
  MarketingHealth,
  MarketingMediaAsset,
  MarketingMediaCreatePayload,
  MarketingMediaUpdatePayload,
  MarketingPackDetail,
  MarketingPackSummary,
  MarketingPackText,
  MarketingPreflightResponse,
  MarketingRubric,
  MarketingRubricCreatePayload,
  MarketingRubricSeedResponse,
  MarketingRubricStatus,
  MarketingRubricUpdatePayload,
  MarketingTakeTopicPackResponse,
  MarketingTakeTopicPayload,
  MarketingTopic,
  MarketingTopicCreatePayload,
  MarketingTopicUpdatePayload,
  PackTextUpsertPayload,
  MarketingChannel,
} from "../types/marketing";
import { buildQuery } from "./query";
import { workspaceApiFetch } from "./workspace";

export function getMarketingHealth(): Promise<MarketingHealth> {
  return workspaceApiFetch<MarketingHealth>("/marketing/health");
}

export function listMarketingTopics(
  params: ListMarketingTopicsParams = {},
): Promise<MarketingTopic[]> {
  return workspaceApiFetch<MarketingTopic[]>(
    `/marketing/topics${buildQuery({
      status: params.status,
      rubric: params.rubric,
      search: params.search,
      include_archived: params.include_archived ? "true" : undefined,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}

export function createMarketingTopic(
  payload: MarketingTopicCreatePayload,
): Promise<MarketingTopic> {
  return workspaceApiFetch<MarketingTopic>("/marketing/topics", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateMarketingTopic(
  topicId: string,
  payload: MarketingTopicUpdatePayload,
): Promise<MarketingTopic> {
  return workspaceApiFetch<MarketingTopic>(`/marketing/topics/${topicId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function takeMarketingTopic(
  topicId: string,
  payload: MarketingTakeTopicPayload = {},
): Promise<MarketingTakeTopicPackResponse> {
  return workspaceApiFetch<MarketingTakeTopicPackResponse>(
    `/marketing/topics/${topicId}/take`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function archiveMarketingTopic(topicId: string): Promise<MarketingTopic> {
  return workspaceApiFetch<MarketingTopic>(`/marketing/topics/${topicId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function markMarketingTopicUsed(topicId: string): Promise<MarketingTopic> {
  return workspaceApiFetch<MarketingTopic>(`/marketing/topics/${topicId}/mark-used`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function listMarketingPacks(
  params: ListMarketingPacksParams = {},
): Promise<MarketingPackSummary[]> {
  return workspaceApiFetch<MarketingPackSummary[]>(
    `/marketing/packs${buildQuery({
      status: params.status,
      topic_id: params.topic_id,
      planned_date: params.planned_date,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}

export function getMarketingPack(packId: string): Promise<MarketingPackDetail> {
  return workspaceApiFetch<MarketingPackDetail>(`/marketing/packs/${packId}`);
}

export function updateMarketingPackText(
  packId: string,
  channel: MarketingChannel,
  payload: PackTextUpsertPayload,
): Promise<MarketingPackText> {
  return workspaceApiFetch<MarketingPackText>(`/marketing/packs/${packId}/texts/${channel}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function listMarketingPackMedia(packId: string): Promise<MarketingMediaAsset[]> {
  return workspaceApiFetch<MarketingMediaAsset[]>(`/marketing/packs/${packId}/media`);
}

export function addMarketingPackMedia(
  packId: string,
  payload: MarketingMediaCreatePayload,
): Promise<MarketingMediaAsset> {
  return workspaceApiFetch<MarketingMediaAsset>(`/marketing/packs/${packId}/media`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateMarketingMedia(
  assetId: string,
  payload: MarketingMediaUpdatePayload,
): Promise<MarketingMediaAsset> {
  return workspaceApiFetch<MarketingMediaAsset>(`/marketing/media/${assetId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteMarketingMedia(assetId: string): Promise<MarketingMediaAsset> {
  return workspaceApiFetch<MarketingMediaAsset>(`/marketing/media/${assetId}`, {
    method: "DELETE",
  });
}

export function runMarketingPreflight(packId: string): Promise<MarketingPreflightResponse> {
  return workspaceApiFetch<MarketingPreflightResponse>(`/marketing/packs/${packId}/preflight`, {
    method: "POST",
    body: JSON.stringify({ strict: true }),
  });
}

export function approveMarketingPack(
  packId: string,
  note?: string,
): Promise<MarketingPackDetail> {
  return workspaceApiFetch<MarketingPackDetail>(`/marketing/packs/${packId}/approve`, {
    method: "POST",
    body: JSON.stringify(note ? { note } : {}),
  });
}

export function rejectMarketingPack(
  packId: string,
  reason?: string,
): Promise<MarketingPackDetail> {
  return workspaceApiFetch<MarketingPackDetail>(`/marketing/packs/${packId}/reject`, {
    method: "POST",
    body: JSON.stringify(reason ? { reason } : {}),
  });
}

export function getActiveMarketingGuide(): Promise<MarketingGuide> {
  return workspaceApiFetch<MarketingGuide>("/marketing/guides/active");
}

export function listMarketingGuides(): Promise<MarketingGuide[]> {
  return workspaceApiFetch<MarketingGuide[]>("/marketing/guides");
}

export function createMarketingGuide(
  payload: MarketingGuideCreatePayload,
): Promise<MarketingGuide> {
  return workspaceApiFetch<MarketingGuide>("/marketing/guides", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateMarketingGuide(
  guideId: string,
  payload: MarketingGuideUpdatePayload,
): Promise<MarketingGuide> {
  return workspaceApiFetch<MarketingGuide>(`/marketing/guides/${guideId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function activateMarketingGuide(guideId: string): Promise<MarketingGuide> {
  return workspaceApiFetch<MarketingGuide>(`/marketing/guides/${guideId}/activate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function listMarketingRubrics(params: {
  status?: MarketingRubricStatus;
  include_archived?: boolean;
} = {}): Promise<MarketingRubric[]> {
  return workspaceApiFetch<MarketingRubric[]>(
    `/marketing/rubrics${buildQuery({
      status: params.status,
      include_archived: params.include_archived ? "true" : undefined,
    })}`,
  );
}

export function createMarketingRubric(
  payload: MarketingRubricCreatePayload,
): Promise<MarketingRubric> {
  return workspaceApiFetch<MarketingRubric>("/marketing/rubrics", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateMarketingRubric(
  rubricId: string,
  payload: MarketingRubricUpdatePayload,
): Promise<MarketingRubric> {
  return workspaceApiFetch<MarketingRubric>(`/marketing/rubrics/${rubricId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function activateMarketingRubric(rubricId: string): Promise<MarketingRubric> {
  return workspaceApiFetch<MarketingRubric>(`/marketing/rubrics/${rubricId}/activate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function deactivateMarketingRubric(rubricId: string): Promise<MarketingRubric> {
  return workspaceApiFetch<MarketingRubric>(`/marketing/rubrics/${rubricId}/deactivate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function archiveMarketingRubric(rubricId: string): Promise<MarketingRubric> {
  return workspaceApiFetch<MarketingRubric>(`/marketing/rubrics/${rubricId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function seedMarketingRubricDefaults(
  force = false,
): Promise<MarketingRubricSeedResponse> {
  return workspaceApiFetch<MarketingRubricSeedResponse>("/marketing/rubrics/seed-defaults", {
    method: "POST",
    body: JSON.stringify({ force }),
  });
}

// --- M7.5 Content Plans ----------------------------------------------------

export function listMarketingContentPlans(params: {
  status?: MarketingContentPlanStatus;
  skip?: number;
  limit?: number;
} = {}): Promise<MarketingContentPlan[]> {
  return workspaceApiFetch<MarketingContentPlan[]>(
    `/marketing/content-plans${buildQuery({
      status: params.status,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}

export function getMarketingContentPlan(planId: string): Promise<MarketingContentPlan> {
  return workspaceApiFetch<MarketingContentPlan>(`/marketing/content-plans/${planId}`);
}

export function createMarketingContentPlan(
  payload: MarketingContentPlanCreatePayload,
): Promise<MarketingContentPlan> {
  return workspaceApiFetch<MarketingContentPlan>("/marketing/content-plans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function approveMarketingContentPlan(planId: string): Promise<MarketingContentPlan> {
  return workspaceApiFetch<MarketingContentPlan>(`/marketing/content-plans/${planId}/approve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function archiveMarketingContentPlan(planId: string): Promise<MarketingContentPlan> {
  return workspaceApiFetch<MarketingContentPlan>(`/marketing/content-plans/${planId}/archive`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function listMarketingContentPlanItems(
  planId: string,
): Promise<MarketingContentPlanItem[]> {
  return workspaceApiFetch<MarketingContentPlanItem[]>(
    `/marketing/content-plans/${planId}/items`,
  );
}

export function createMarketingContentPlanItem(
  planId: string,
  payload: MarketingContentPlanItemCreatePayload,
): Promise<MarketingContentPlanItem> {
  return workspaceApiFetch<MarketingContentPlanItem>(
    `/marketing/content-plans/${planId}/items`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function updateMarketingContentPlanItem(
  planId: string,
  itemId: string,
  payload: MarketingContentPlanItemUpdatePayload,
): Promise<MarketingContentPlanItem> {
  return workspaceApiFetch<MarketingContentPlanItem>(
    `/marketing/content-plans/${planId}/items/${itemId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}

export function cancelMarketingContentPlanItem(
  planId: string,
  itemId: string,
): Promise<MarketingContentPlanItem> {
  return workspaceApiFetch<MarketingContentPlanItem>(
    `/marketing/content-plans/${planId}/items/${itemId}/cancel`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export function createTopicFromContentPlanItem(
  planId: string,
  itemId: string,
): Promise<MarketingContentPlanCreateTopicResponse> {
  return workspaceApiFetch<MarketingContentPlanCreateTopicResponse>(
    `/marketing/content-plans/${planId}/items/${itemId}/create-topic`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export function exportMarketingContentPlanPrompt(
  payload: MarketingContentPlanPromptExportPayload,
): Promise<MarketingContentPlanPromptExportResponse> {
  return workspaceApiFetch<MarketingContentPlanPromptExportResponse>(
    "/marketing/content-plans/prompt-export",
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function previewMarketingContentPlanImport(payload: {
  plan: Record<string, unknown> | string;
  rubric_code_map?: Record<string, string>;
}): Promise<MarketingContentPlanImportPreviewResponse> {
  return workspaceApiFetch<MarketingContentPlanImportPreviewResponse>(
    "/marketing/content-plans/import/preview",
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function commitMarketingContentPlanImport(payload: {
  plan: Record<string, unknown> | string;
  rubric_code_map?: Record<string, string>;
}): Promise<MarketingContentPlanImportCommitResponse> {
  return workspaceApiFetch<MarketingContentPlanImportCommitResponse>(
    "/marketing/content-plans/import/commit",
    { method: "POST", body: JSON.stringify(payload) },
  );
}
