import type { PipelineStage, WorkItem } from "../../types/workflows";

import { formatCommonStatus, formatWorkItemType } from "../../i18n/ruUi";

import { resolveLeadSourceLabel } from "../../workspace/leadSourceHelpers";

import { getDispositionLabel, readDisposition } from "../../workspace/leadDispositionHelpers";

import type { LeadSource } from "../../types/leadSources";

import { WorkItemStageSelect } from "./WorkItemStageSelect";

import { formatDate } from "../../workspace/formatters";
import {
  groupWorkItemsByStage,
  splitPipelineStages,
  shouldShowActiveBoardSection,
  shouldShowTerminalBoardSection,
  type CrmBoardViewMode,
  type CrmCardDensity,
} from "../../workspace/crmPipelineBoardHelpers";
import { Alert } from "../ui/Alert";

interface CrmPipelineBoardProps {
  stages: PipelineStage[];
  workItems: WorkItem[];
  workItemLabel: string;
  boardView: CrmBoardViewMode;
  cardDensity: CrmCardDensity;
  leadSources?: LeadSource[];
  partyNameById?: Map<string, string>;
  onCardClick?: (workItem: WorkItem) => void;
}

function PipelineColumns({
  stages,
  allStages,
  itemsByStage,
  workItemLabel,
  leadSources,
  cardDensity,
  partyNameById,
  onCardClick,
}: {
  stages: PipelineStage[];
  allStages: PipelineStage[];
  itemsByStage: Map<string, WorkItem[]>;
  workItemLabel: string;
  leadSources: LeadSource[];
  cardDensity: CrmCardDensity;
  partyNameById?: Map<string, string>;
  onCardClick?: (workItem: WorkItem) => void;
}) {
  const isCompact = cardDensity === "compact";
  return (
    <>
      {stages.map((stage) => {
        const items = itemsByStage.get(stage.id) ?? [];

        return (
          <section
            key={stage.id}
            className="crm-pipeline-column"
            data-stage-code={stage.code}
            data-stage-terminal={stage.is_terminal ? "true" : "false"}
          >
            <header className="crm-pipeline-column-header">
              <h3>{stage.name}</h3>
              <span className="crm-pipeline-count">{items.length}</span>
            </header>

            <div className="crm-pipeline-cards">
              {items.length === 0 ? (
                <p className="muted crm-pipeline-empty">Нет {workItemLabel.toLowerCase()}</p>
              ) : (
                items.map((item) => {
                  const sourceLabel = resolveLeadSourceLabel(leadSources, item.source);
                  const disposition =
                    stage.code === "rejected" ? readDisposition(item.custom_fields) : null;
                  const dispositionLabel = disposition ? getDispositionLabel(disposition) : null;
                  const contactName = item.primary_party_id
                    ? partyNameById?.get(item.primary_party_id)
                    : undefined;
                  const isClickable = Boolean(onCardClick);

                  return (
                    <article
                      key={item.id}
                      className={`crm-pipeline-card${isClickable ? " crm-pipeline-card--clickable" : ""}`}
                    >
                      <div
                        className="crm-pipeline-card-body"
                        role={isClickable ? "button" : undefined}
                        tabIndex={isClickable ? 0 : undefined}
                        onClick={isClickable ? () => onCardClick?.(item) : undefined}
                        onKeyDown={
                          isClickable
                            ? (event) => {
                                if (event.key === "Enter" || event.key === " ") {
                                  event.preventDefault();
                                  onCardClick?.(item);
                                }
                              }
                            : undefined
                        }
                      >
                        <div className="crm-pipeline-card-title">{item.title}</div>
                        {contactName && (
                          <div className="crm-pipeline-card-contact muted">{contactName}</div>
                        )}
                        <div className="crm-pipeline-card-meta">
                          <span className={`badge badge-${item.status}`}>
                            {formatCommonStatus(item.status)}
                          </span>
                          {!isCompact && (
                            <span className="muted">{formatWorkItemType(item.work_item_type)}</span>
                          )}
                          {sourceLabel && <span className="badge">{sourceLabel}</span>}
                          {dispositionLabel && <span className="badge">{dispositionLabel}</span>}
                        </div>
                        {!isCompact && (
                          <div className="crm-pipeline-card-date muted">
                            Обновлено: {formatDate(item.updated_at)}
                          </div>
                        )}
                      </div>
                      <div
                        className="crm-pipeline-card-actions"
                        onClick={(event) => event.stopPropagation()}
                        onKeyDown={(event) => event.stopPropagation()}
                      >
                        <WorkItemStageSelect workItem={item} stages={allStages} compact />
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </section>
        );
      })}
    </>
  );
}

export function CrmPipelineBoard({
  stages,
  workItems,
  workItemLabel,
  boardView,
  cardDensity,
  leadSources = [],
  partyNameById,
  onCardClick,
}: CrmPipelineBoardProps) {
  const { activeStages, terminalStages } = splitPipelineStages(stages);
  const { byStageId, orphans } = groupWorkItemsByStage(stages, workItems);
  const showActive = shouldShowActiveBoardSection(boardView);
  const showTerminal = shouldShowTerminalBoardSection(boardView);
  const visibleItemCount = [...byStageId.entries()].reduce((count, [stageId, items]) => {
    const stage = stages.find((entry) => entry.id === stageId);
    if (!stage) {
      return count;
    }
    if (stage.is_terminal && !showTerminal) {
      return count;
    }
    if (!stage.is_terminal && !showActive) {
      return count;
    }
    return count + items.length;
  }, 0);

  return (
    <div
      className={`crm-pipeline-board-wrapper${
        cardDensity === "compact" ? " crm-pipeline-board-wrapper--compact" : ""
      }`}
    >
      {orphans.length > 0 && (
        <Alert variant="info">
          {orphans.length} {workItemLabel.toLowerCase()} не привязаны к видимым колонкам воронки.
        </Alert>
      )}

      {visibleItemCount === 0 && (
        <Alert variant="info">
          {boardView === "active"
            ? `Нет активных ${workItemLabel.toLowerCase()} в воронке.`
            : boardView === "closed"
              ? `Нет закрытых ${workItemLabel.toLowerCase()}.`
              : `Нет ${workItemLabel.toLowerCase()} в выбранном виде.`}
        </Alert>
      )}

      {showActive && activeStages.length > 0 && (
        <div className="crm-pipeline-board crm-pipeline-board--active">
          <PipelineColumns
            stages={activeStages}
            allStages={stages}
            itemsByStage={byStageId}
            workItemLabel={workItemLabel}
            leadSources={leadSources}
            cardDensity={cardDensity}
            partyNameById={partyNameById}
            onCardClick={onCardClick}
          />
        </div>
      )}

      {showTerminal && terminalStages.length > 0 && (
        <div className="crm-pipeline-terminal-section">
          {boardView === "all" && (
            <h3 className="crm-pipeline-terminal-title">Закрытые и финальные стадии</h3>
          )}
          <div className="crm-pipeline-board crm-pipeline-board--terminal">
            <PipelineColumns
              stages={terminalStages}
              allStages={stages}
              itemsByStage={byStageId}
              workItemLabel={workItemLabel}
              leadSources={leadSources}
              cardDensity={cardDensity}
              partyNameById={partyNameById}
              onCardClick={onCardClick}
            />
          </div>
        </div>
      )}
    </div>
  );
}
