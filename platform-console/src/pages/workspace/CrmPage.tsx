import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { listPipelines, listWorkItems } from "../../api/workflows";
import { ApiError } from "../../api/client";
import { CreateWorkItemModal } from "../../components/workspace/CreateWorkItemModal";
import { CrmPipelineBoard } from "../../components/workspace/CrmPipelineBoard";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { pickDefaultPipeline } from "../../workspace/formatters";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function CrmPage() {
  const { crmSectionTitle, entityLabel, isLoading: labelsLoading } = useWorkspaceLabels();
  const workItemLabel = entityLabel("work_item", "Заявка");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const pipelinesQuery = useQuery({
    queryKey: ["workspace-pipelines"],
    queryFn: listPipelines,
    enabled: !labelsLoading,
  });

  const pipeline = pipelinesQuery.data ? pickDefaultPipeline(pipelinesQuery.data) : null;

  const workItemsQuery = useQuery({
    queryKey: ["workspace-work-items", pipeline?.id],
    queryFn: () => listWorkItems({ pipeline_id: pipeline!.id, limit: 200 }),
    enabled: Boolean(pipeline?.id),
  });

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
        <PageHeader title="CRM" subtitle={crmSectionTitle} />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="page">
        <PageHeader title="CRM" subtitle={crmSectionTitle} />
        <Alert variant="info">
          Воронка не настроена. Примените industry template для tenant.
        </Alert>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title="CRM"
        subtitle={`${crmSectionTitle} · ${pipeline.name}`}
        action={
          <button type="button" className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            Создать заявку
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
          <CrmPipelineBoard
            stages={pipeline.stages}
            workItems={workItemsQuery.data}
            workItemLabel={workItemLabel}
          />
        </>
      )}

      {showCreateModal && (
        <CreateWorkItemModal
          defaultPipeline={pipeline}
          onClose={() => setShowCreateModal(false)}
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
