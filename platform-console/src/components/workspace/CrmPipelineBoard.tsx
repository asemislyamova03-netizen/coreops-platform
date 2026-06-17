import type { PipelineStage, WorkItem } from "../../types/workflows";

interface CrmPipelineBoardProps {
  stages: PipelineStage[];
  workItems: WorkItem[];
  workItemLabel: string;
}

function formatDate(value: string): string {
  try {
    return new Date(value).toLocaleDateString("ru-RU");
  } catch {
    return value;
  }
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
                      <span className={`badge badge-${item.status}`}>{item.status}</span>
                      <span className="muted">{item.work_item_type}</span>
                    </div>
                    <div className="crm-pipeline-card-date muted">
                      Обновлено: {formatDate(item.updated_at)}
                    </div>
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
