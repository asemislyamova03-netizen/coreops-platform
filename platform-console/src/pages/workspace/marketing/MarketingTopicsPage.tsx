import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import {
  archiveMarketingTopic,
  createMarketingTopic,
  listMarketingTopics,
  takeMarketingTopic,
  updateMarketingTopic,
} from "../../../api/marketing";
import { ApiError } from "../../../api/client";
import { Alert } from "../../../components/ui/Alert";
import { Loading } from "../../../components/ui/Loading";
import { Table } from "../../../components/ui/Table";
import type {
  MarketingTopic,
  MarketingTopicCreatePayload,
  MarketingTopicStatus,
  MarketingTopicUpdatePayload,
} from "../../../types/marketing";
import { ui } from "../../../i18n/ruUi";
import { formatDate } from "../../../workspace/formatters";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import {
  firstBlockingError,
  isModuleDisabled,
  moduleDisabledMessage,
} from "../../../workspace/moduleErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";
import { marketingTopicStatusLabel } from "./marketingLabels";
import { formatMarketingApiError } from "./packDetail/marketingErrors";
import {
  MARKETING_FUNNEL_OPTIONS,
  MARKETING_PRIORITY_OPTIONS,
  MARKETING_RUBRIC_OPTIONS,
  buildTopicCreatePayload,
  buildTopicUpdatePayload,
  extractTopicEditorial,
  marketingFunnelLabel,
  marketingRubricLabel,
  priorityLabel,
  priorityLevelFromValue,
  priorityValueFromLevel,
  type MarketingPriorityLevel,
} from "./marketingTaxonomy";

type TopicFormState = {
  title: string;
  rubric: string;
  angle: string;
  audience: string;
  pain: string;
  insight: string;
  source_ref: string;
  cta: string;
  funnel_stage: string;
  priorityLevel: MarketingPriorityLevel;
  planned_date: string;
  notes: string;
};

const EMPTY_FORM: TopicFormState = {
  title: "",
  rubric: "asem_column",
  angle: "",
  audience: "",
  pain: "",
  insight: "",
  source_ref: "",
  cta: "",
  funnel_stage: "awareness",
  priorityLevel: "normal",
  planned_date: "",
  notes: "",
};

function formFromTopic(topic: MarketingTopic): TopicFormState {
  const editorial = extractTopicEditorial(topic);
  return {
    title: topic.title,
    rubric: topic.rubric || "asem_column",
    angle: topic.angle ?? "",
    audience: editorial.audience,
    pain: editorial.pain,
    insight: editorial.insight,
    source_ref: editorial.source_ref,
    cta: editorial.cta,
    funnel_stage: editorial.funnel_stage || "awareness",
    priorityLevel: priorityLevelFromValue(topic.priority),
    planned_date: editorial.planned_date,
    notes: editorial.notes,
  };
}

