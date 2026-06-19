import type { PipelineStage, WorkItem } from "../../types/workflows";
import { formatCommonStatus, formatWorkItemType } from "../../i18n/ruUi";
import { WorkItemStageSelect } from "./WorkItemStageSelect";
import { formatDate } from "../../workspace/formatters";

interface CrmPipelineBoardProps {
  stages: PipelineStage[];
  workItems: WorkItem[];
  workItemLabel: string;
}

export function CrmPipelineBoard({ stages, workItems, workItemLabel }: CrmPipelineBoardProps) {
  const sortedStages = [...stages].sort((a, b) => a.sort_order - b.sort_order);

  const itemsByStage = new Map<string, WorkItem[]>();
  for (const stage of sortedStages) {
    itemsByStage.set(stage.id, []);
  }
  for (const item of workItems) {
    const bucket = itemsByStage.get(item.stage_id);
    if (bucket) {
      bucket.push(item);
    }
  }

  return (
    <div className="crm-pipeline-board">
      {sortedStages.map((stage) => {
        const items = itemsByStage.get(stage.id) ?? [];
        return (
          <section key={stage.id} className="crm-pipeline-column">
            <header className="crm-pipeline-column-header">
              <h3>{stage.name}</h3>
              <span className="crm-pipeline-count">{items.length}</span>
            </header>
            <div className="crm-pipeline-cards">
              {items.length === 0 ? (
                <p className="muted crm-pipeline-empty">Нет {workItemLabel.toLowerCase()}</p>
              ) : (
                items.map((item) => (
                  <article key={item.id} className="crm-pipeline-card">
                    <div className="crm-pipeline-card-title">{item.title}</div>
                    <div className="crm-pipeline-card-meta">
                      <span className={`badge badge-${item.status}`}>
                        {formatCommonStatus(item.status)}
                      </span>
                      <span className="muted">{formatWorkItemType(item.work_item_type)}</span>
                    </div>
                    <div className="crm-pipeline-card-date muted">
                      Обновлено: {formatDate(item.updated_at)}
                    </div>
                    <WorkItemStageSelect
                      workItem={item}
                      stages={stages}
                      compact
                    />
                  </article>
                ))
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}
