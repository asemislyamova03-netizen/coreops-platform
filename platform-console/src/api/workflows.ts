import type { ListWorkItemsParams, Pipeline, WorkItem } from "../types/workflows";
import { workspaceApiFetch } from "./workspace";

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function listPipelines(): Promise<Pipeline[]> {
  return workspaceApiFetch<Pipeline[]>("/pipelines");
}

export function listWorkItems(params: ListWorkItemsParams = {}): Promise<WorkItem[]> {
  return workspaceApiFetch<WorkItem[]>(
    `/work-items${buildQuery({
      pipeline_id: params.pipeline_id,
      stage_id: params.stage_id,
      status: params.status,
      work_item_type: params.work_item_type,
      search: params.search,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}
