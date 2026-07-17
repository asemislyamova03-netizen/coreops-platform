export interface PipelineStage {
  id: string;
  code: string;
  name: string;
  sort_order: number;
  is_terminal: boolean;
}

export interface Pipeline {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  entity_type: string;
  is_default: boolean;
  stages: PipelineStage[];
  created_at: string;
}

export type WorkItemStatus =
  | "open"
  | "in_progress"
  | "won"
  | "lost"
  | "cancelled"
  | "archived";

export type DispositionCode =
  | "spam"
  | "off_topic"
  | "duplicate"
  | "test"
  | "no_response"
  | "other";

export interface WorkItemParticipant {
  id: string;
  party_id: string;
  role: string;
}

export type ActivityType =
  | "call"
  | "email"
  | "meeting"
  | "note"
  | "status_change"
  | "other";

export interface Activity {
  id: string;
  activity_type: ActivityType;
  title: string;
  description: string | null;
  occurred_at: string;
  created_by_user_id: string | null;
  created_at: string;
}

export interface WorkItemParticipantCreate {
  party_id: string;
  role?: "client" | "assignee" | "observer" | "other";
}

export interface WorkItemCreate {
  pipeline_id: string;
  stage_id?: string | null;
  work_item_type: string;
  title: string;
  description?: string | null;
  primary_party_id?: string | null;
  source?: string | null;
  participants?: WorkItemParticipantCreate[];
  custom_fields?: Record<string, unknown>;
}

export interface WorkItemUpdate {
  title?: string;
  description?: string | null;
  primary_party_id?: string | null;
  source?: string | null;
  stage_id?: string | null;
  custom_fields?: Record<string, unknown>;
}

export interface MoveStageRequest {
  stage_id: string;
}

export interface CloseWorkItemRequest {
  disposition: DispositionCode;
  disposition_note?: string | null;
}

export interface ReopenWorkItemRequest {
  note?: string | null;
}

export interface ActivityCreate {
  activity_type?: ActivityType;
  title: string;
  description?: string | null;
}

export interface TaskCreate {
  title: string;
  description?: string | null;
}

export interface WorkItem {
  id: string;
  tenant_id: string;
  pipeline_id: string;
  stage_id: string;
  work_item_type: string;
  title: string;
  description: string | null;
  primary_party_id: string | null;
  status: WorkItemStatus;
  amount: string | null;
  currency: string | null;
  source: string | null;
  custom_fields: Record<string, unknown>;
  participants: WorkItemParticipant[];
  activities?: Activity[];
  created_at: string;
  updated_at: string;
  created_by_user_id: string | null;
  updated_by_user_id: string | null;
}

export interface ListWorkItemsParams {
  pipeline_id?: string;
  stage_id?: string;
  status?: WorkItemStatus;
  work_item_type?: string;
  primary_party_id?: string;
  search?: string;
  skip?: number;
  limit?: number;
}
