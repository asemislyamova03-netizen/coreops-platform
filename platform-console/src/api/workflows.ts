import type { ListWorkItemsParams, Pipeline, WorkItem } from "../types/workflows";
import { buildQuery } from "./query";
import { workspaceApiFetch } from "./workspace";

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
