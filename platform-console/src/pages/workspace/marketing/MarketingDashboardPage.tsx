import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getMarketingHealth, listMarketingPacks, listMarketingTopics } from "../../../api/marketing";
import { ApiError } from "../../../api/client";
import { DashboardKpiCard } from "../../../components/workspace/DashboardKpiCard";
import { Alert } from "../../../components/ui/Alert";
import { Loading } from "../../../components/ui/Loading";
import { ui } from "../../../i18n/ruUi";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import {
  firstBlockingError,
  isModuleDisabled,
  moduleDisabledMessage,
} from "../../../workspace/moduleErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";

export function MarketingDashboardPage() {
  const { isLoading: labelsLoading } = useWorkspaceLabels();

  const healthQuery = useQuery({
    queryKey: ["marketing-health"],
    queryFn: getMarketingHealth,
    enabled: !labelsLoading,
  });

  const topicsQuery = useQuery({
    queryKey: ["marketing-topics", "dashboard"],
    queryFn: () => listMarketingTopics({ limit: 200 }),
    enabled: !labelsLoading && healthQuery.isSuccess,
  });

  const packsQuery = useQuery({
    queryKey: ["marketing-packs", "dashboard"],
    queryFn: () => listMarketingPacks({ limit: 200 }),
    enabled: !labelsLoading && healthQuery.isSuccess,
  });

  if (labelsLoading || healthQuery.isLoading) {
    return <Loading text="Загрузка раздела «Маркетинг»..." />;
  }

  const marketingDisabled = isModuleDisabled("marketing", healthQuery.error);
  const error = firstBlockingError(
    healthQuery.error,
    topicsQuery.error,
    packsQuery.error,
  );

  if (marketingDisabled && !error) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketing}
          subtitle="Контент, публикации и согласование материалов организации."
        />
        <Alert variant="info">{moduleDisabledMessage("marketing")}</Alert>
      </div>
    );
  }

  if (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Не удалось загрузить данные раздела «Маркетинг».";
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketing}
          subtitle="Контент, публикации и согласование материалов организации."
        />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const topics = topicsQuery.data ?? [];
  const packs = packsQuery.data ?? [];
  const pendingApprovalCount = packs.filter(
    (pack) =>
      pack.status === "ready_for_approval" || pack.approval_status === "pending",
  ).length;
  const latestPublicationsCount = packs.filter(
    (pack) =>
      pack.publish_status === "published" || pack.status === "published",
  ).length;

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketing}
        subtitle="Контент, публикации и согласование материалов организации."
      />

      <Alert variant="info">
        Workflow: Темы → взять в работу → Pack → тексты / media → preflight → approval. Публикация
        пока выключена.
      </Alert>

      <div className="workspace-kpi-grid">
        <Link to="topics" className="workspace-kpi-link">
          <DashboardKpiCard
            label="Темы"
            value={topicsQuery.isLoading ? "…" : String(topics.length)}
            hint="Банк тем для контента"
          />
        </Link>
        <Link to="packs" className="workspace-kpi-link">
          <DashboardKpiCard
            label="Публикации / Packs"
            value={packsQuery.isLoading ? "…" : String(packs.length)}
            hint="Контент-пакеты по каналам"
          />
        </Link>
        <DashboardKpiCard
          label="На согласовании"
          value={packsQuery.isLoading ? "…" : String(pendingApprovalCount)}
          hint="Packs в статусе ready_for_approval"
        />
        <DashboardKpiCard
          label="Последние публикации"
          value={packsQuery.isLoading ? "…" : String(latestPublicationsCount)}
          hint="Placeholder · детальный журнал — в следующих слайсах"
        />
      </div>

      <div className="workspace-dashboard-links panel">
        <h3>Разделы Marketing Cabinet</h3>
        <div className="workspace-quick-links">
          <Link to="topics">{ui.marketingTopics}</Link>
          <Link to="packs">{ui.marketingPacks}</Link>
          <span className="muted">Leads из контента — будет подключено позже</span>
        </div>
      </div>
    </div>
  );
}
