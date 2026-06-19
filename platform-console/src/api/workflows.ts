import type {
  Activity,
  ActivityCreate,
  ListWorkItemsParams,
  MoveStageRequest,
  Pipeline,
  TaskCreate,
  WorkItem,
  WorkItemCreate,
  WorkItemUpdate,
} from "../types/workflows";
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
      primary_party_id: params.primary_party_id,
      search: params.search,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}

export function getWorkItem(workItemId: string): Promise<WorkItem> {
  return workspaceApiFetch<WorkItem>(`/work-items/${workItemId}`);
}

export function createWorkItem(payload: WorkItemCreate): Promise<WorkItem> {
  return workspaceApiFetch<WorkItem>("/work-items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateWorkItem(
  workItemId: string,
  payload: WorkItemUpdate,
): Promise<WorkItem> {
  return workspaceApiFetch<WorkItem>(`/work-items/${workItemId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function moveWorkItemStage(
  workItemId: string,
  payload: MoveStageRequest,
): Promise<WorkItem> {
  return workspaceApiFetch<WorkItem>(`/work-items/${workItemId}/move-stage`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createWorkItemActivity(
  workItemId: string,
  payload: ActivityCreate,
): Promise<Activity> {
  return workspaceApiFetch<Activity>(`/work-items/${workItemId}/activities`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createWorkItemTask(workItemId: string, payload: TaskCreate): Promise<unknown> {
  return workspaceApiFetch(`/work-items/${workItemId}/tasks`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