export function MarketingTopicsPage() {
  const { tenantSlug = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isLoading: labelsLoading } = useWorkspaceLabels();

  const [form, setForm] = useState<TopicFormState>(EMPTY_FORM);
  const [editingTopicId, setEditingTopicId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyTopicId, setBusyTopicId] = useState<string | null>(null);
  const [filterRubric, setFilterRubric] = useState("");
  const [filterStatus, setFilterStatus] = useState<"" | MarketingTopicStatus>("");
  const [filterPriority, setFilterPriority] = useState<"" | MarketingPriorityLevel>("");

  const topicsQuery = useQuery({
    queryKey: ["marketing-topics", filterRubric, filterStatus],
    queryFn: () =>
      listMarketingTopics({
        limit: 200,
        rubric: filterRubric || undefined,
        status: filterStatus || undefined,
      }),
    enabled: !labelsLoading,
  });

  const createMutation = useMutation({
    mutationFn: (payload: MarketingTopicCreatePayload) => createMarketingTopic(payload),
    onSuccess: async () => {
      setForm(EMPTY_FORM);
      setEditingTopicId(null);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["marketing-topics"] });
    },
    onError: (error) => {
      setFormError(formatMarketingApiError(error, "Не удалось создать тему."));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      topicId,
      payload,
    }: {
      topicId: string;
      payload: MarketingTopicUpdatePayload;
    }) => updateMarketingTopic(topicId, payload),
    onSuccess: async () => {
      setForm(EMPTY_FORM);
      setEditingTopicId(null);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["marketing-topics"] });
    },
    onError: (error) => {
      setFormError(formatMarketingApiError(error, "Не удалось сохранить тему."));
    },
  });

  async function runTopicAction(topicId: string, action: () => Promise<unknown>) {
    setBusyTopicId(topicId);
    setActionError(null);
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: ["marketing-topics"] });
      await queryClient.invalidateQueries({ queryKey: ["marketing-packs"] });
    } catch (error) {
      setActionError(formatMarketingApiError(error, "Не удалось выполнить действие."));
    } finally {
      setBusyTopicId(null);
    }
  }

  const topics = useMemo(() => {
    const rows = topicsQuery.data ?? [];
    if (!filterPriority) return rows;
    return rows.filter(
      (row) => priorityLevelFromValue(row.priority) === filterPriority,
    );
  }, [topicsQuery.data, filterPriority]);

  if (labelsLoading || topicsQuery.isLoading) {
    return <Loading text="Загрузка тем..." />;
  }

  const marketingDisabled = isModuleDisabled("marketing", topicsQuery.error);
  const error = firstBlockingError(topicsQuery.error);

  if (marketingDisabled && !error) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingTopics}
          subtitle="Банк тем для контент-планирования."
        />
        <Alert variant="info">{moduleDisabledMessage("marketing")}</Alert>
      </div>
    );
  }

  if (topicsQuery.error) {
    const message =
      topicsQuery.error instanceof ApiError
        ? topicsQuery.error.message
        : "Не удалось загрузить темы.";
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingTopics}
          subtitle="Банк тем для контент-планирования."
        />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  function patchForm(partial: Partial<TopicFormState>) {
    setForm((prev) => ({ ...prev, ...partial }));
  }

  function submitForm(event: FormEvent) {
    event.preventDefault();
    if (!form.title.trim()) {
      setFormError("Укажите название темы.");
      return;
    }
    setFormError(null);
    const base = {
      title: form.title,
      rubric: form.rubric,
      angle: form.angle,
      priority: priorityValueFromLevel(form.priorityLevel),
      audience: form.audience,
      pain: form.pain,
      insight: form.insight,
      source_ref: form.source_ref,
      cta: form.cta,
      funnel_stage: form.funnel_stage,
      notes: form.notes,
      planned_date: form.planned_date,
    };
    if (editingTopicId) {
      updateMutation.mutate({
        topicId: editingTopicId,
        payload: buildTopicUpdatePayload(base),
      });
      return;
    }
    createMutation.mutate(buildTopicCreatePayload(base));
  }

  const formBusy = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingTopics}
        subtitle="Банк тем: рубрика, insight, CTA → утвердить → взять в работу."
      />

      <form className="panel marketing-topic-create" onSubmit={submitForm}>
        <h3>{editingTopicId ? "Редактирование темы" : "Создание темы"}</h3>
        <div className="marketing-form-grid">
          <label className="form-field marketing-form-span-2">
            <span className="form-label">Название</span>
            <input
              className="form-input"
              value={form.title}
              onChange={(event) => patchForm({ title: event.target.value })}
              placeholder="Тема для контент-пака"
            />
          </label>
          <label className="form-field">
            <span className="form-label">Рубрика</span>
            <select
              className="form-input"
              value={form.rubric}
              onChange={(event) => patchForm({ rubric: event.target.value })}
            >
              {MARKETING_RUBRIC_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">Priority</span>
            <select
              className="form-input"
              value={form.priorityLevel}
              onChange={(event) =>
                patchForm({ priorityLevel: event.target.value as MarketingPriorityLevel })
              }
            >
              {MARKETING_PRIORITY_OPTIONS.map((option) => (
                <option key={option.level} value={option.level}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">Funnel stage</span>
            <select
              className="form-input"
              value={form.funnel_stage}
              onChange={(event) => patchForm({ funnel_stage: event.target.value })}
            >
              {MARKETING_FUNNEL_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">Плановая дата</span>
            <input
              className="form-input"
              type="date"
              value={form.planned_date}
              onChange={(event) => patchForm({ planned_date: event.target.value })}
            />
          </label>
          <label className="form-field marketing-form-span-2">
            <span className="form-label">Angle</span>
            <input
              className="form-input"
              value={form.angle}
              onChange={(event) => patchForm({ angle: event.target.value })}
              placeholder="Угол подачи"
            />
          </label>
          <label className="form-field">
            <span className="form-label">Audience</span>
            <input
              className="form-input"
              value={form.audience}
              onChange={(event) => patchForm({ audience: event.target.value })}
              placeholder="Для кого"
            />
          </label>
          <label className="form-field">
            <span className="form-label">CTA</span>
            <input
              className="form-input"
              value={form.cta}
              onChange={(event) => patchForm({ cta: event.target.value })}
              placeholder="Призыв к действию"
            />
          </label>
          <label className="form-field marketing-form-span-2">
            <span className="form-label">Pain / problem</span>
            <textarea
              className="form-input marketing-textarea"
              rows={2}
              value={form.pain}
              onChange={(event) => patchForm({ pain: event.target.value })}
              placeholder="Боль клиента / проблема"
            />
          </label>
          <label className="form-field marketing-form-span-2">
            <span className="form-label">Insight</span>
            <textarea
              className="form-input marketing-textarea"
              rows={2}
              value={form.insight}
              onChange={(event) => patchForm({ insight: event.target.value })}
              placeholder="Ключевой инсайт"
            />
          </label>
          <label className="form-field marketing-form-span-2">
            <span className="form-label">Source / reference</span>
            <textarea
              className="form-input marketing-textarea"
              rows={2}
              value={form.source_ref}
              onChange={(event) => patchForm({ source_ref: event.target.value })}
              placeholder="Откуда идея / ссылка / контекст"
            />
          </label>
          <label className="form-field marketing-form-span-2">
            <span className="form-label">Notes</span>
            <textarea
              className="form-input marketing-textarea"
              rows={2}
              value={form.notes}
              onChange={(event) => patchForm({ notes: event.target.value })}
              placeholder="Внутренние заметки"
            />
          </label>
        </div>
        {formError && <Alert variant="error">{formError}</Alert>}
        <div className="marketing-topic-actions">
          <button type="submit" className="btn btn-primary" disabled={formBusy}>
            {formBusy
              ? "Сохранение..."
              : editingTopicId
                ? "Сохранить изменения"
                : "Создать тему"}
          </button>
          {editingTopicId && (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={formBusy}
              onClick={() => {
                setEditingTopicId(null);
                setForm(EMPTY_FORM);
                setFormError(null);
              }}
            >
              Отмена
            </button>
          )}
        </div>
      </form>

      <div className="panel marketing-packs-filters">
        <h3>Фильтры</h3>
        <div className="marketing-form-grid">
          <label className="form-field">
            <span className="form-label">Рубрика</span>
            <select
              className="form-input"
              value={filterRubric}
              onChange={(event) => setFilterRubric(event.target.value)}
            >
              <option value="">Все</option>
              {MARKETING_RUBRIC_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">Статус</span>
            <select
              className="form-input"
              value={filterStatus}
              onChange={(event) =>
                setFilterStatus(event.target.value as "" | MarketingTopicStatus)
              }
            >
              <option value="">Все</option>
              <option value="draft">Черновик</option>
              <option value="approved">Утверждена</option>
              <option value="used">Использована</option>
              <option value="archived">В архиве</option>
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">Priority</span>
            <select
              className="form-input"
              value={filterPriority}
              onChange={(event) =>
                setFilterPriority(event.target.value as "" | MarketingPriorityLevel)
              }
            >
              <option value="">Все</option>
              {MARKETING_PRIORITY_OPTIONS.map((option) => (
                <option key={option.level} value={option.level}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {actionError && <Alert variant="error">{actionError}</Alert>}

      {topics.length === 0 ? (
        <Alert variant="info">Тем пока нет или фильтр пуст. Создайте первую тему.</Alert>
      ) : (
        <div className="panel">
          <Table<MarketingTopic>
            rowKey={(row) => row.id}
            data={topics}
            emptyText="Нет тем"
            columns={[
              {
                key: "title",
                header: "Название",
                render: (row) => (
                  <div>
                    <div>{row.title}</div>
                    {row.angle ? <div className="muted">{row.angle}</div> : null}
                  </div>
                ),
              },
              {
                key: "rubric",
                header: "Рубрика",
                render: (row) => marketingRubricLabel(row.rubric),
              },
              {
                key: "context",
                header: "Контекст",
                render: (row) => {
                  const editorial = extractTopicEditorial(row);
                  return (
                    <div className="muted">
                      <div>{marketingFunnelLabel(editorial.funnel_stage)}</div>
                      {editorial.audience ? <div>Audience: {editorial.audience}</div> : null}
                      {editorial.cta ? <div>CTA: {editorial.cta}</div> : null}
                    </div>
                  );
                },
              },
              {
                key: "status",
                header: "Статус",
                render: (row) => (
                  <span className="badge">{marketingTopicStatusLabel(row.status)}</span>
                ),
              },
              {
                key: "priority",
                header: "Priority",
                render: (row) => priorityLabel(row.priority),
              },
              {
                key: "planned",
                header: "План",
                render: (row) => extractTopicEditorial(row).planned_date || "—",
              },
              {
                key: "updated",
                header: "Обновлена",
                render: (row) => formatDate(row.updated_at),
              },
              {
                key: "actions",
                header: "Действия",
                render: (row) => (
                  <TopicRowActions
                    topic={row}
                    busy={busyTopicId === row.id}
                    onEdit={() => {
                      setEditingTopicId(row.id);
                      setForm(formFromTopic(row));
                      setFormError(null);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                    onApprove={() =>
                      runTopicAction(row.id, () =>
                        updateMarketingTopic(row.id, { status: "approved" }),
                      )
                    }
                    onTake={() =>
                      runTopicAction(row.id, async () => {
                        const editorial = extractTopicEditorial(row);
                        const pack = await takeMarketingTopic(row.id, {
                          source: "console",
                          planned_date: editorial.planned_date || undefined,
                        });
                        navigate(`/workspace/${tenantSlug}/marketing/packs/${pack.id}`);
                      })
                    }
                    onArchive={() =>
                      runTopicAction(row.id, () => archiveMarketingTopic(row.id))
                    }
                  />
                ),
              },
            ]}
          />
        </div>
      )}
    </div>
  );
}

function TopicRowActions({
  topic,
  busy,
  onEdit,
  onApprove,
  onTake,
  onArchive,
}: {
  topic: MarketingTopic;
  busy: boolean;
  onEdit: () => void;
  onApprove: () => void;
  onTake: () => void;
  onArchive: () => void;
}) {
  const canApprove = topic.status === "draft";
  const canTake = topic.status === "approved";
  const canArchive = topic.status !== "archived";

  return (
    <div className="marketing-topic-actions">
      <button type="button" className="btn btn-secondary" disabled={busy} onClick={onEdit}>
        Edit
      </button>
      {canApprove && (
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={onApprove}>
          Утвердить
        </button>
      )}
      {canTake ? (
        <button type="button" className="btn btn-primary" disabled={busy} onClick={onTake}>
          {busy ? "..." : "Взять в работу"}
        </button>
      ) : topic.status !== "archived" && topic.status !== "used" ? (
        <span className="muted marketing-topic-take-hint">
          Взять можно после approval темы
        </span>
      ) : null}
      {canArchive && (
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={onArchive}>
          В архив
        </button>
      )}
    </div>
  );
}
