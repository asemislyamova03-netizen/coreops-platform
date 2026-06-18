import { useQueries } from "@tanstack/react-query";
import { listDocuments } from "../api/documents";
import { getFinanceSummary, listReceivables } from "../api/finance";
import { listPipelines, listWorkItems } from "../api/workflows";
import type { Document } from "../types/document";
import type { FinanceSummary, Receivable } from "../types/finance";
import type { Pipeline, WorkItem } from "../types/workflows";
import { pickDefaultPipeline } from "./formatters";

const EARLY_LEAD_STAGE_CODES = new Set(["new_lead", "first_contact"]);
const ACTIVE_STATUSES = new Set(["open", "in_progress"]);

export interface DashboardMetrics {
  pipeline: Pipeline | null;
  workItems: WorkItem[];
  financeSummary: FinanceSummary | null;
  receivables: Receivable[];
  documents: Document[];
  newLeadsCount: number;
  activeDealsCount: number;
  pendingDocumentsCount: number;
  overdueReceivablesCount: number;
}

function countNewLeads(pipeline: Pipeline | null, workItems: WorkItem[]): number {
  if (!pipeline) return 0;
  const stageCodes = new Map(pipeline.stages.map((s) => [s.id, s.code]));
  return workItems.filter((item) => {
    const code = stageCodes.get(item.stage_id);
    return code ? EARLY_LEAD_STAGE_CODES.has(code) : false;
  }).length;
}

function countActiveDeals(pipeline: Pipeline | null, workItems: WorkItem[]): number {
  if (!pipeline) return 0;
  const terminalStages = new Set(
    pipeline.stages.filter((s) => s.is_terminal).map((s) => s.id),
  );
  return workItems.filter(
    (item) =>
      ACTIVE_STATUSES.has(item.status) && !terminalStages.has(item.stage_id),
  ).length;
}

function countPendingDocuments(documents: Document[]): number {
  return documents.filter((doc) => {
    if (doc.status === "sent_for_review" || doc.status === "sent_for_signature") {
      return true;
    }
    return doc.signature_requests.some(
      (sig) => sig.status === "pending" || sig.status === "sent",
    );
  }).length;
}

export function useDashboardData(enabled: boolean) {
  const results = useQueries({
    queries: [
      {
        queryKey: ["workspace-dashboard-pipelines"],
        queryFn: listPipelines,
        enabled,
      },
      {
        queryKey: ["workspace-dashboard-finance-summary"],
        queryFn: () => getFinanceSummary(),
        enabled,
      },
      {
        queryKey: ["workspace-dashboard-receivables"],
        queryFn: listReceivables,
        enabled,
      },
      {
        queryKey: ["workspace-dashboard-documents"],
        queryFn: () => listDocuments({ limit: 200 }),
        enabled,
      },
    ],
  });

  const pipelinesQuery = results[0];
  const pipeline = pipelinesQuery.data ? pickDefaultPipeline(pipelinesQuery.data) : null;

  const workItemsQuery = useQueries({
    queries: [
      {
        queryKey: ["workspace-dashboard-work-items", pipeline?.id],
        queryFn: () => listWorkItems({ pipeline_id: pipeline!.id, limit: 200 }),
        enabled: enabled && Boolean(pipeline?.id),
      },
    ],
  })[0];

  const workItems = workItemsQuery.data ?? [];
  const documents = results[3].data ?? [];
  const receivables = results[2].data ?? [];
  const financeSummary = results[1].data ?? null;

  const metrics: DashboardMetrics = {
    pipeline,
    workItems,
    financeSummary,
    receivables,
    documents,
    newLeadsCount: countNewLeads(pipeline, workItems),
    activeDealsCount: countActiveDeals(pipeline, workItems),
    pendingDocumentsCount: countPendingDocuments(documents),
    overdueReceivablesCount: receivables.filter((r) => r.is_overdue).length,
  };

  const isLoading =
    pipelinesQuery.isLoading ||
    results[1].isLoading ||
    results[2].isLoading ||
    results[3].isLoading ||
    workItemsQuery.isLoading;

  const error =
    pipelinesQuery.error ??
    results[1].error ??
    results[2].error ??
    results[3].error ??
    workItemsQuery.error;

  return { metrics, isLoading, error };
}
