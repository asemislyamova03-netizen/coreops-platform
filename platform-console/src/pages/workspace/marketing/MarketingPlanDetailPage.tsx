import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  approveMarketingContentPlan,
  archiveMarketingContentPlan,
  cancelMarketingContentPlanItem,
  createMarketingContentPlanItem,
  createTopicFromContentPlanItem,
  getMarketingContentPlan,
  listMarketingContentPlanItems,
  listMarketingRubrics,
  updateMarketingContentPlanItem,
} from "../../../api/marketing";
import { ApiError } from "../../../api/client";
import { Alert } from "../../../components/ui/Alert";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Loading } from "../../../components/ui/Loading";
import { Table } from "../../../components/ui/Table";
import { ui } from "../../../i18n/ruUi";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import { formatMarketingApiError } from "./packDetail/marketingErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";
import {
  PLAN_CHANNEL_OPTIONS,
  marketingContentPlanItemStatusLabel,
  marketingContentPlanStatusLabel,
} from "./marketingPlanLabels";

export function MarketingPlanDetailPage() {
  const { tenantSlug = "", planId = "" } = useParams();
  const queryClient = useQueryClient();
  const { isLoading: labelsLoading } = useWorkspaceLabels();
  const base = `/workspace/${tenantSlug}/marketing`;

  const [actionError, setActionError] = useState<string | null>(null);
  const [actionInfo, setActionInfo] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [plannedDate, setPlannedDate] = useState("");
  const [rubricId, setRubricId] = useState("");
  const [channels, setChannels] = useState<string[]>(["telegram"]);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);

  const planQuery = useQuery({
    queryKey: ["marketing-content-plan", planId],
    queryFn: () => getMarketingContentPlan(planId),
    enabled: !labelsLoading && Boolean(planId),
  });
  const itemsQuery = useQuery({
    queryKey: ["marketing-content-plan-items", planId],
    queryFn: () => listMarketingContentPlanItems(planId),
    enabled: !labelsLoading && Boolean(planId),
  });
  const rubricsQuery = useQuery({
    queryKey: ["marketing-rubrics-active"],
    queryFn: () => listMarketingRubrics({ status: "active" }),
    enabled: !labelsLoading,
  });

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["marketing-content-plan", planId] });
    await queryClient.invalidateQueries({ queryKey: ["marketing-content-plan-items", planId] });
    await queryClient.invalidateQueries({ queryKey: ["marketing-content-plans"] });
    await queryClient.invalidateQueries({ queryKey: ["marketing-topics"] });
  };

  const approveMutation = useMutation({
    mutationFn: () => approveMarketingContentPlan(planId),
    onSuccess: async () => {
      setActionError(null);
      setActionInfo("План утверждён. Строки переведены в approved.");
      await invalidate();
    },
    onError: (error) =>
      setActionError(formatMarketingApiError(error, "Не удалось утвердить план.")),
  });
  const archiveMutation = useMutation({
    mutationFn: () => archiveMarketingContentPlan(planId),
    onSuccess: async () => {
      setActionError(null);
      setActionInfo("План отправлен в архив.");
      await invalidate();
    },
    onError: (error) =>
      setActionError(formatMarketingApiError(error, "Не удалось архивировать план.")),
  });
  const saveItemMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        planned_date: plannedDate,
        rubric_id: rubricId,
        working_title: title.trim(),
        channels,
      };
      if (editingItemId) {
        return updateMarketingContentPlanItem(planId, editingItemId, payload);
      }
      return createMarketingContentPlanItem(planId, payload);
    },
    onSuccess: async () => {
      setActionError(null);
      setTitle("");
      setPlannedDate("");
      setEditingItemId(null);
      await invalidate();
    },
    onError: (error) =>
      setActionError(formatMarketingApiError(error, "Не удалось сохранить строку.")),
  });
  const cancelMutation = useMutation({
    mutationFn: (itemId: string) => cancelMarketingContentPlanItem(planId, itemId),
    onSuccess: async () => {
      setActionError(null);
      await invalidate();
    },
    onError: (error) =>
      setActionError(formatMarketingApiError(error, "Не удалось отменить строку.")),
  });
  const createTopicMutation = useMutation({
    mutationFn: (itemId: string) => createTopicFromContentPlanItem(planId, itemId),
    onSuccess: async (result) => {
      setActionError(null);
      setActionInfo(
        result.replayed
          ? "Тема уже была создана ранее — открываем существующую."
          : "Тема создана. Дальше — «Взять в работу» в разделе Темы.",
      );
      await invalidate();
    },
    onError: (error) =>
      setActionError(formatMarketingApiError(error, "Не удалось создать тему.")),
  });

  const plan = planQuery.data;
  const items = itemsQuery.data ?? [];
  const rubrics = rubricsQuery.data ?? [];
  const rubricNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const row of rubrics) map.set(row.id, `${row.name} (${row.code})`);
    return map;
  }, [rubrics]);

  const isDraft = plan?.status === "draft";
  const isApproved = plan?.status === "approved";
  const nonCancelled = items.filter((row) => row.status !== "cancelled");

  if (labelsLoading || planQuery.isLoading || itemsQuery.isLoading) {
    return <Loading text="Загрузка плана..." />;
  }
  if (planQuery.error || !plan) {
    return (
      <div className="page">
        <MarketingPageHeader title={ui.marketingPlans} subtitle="Карточка плана" />
        <Alert variant="error">
          {planQuery.error instanceof ApiError
            ? planQuery.error.message
            : "План не найден."}
        </Alert>
        <Link to={`${base}/plans`}>← К списку</Link>
      </div>
    );
  }

  function onSaveItem(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || !plannedDate || !rubricId) {
      setActionError("Заполните название, дату и рубрику.");
      return;
    }
    saveItemMutation.mutate();
  }

  function toggleChannel(channel: string) {
    setChannels((prev) =>
      prev.includes(channel) ? prev.filter((c) => c !== channel) : [...prev, channel],
    );
  }

  return (
    <div className="page">
      <MarketingPageHeader
        title={plan.title}
        subtitle={`${plan.period_start} → ${plan.period_end} · ${marketingContentPlanStatusLabel(plan.status)}`}
      />
      <p>
        <Link to={`${base}/plans`}>← К списку планов</Link>
      </p>

      {actionError ? <Alert variant="error">{actionError}</Alert> : null}
      {actionInfo ? <Alert variant="info">{actionInfo}</Alert> : null}

      <section className="panel" style={{ marginBottom: "1rem" }}>
        <h2>Жизненный цикл</h2>
        <p className="muted">
          Активных строк (не cancelled): <strong>{nonCancelled.length}</strong>
        </p>
        {isDraft ? (
          <div className="workspace-quick-links">
            <Button
              type="button"
              disabled={approveMutation.isPending || nonCancelled.length === 0}
              onClick={() => {
                if (nonCancelled.length === 0) {
                  setActionError("Нельзя утвердить план без строк.");
                  return;
                }
                if (
                  window.confirm(
                    `Утвердить план «${plan.title}»? Будет утверждено строк: ${nonCancelled.length}.`,
                  )
                ) {
                  approveMutation.mutate();
                }
              }}
            >
              {approveMutation.isPending ? "Утверждение…" : "Утвердить план"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={archiveMutation.isPending}
              onClick={() => {
                if (window.confirm("Отправить план в архив?")) archiveMutation.mutate();
              }}
            >
              В архив
            </Button>
          </div>
        ) : null}
        {isApproved ? (
          <div className="workspace-quick-links">
            <Button
              type="button"
              variant="secondary"
              disabled={archiveMutation.isPending}
              onClick={() => {
                if (window.confirm("Архивировать утверждённый план?")) {
                  archiveMutation.mutate();
                }
              }}
            >
              Архивировать
            </Button>
            <span className="muted">Редактирование строк недоступно после approve.</span>
          </div>
        ) : null}
        {plan.status === "archived" ? (
          <p className="muted">План в архиве — только просмотр.</p>
        ) : null}
      </section>

      {isDraft ? (
        <section className="panel marketing-topic-create" style={{ marginBottom: "1rem" }}>
          <h2>{editingItemId ? "Редактировать строку" : "Добавить строку"}</h2>
          {rubrics.length === 0 ? (
            <Alert variant="info">
              Нет active рубрик.{" "}
              <Link to={`${base}/rubrics`}>Создайте рубрику</Link>, затем вернитесь сюда.
            </Alert>
          ) : (
            <form className="marketing-form-grid" onSubmit={onSaveItem}>
              <Input
                label="Рабочий заголовок"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <Input
                label="Дата"
                type="date"
                value={plannedDate}
                onChange={(e) => setPlannedDate(e.target.value)}
              />
              <label className="form-field">
                <span className="form-label">Рубрика</span>
                <select
                  className="form-select"
                  value={rubricId}
                  onChange={(e) => setRubricId(e.target.value)}
                >
                  <option value="">Выберите…</option>
                  {rubrics.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.name} ({row.code})
                    </option>
                  ))}
                </select>
              </label>
              <fieldset>
                <legend>Каналы</legend>
                {PLAN_CHANNEL_OPTIONS.map((channel) => (
                  <label key={channel} style={{ display: "inline-flex", marginRight: "0.75rem" }}>
                    <input
                      type="checkbox"
                      checked={channels.includes(channel)}
                      onChange={() => toggleChannel(channel)}
                    />{" "}
                    {channel}
                  </label>
                ))}
              </fieldset>
              <div className="workspace-quick-links">
                <Button type="submit" disabled={saveItemMutation.isPending}>
                  {saveItemMutation.isPending ? "Сохранение…" : "Сохранить строку"}
                </Button>
                {editingItemId ? (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setEditingItemId(null);
                      setTitle("");
                      setPlannedDate("");
                    }}
                  >
                    Отменить правку
                  </Button>
                ) : null}
              </div>
            </form>
          )}
        </section>
      ) : null}

      <section className="panel">
        <h2>Строки плана</h2>
        <Table
          emptyText="Строк пока нет."
          rowKey={(item) => item.id}
          data={items}
          columns={[
            { key: "date", header: "Дата", render: (item) => item.planned_date },
            {
              key: "rubric",
              header: "Рубрика",
              render: (item) =>
                rubricNameById.get(item.rubric_id) ?? item.rubric_id.slice(0, 8),
            },
            { key: "title", header: "Заголовок", render: (item) => item.working_title },
            {
              key: "channels",
              header: "Каналы",
              render: (item) => item.channels.join(", ") || "—",
            },
            {
              key: "status",
              header: "Статус",
              render: (item) => marketingContentPlanItemStatusLabel(item.status),
            },
            {
              key: "actions",
              header: "Действия",
              render: (item) => (
                <div className="workspace-quick-links">
                  {isDraft && item.status === "draft" ? (
                    <>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => {
                          setEditingItemId(item.id);
                          setTitle(item.working_title);
                          setPlannedDate(item.planned_date);
                          setRubricId(item.rubric_id);
                          setChannels(item.channels.length ? item.channels : ["telegram"]);
                        }}
                      >
                        Изменить
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={cancelMutation.isPending}
                        onClick={() => {
                          if (window.confirm("Отменить строку? Удаление запрещено.")) {
                            cancelMutation.mutate(item.id);
                          }
                        }}
                      >
                        Отменить
                      </Button>
                    </>
                  ) : null}
                  {isApproved && item.status === "approved" ? (
                    <Button
                      type="button"
                      disabled={createTopicMutation.isPending}
                      onClick={() => createTopicMutation.mutate(item.id)}
                    >
                      Создать тему
                    </Button>
                  ) : null}
                  {item.topic_id ? <Link to={`${base}/topics`}>Открыть темы →</Link> : null}
                  {isApproved && item.status === "topic_created" && item.topic_id ? (
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={createTopicMutation.isPending}
                      onClick={() => createTopicMutation.mutate(item.id)}
                    >
                      Показать тему (replay)
                    </Button>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      </section>
    </div>
  );
}
