import type {
  ListMarketingPacksParams,
  ListMarketingTopicsParams,
  MarketingHealth,
  MarketingMediaAsset,
  MarketingMediaCreatePayload,
  MarketingMediaUpdatePayload,
  MarketingPackDetail,
  MarketingPackSummary,
  MarketingPackText,
  MarketingPreflightResponse,
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
