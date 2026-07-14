import { FormEvent, useState } from "react";
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
import type { MarketingTopic } from "../../../types/marketing";
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

export function MarketingTopicsPage() {
  const { tenantSlug = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isLoading: labelsLoading } = useWorkspaceLabels();

  const [title, setTitle] = useState("");
  const [rubric, setRubric] = useState("general");
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyTopicId, setBusyTopicId] = useState<string | null>(null);

  const topicsQuery = useQuery({
    queryKey: ["marketing-topics"],
    queryFn: () => listMarketingTopics({ limit: 200 }),
    enabled: !labelsLoading,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createMarketingTopic({
        title: title.trim(),
        rubric: rubric.trim() || "general",
        source: "console",
        status: "draft",
      }),
    onSuccess: async () => {
      setTitle("");
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["marketing-topics"] });
    },
    onError: (error) => {
      setFormError(formatMarketingApiError(error, "Не удалось создать тему."));
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

  const topics = topicsQuery.data ?? [];

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingTopics}
        subtitle="Банк тем: создать → утвердить → взять в работу (создаёт draft pack)."
      />

      <form
        className="panel marketing-topic-create"
        onSubmit={(event: FormEvent) => {
          event.preventDefault();
          if (!title.trim()) {
            setFormError("Укажите название темы.");
            return;
          }
          setFormError(null);
          createMutation.mutate();
        }}
      >
        <h3>Быстрое создание темы</h3>
        <div className="marketing-form-grid">
          <label className="form-field">
            <span className="form-label">Название</span>
            <input
              className="form-input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Тема для контент-пака"
            />
          </label>
          <label className="form-field">
            <span className="form-label">Рубрика</span>
            <input
              className="form-input"
              value={rubric}
              onChange={(event) => setRubric(event.target.value)}
              placeholder="general"
            />
          </label>
        </div>
        {formError && <Alert variant="error">{formError}</Alert>}
        <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
          {createMutation.isPending ? "Создание..." : "Создать тему"}
        </button>
      </form>

      {actionError && <Alert variant="error">{actionError}</Alert>}

      {topics.length === 0 ? (
        <Alert variant="info">Тем пока нет. Создайте первую тему.</Alert>
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
                render: (row) => row.title,
              },
              {
                key: "rubric",
                header: "Рубрика",
                render: (row) => row.rubric,
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
                header: "Приоритет",
                render: (row) => String(row.priority),
              },
              {
                key: "used",
                header: "Использований",
                render: (row) => String(row.used_count),
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
                    onApprove={() =>
                      runTopicAction(row.id, () =>
                        updateMarketingTopic(row.id, { status: "approved" }),
                      )
                    }
                    onTake={() =>
                      runTopicAction(row.id, async () => {
                        const pack = await takeMarketingTopic(row.id, { source: "console" });
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
  onApprove,
  onTake,
  onArchive,
}: {
  topic: MarketingTopic;
  busy: boolean;
  onApprove: () => void;
  onTake: () => void;
  onArchive: () => void;
}) {
  const canApprove = topic.status === "draft";
  const canTake = topic.status === "approved";
  const canArchive = topic.status !== "archived";

  return (
    <div className="marketing-topic-actions">
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
