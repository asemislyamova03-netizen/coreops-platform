import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { listParties } from "../../api/parties";
import { listPipelines, listWorkItems } from "../../api/workflows";
import { ApiError } from "../../api/client";
import { CreateWorkItemModal } from "../../components/workspace/CreateWorkItemModal";
import { CrmBoardViewSwitcher } from "../../components/workspace/CrmBoardViewSwitcher";
import { CrmCardDensitySwitcher } from "../../components/workspace/CrmCardDensitySwitcher";
import { CrmDisplayModeSwitcher } from "../../components/workspace/CrmDisplayModeSwitcher";
import { CrmPipelineBoard } from "../../components/workspace/CrmPipelineBoard";
import { CrmStageFilter } from "../../components/workspace/CrmStageFilter";
import { CrmWorkItemsListView } from "../../components/workspace/CrmWorkItemsListView";
import { LeadDetailModal } from "../../components/workspace/LeadDetailModal";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { ui } from "../../i18n/ruUi";
import type {
  CrmBoardViewMode,
  CrmCardDensity,
  CrmDisplayMode,
  CrmListStageFilter,
} from "../../workspace/crmPipelineBoardHelpers";
import {
  readCardDensity,
  readDisplayMode,
  resolveListStageFilter,
  writeCardDensity,
  writeDisplayMode,
  writeListStageFilter,
} from "../../workspace/crmPipelineBoardHelpers";
import { pickDefaultPipeline } from "../../workspace/formatters";
import { useLeadSources } from "../../workspace/useLeadSources";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";
import { useTenantWorkspace } from "../../auth/TenantWorkspaceContext";

