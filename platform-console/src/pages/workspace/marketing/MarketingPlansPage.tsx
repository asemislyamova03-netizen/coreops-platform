import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  createMarketingContentPlan,
  listMarketingContentPlans,
} from "../../../api/marketing";
import { ApiError } from "../../../api/client";
import { Alert } from "../../../components/ui/Alert";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Loading } from "../../../components/ui/Loading";
import { Table } from "../../../components/ui/Table";
import { ui } from "../../../i18n/ruUi";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import {
  firstBlockingError,
  isModuleDisabled,
  moduleDisabledMessage,
} from "../../../workspace/moduleErrors";
import { formatMarketingApiError } from "./packDetail/marketingErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";
import { marketingContentPlanStatusLabel } from "./marketingPlanLabels";

export function MarketingPlansPage() {
  const { tenantSlug = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isLoading: labelsLoading } = useWorkspaceLabels();
  const base = `/workspace/${tenantSlug}/marketing`;

  const [title, setTitle] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const plansQuery = useQuery({
    queryKey: ["marketing-content-plans"],
    queryFn: () => listMarketingContentPlans({ limit: 100 }),
    enabled: !labelsLoading,
  });

  const createMutation = useMutation({
    mutationFn: createMarketingContentPlan,
    onSuccess: async (plan) => {
      setFormError(null);
      setTitle("");
      setPeriodStart("");
      setPeriodEnd("");
      await queryClient.invalidateQueries({ queryKey: ["marketing-content-plans"] });
      navigate(`${base}/plans/${plan.id}`);
    },
    onError: (error) => {
      setFormError(formatMarketingApiError(error, "Не удалось создать план."));
    },
  });

  if (labelsLoading || plansQuery.isLoading) {
    return <Loading text="Загрузка контент-планов..." />;
  }

  const marketingDisabled = isModuleDisabled("marketing", plansQuery.error);
  const blocking = firstBlockingError(plansQuery.error);
  if (marketingDisabled && !blocking) {
    return (
      <div className="page">
        <MarketingPageHeader title={ui.marketingPlans} subtitle="Планы публикаций tenant." />
        <Alert variant="info">{moduleDisabledMessage("marketing")}</Alert>
      </div>
    );
  }
  if (blocking) {
    return (
      <div className="page">
        <MarketingPageHeader title={ui.marketingPlans} subtitle="Планы публикаций tenant." />
        <Alert variant="error">
          {blocking instanceof ApiError ? blocking.message : "Ошибка загрузки планов."}
        </Alert>
      </div>
    );
  }

  const plans = plansQuery.data ?? [];

  function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || !periodStart || !periodEnd) {
      setFormError("Укажите название и период.");
      return;
    }
    createMutation.mutate({
      title: title.trim(),
      period_start: periodStart,
      period_end: periodEnd,
    });
  }

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingPlans}
        subtitle="Черновики и утверждённые планы. Prompt export и JSON import — отдельные шаги."
      />

      <div className="workspace-quick-links panel" style={{ marginBottom: "1rem" }}>
        <Link to={`${base}/plans/prompt`}>Сформировать промпт</Link>
        <Link to={`${base}/plans/import`}>Импорт JSON</Link>
        <Link to={`${base}/guide`}>Marketing Guide</Link>
        <Link to={`${base}/rubrics`}>Рубрики</Link>
      </div>

      <section className="panel marketing-topic-create" style={{ marginBottom: "1.25rem" }}>
        <h2>Новый draft-план</h2>
        <p className="muted">Создаёт только заголовок. Строки добавляются в карточке плана.</p>
        {formError ? <Alert variant="error">{formError}</Alert> : null}
        <form className="marketing-form-grid" onSubmit={onCreate}>
          <Input label="Название" value={title} onChange={(e) => setTitle(e.target.value)} />
          <Input
            label="Начало периода"
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
          <Input
            label="Конец периода"
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
          />
          <div>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Создание…" : "Создать draft"}
            </Button>
          </div>
        </form>
      </section>

      <section className="panel">
        <h2>Список планов</h2>
        <Table
          emptyText="Планов пока нет — создайте draft или импортируйте JSON."
          rowKey={(plan) => plan.id}
          data={plans}
          columns={[
            { key: "title", header: "Название", render: (plan) => plan.title },
            {
              key: "period",
              header: "Период",
              render: (plan) => `${plan.period_start} → ${plan.period_end}`,
            },
            {
              key: "status",
              header: "Статус",
              render: (plan) => marketingContentPlanStatusLabel(plan.status),
            },
            {
              key: "source",
              header: "Источник",
              render: (plan) => (plan.source === "json_import" ? "JSON import" : "Вручную"),
            },
            {
              key: "open",
              header: "",
              render: (plan) => <Link to={`${base}/plans/${plan.id}`}>Открыть</Link>,
            },
          ]}
        />
      </section>
    </div>
  );
}
