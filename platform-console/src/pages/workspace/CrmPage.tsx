import { useQuery } from "@tanstack/react-query";
import { listPipelines, listWorkItems } from "../../api/workflows";
import { ApiError } from "../../api/client";
import { CrmPipelineBoard } from "../../components/workspace/CrmPipelineBoard";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

function pickPipeline(pipelines: Awaited<ReturnType<typeof listPipelines>>) {
  if (pipelines.length === 0) return null;
  return pipelines.find((p) => p.is_default) ?? pipelines[0];
}

export function CrmPage() {
  const { crmSectionTitle, entityLabel, isLoading: labelsLoading } = useWorkspaceLabels();
  const workItemLabel = entityLabel("work_item", "Заявка");
  const pipelineLabel = entityLabel("pipeline", "Воронка");

  const pipelinesQuery = useQuery({
    queryKey: ["workspace-pipelines"],
    queryFn: listPipelines,
    enabled: !labelsLoading,
  });

  const pipeline = pipelinesQuery.data ? pickPipeline(pipelinesQuery.data) : null;

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
          {pipelineLabel} не настроена. Примените industry template для tenant.
        </Alert>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title="CRM"
        subtitle={`${crmSectionTitle} · ${pipeline.name}`}
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
              Пока нет {workItemLabel.toLowerCase()} в воронке «{pipeline.name}». Создание заявок —
              в W3.
            </Alert>
          )}
          <CrmPipelineBoard
            stages={pipeline.stages}
            workItems={workItemsQuery.data}
            workItemLabel={workItemLabel}
          />
        </>
      )}
    </div>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        <p className="muted">{subtitle}</p>
      </div>
    </div>
  );
}