export function CrmPage() {
  const { tenant } = useTenantWorkspace();
  const { crmSectionTitle, entityLabel, isLoading: labelsLoading } = useWorkspaceLabels();
  const { sources: leadSources } = useLeadSources(tenant?.tenantId ?? null);
  const workItemLabel = entityLabel("work_item", "Заявка");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedWorkItemId, setSelectedWorkItemId] = useState<string | null>(null);
  const [boardView, setBoardView] = useState<CrmBoardViewMode>("active");
  const [displayMode, setDisplayMode] = useState<CrmDisplayMode>(() => readDisplayMode());
  const [cardDensity, setCardDensity] = useState<CrmCardDensity>(() => readCardDensity());
  const [listStageFilter, setListStageFilter] = useState<CrmListStageFilter>("all");
  const [closeNotice, setCloseNotice] = useState(false);

  const pipelinesQuery = useQuery({
    queryKey: ["workspace-pipelines"],
    queryFn: listPipelines,
    enabled: !labelsLoading,
  });

  const pipeline = pipelinesQuery.data ? pickDefaultPipeline(pipelinesQuery.data) : null;

  useEffect(() => {
    if (!pipeline) {
      return;
    }
    const resolved = resolveListStageFilter(pipeline.stages);
    setListStageFilter(resolved);
    writeListStageFilter(resolved);
  }, [pipeline?.id]);

  const workItemsQuery = useQuery({
    queryKey: ["workspace-work-items", pipeline?.id],
    queryFn: () => listWorkItems({ pipeline_id: pipeline!.id, limit: 200 }),
    enabled: Boolean(pipeline?.id),
  });

  const partiesQuery = useQuery({
    queryKey: ["workspace-parties", "crm-board"],
    queryFn: () => listParties({ limit: 200 }),
    enabled: Boolean(pipeline?.id) && !labelsLoading,
  });

  const partyNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const party of partiesQuery.data ?? []) {
      map.set(party.id, party.display_name);
    }
    return map;
  }, [partiesQuery.data]);

  if (labelsLoading || pipelinesQuery.isLoading) {
    return <Loading text="Загрузка CRM..." />;
  }

  if (pipelinesQuery.error) {
    const message =
      pipelinesQuery.error instanceof ApiError
        ? pipelinesQuery.error.message
        : "Не удалось загрузить воронки.";
    return (
      <div className="page">
        <PageHeader title={ui.crm} subtitle={crmSectionTitle} />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="page">
        <PageHeader title={ui.crm} subtitle={crmSectionTitle} />
        <Alert variant="info">
          Воронка не настроена. Примените отраслевой шаблон для организации.
        </Alert>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title={ui.crm}
        subtitle={`${crmSectionTitle} · ${pipeline.name}`}
        action={
          <button type="button" className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            Создать {workItemLabel.toLowerCase()}
          </button>
        }
      />

      {workItemsQuery.isLoading && <Loading text={`Загрузка ${workItemLabel.toLowerCase()}...`} />}

      {workItemsQuery.error && (
        <Alert variant="error">
          {workItemsQuery.error instanceof ApiError
            ? workItemsQuery.error.message
            : `Не удалось загрузить ${workItemLabel.toLowerCase()}.`}
        </Alert>
      )}

      {workItemsQuery.isSuccess && (
        <>
          {workItemsQuery.data.length === 0 && (
            <Alert variant="info">
              Пока нет {workItemLabel.toLowerCase()} в воронке «{pipeline.name}».
            </Alert>
          )}

          {workItemsQuery.data.length > 0 && (
            <div className="crm-board-controls">
              <CrmDisplayModeSwitcher
                value={displayMode}
                onChange={(nextMode) => {
                  setDisplayMode(nextMode);
                  writeDisplayMode(nextMode);
                }}
              />
              <CrmBoardViewSwitcher
                value={boardView}
                onChange={(nextView) => {
                  setBoardView(nextView);
                  if (nextView === "closed") {
                    setCloseNotice(false);
                  }
                }}
              />
              {displayMode === "board" && (
                <CrmCardDensitySwitcher
                  value={cardDensity}
                  onChange={(nextDensity) => {
                    setCardDensity(nextDensity);
                    writeCardDensity(nextDensity);
                  }}
                />
              )}
              {displayMode === "list" && (
                <CrmStageFilter
                  stages={pipeline.stages}
                  value={listStageFilter}
                  onChange={(nextFilter) => {
                    setListStageFilter(nextFilter);
                    writeListStageFilter(nextFilter);
                  }}
                />
              )}
            </div>
          )}

          {closeNotice && (
            <Alert variant="info">
              Лид закрыт и перемещён в Закрытые.{" "}
              <button
                type="button"
                className="btn btn-secondary crm-board-close-notice-btn"
                onClick={() => {
                  setBoardView("closed");
                  setCloseNotice(false);
                }}
              >
                Открыть закрытые
              </button>
            </Alert>
          )}

          {displayMode === "list" && (
            <CrmWorkItemsListView
              stages={pipeline.stages}
              workItems={workItemsQuery.data}
              workItemLabel={workItemLabel}
              boardView={boardView}
              stageFilter={listStageFilter}
              leadSources={leadSources}
              partyNameById={partyNameById}
              onRowClick={(item) => setSelectedWorkItemId(item.id)}
            />
          )}
          {displayMode === "board" && (
            <CrmPipelineBoard
              stages={pipeline.stages}
              workItems={workItemsQuery.data}
              workItemLabel={workItemLabel}
              boardView={boardView}
              cardDensity={cardDensity}
              leadSources={leadSources}
              partyNameById={partyNameById}
              onCardClick={(item) => setSelectedWorkItemId(item.id)}
            />
          )}
        </>
      )}

      {showCreateModal && (
        <CreateWorkItemModal
          defaultPipeline={pipeline}
          onClose={() => setShowCreateModal(false)}
        />
      )}

      {selectedWorkItemId && (
        <LeadDetailModal
          key={selectedWorkItemId}
          workItemId={selectedWorkItemId}
          pipeline={pipeline}
          leadSources={leadSources}
          onClose={() => setSelectedWorkItemId(null)}
          onOpenWorkItem={setSelectedWorkItemId}
          onWorkItemClosed={() => {
            setSelectedWorkItemId(null);
            setCloseNotice(true);
          }}
          onWorkItemReopened={() => {
            setBoardView("active");
            setCloseNotice(false);
          }}
        />
      )}
    </div>
  );
}

function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-header workspace-page-header-with-action">
      <div>
        <h1>{title}</h1>
        <p className="muted">{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
