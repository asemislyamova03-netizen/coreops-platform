import { useMemo } from "react";
import { formatCommonStatus } from "../../i18n/ruUi";
import type { LeadSource } from "../../types/leadSources";
import type { PipelineStage, WorkItem } from "../../types/workflows";
import { Table } from "../ui/Table";
import { formatDate } from "../../workspace/formatters";
import {
  emptyTextForListView,
  filterWorkItemsForListView,
  sortWorkItemsByUpdatedAt,
  type CrmBoardViewMode,
  type CrmListStageFilter,
} from "../../workspace/crmPipelineBoardHelpers";
import {
  getDispositionLabel,
  readDisposition,
} from "../../workspace/leadDispositionHelpers";
import { resolveLeadSourceLabel } from "../../workspace/leadSourceHelpers";
import { WorkItemStageSelect } from "./WorkItemStageSelect";

interface CrmWorkItemsListViewProps {
  stages: PipelineStage[];
  workItems: WorkItem[];
  workItemLabel: string;
  boardView: CrmBoardViewMode;
  stageFilter: CrmListStageFilter;
  leadSources: LeadSource[];
  partyNameById?: Map<string, string>;
  onRowClick: (workItem: WorkItem) => void;
}

function stageName(stages: PipelineStage[], stageId: string): string {
  return stages.find((stage) => stage.id === stageId)?.name ?? "—";
}

export function CrmWorkItemsListView({
  stages,
  workItems,
  workItemLabel,
  boardView,
  stageFilter,
  leadSources,
  partyNameById,
  onRowClick,
}: CrmWorkItemsListViewProps) {
  const filteredItems = useMemo(
    () =>
      sortWorkItemsByUpdatedAt(
        filterWorkItemsForListView(workItems, stages, boardView, stageFilter),
      ),
    [workItems, stages, boardView, stageFilter],
  );

  const emptyText = emptyTextForListView(boardView, stageFilter, workItemLabel);

  return (
    <div className="crm-work-items-list">
      <Table
        data={filteredItems}
        emptyText={emptyText}
        rowKey={(item) => item.id}
        onRowClick={onRowClick}
        columns={[
          {
            key: "title",
            header: "Название",
            render: (item) => <span className="crm-list-title">{item.title}</span>,
          },
          {
            key: "contact",
            header: "Контакт",
            render: (item) => {
              const name = item.primary_party_id
                ? partyNameById?.get(item.primary_party_id)
                : undefined;
              return name ? <span>{name}</span> : <span className="muted">—</span>;
            },
          },
          {
            key: "source",
            header: "Источник",
            render: (item) => {
              const label = resolveLeadSourceLabel(leadSources, item.source);
              return label ? <span className="badge">{label}</span> : <span className="muted">—</span>;
            },
          },
          {
            key: "stage",
            header: "Стадия",
            render: (item) => stageName(stages, item.stage_id),
          },
          {
            key: "status",
            header: "Статус",
            render: (item) => (
              <span className={`badge badge-${item.status}`}>
                {formatCommonStatus(item.status)}
              </span>
            ),
          },
          {
            key: "disposition",
            header: "Причина",
            render: (item) => {
              const disposition = readDisposition(item.custom_fields);
              return disposition ? (
                <span className="badge">{getDispositionLabel(disposition)}</span>
              ) : (
                <span className="muted">—</span>
              );
            },
          },
          {
            key: "updated",
            header: "Обновлено",
            render: (item) => <span className="muted">{formatDate(item.updated_at)}</span>,
          },
          {
            key: "actions",
            header: "Действия",
            render: (item) => (
              <div
                className="crm-list-actions"
                onClick={(event) => event.stopPropagation()}
                onKeyDown={(event) => event.stopPropagation()}
              >
                <button
                  type="button"
                  className="btn btn-secondary crm-list-open-btn"
                  onClick={() => onRowClick(item)}
                >
                  Открыть
                </button>
                <WorkItemStageSelect workItem={item} stages={stages} compact />
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
