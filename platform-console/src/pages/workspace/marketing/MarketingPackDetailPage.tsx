import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getMarketingPack } from "../../../api/marketing";
import { ApiError } from "../../../api/client";
import { Alert } from "../../../components/ui/Alert";
import { Loading } from "../../../components/ui/Loading";
import { ui } from "../../../i18n/ruUi";
import { formatDate } from "../../../workspace/formatters";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import {
  firstBlockingError,
  isModuleDisabled,
  moduleDisabledMessage,
} from "../../../workspace/moduleErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";
import {
  marketingApprovalStatusLabel,
  marketingPackStatusLabel,
  marketingPreflightStatusLabel,
  marketingPublishStatusLabel,
} from "./marketingLabels";
import { resolveMarketingNextAction } from "./marketingNextAction";
import { PackDetailApprovalTab } from "./packDetail/PackDetailApprovalTab";
import { PackDetailLogsTab } from "./packDetail/PackDetailLogsTab";
import { PackDetailMediaTab } from "./packDetail/PackDetailMediaTab";
import { PackDetailPreflightTab } from "./packDetail/PackDetailPreflightTab";
import { PackDetailPublishTab } from "./packDetail/PackDetailPublishTab";
import { PackDetailTextsTab } from "./packDetail/PackDetailTextsTab";

const PACK_TABS = [
  { id: "texts", label: "Texts" },
  { id: "media", label: "Media" },
  { id: "preflight", label: "Preflight" },
  { id: "approval", label: "Approval" },
  { id: "publish", label: "Publish" },
  { id: "logs", label: "Logs" },
] as const;

type PackTabId = (typeof PACK_TABS)[number]["id"];

export function MarketingPackDetailPage() {
  const { tenantSlug = "", packId = "" } = useParams();
  const { isLoading: labelsLoading } = useWorkspaceLabels();
  const [activeTab, setActiveTab] = useState<PackTabId>("texts");

  const packQuery = useQuery({
    queryKey: ["marketing-pack", packId],
    queryFn: () => getMarketingPack(packId),
    enabled: !labelsLoading && Boolean(packId),
  });

  if (labelsLoading || packQuery.isLoading) {
    return <Loading text="Загрузка pack..." />;
  }

  const marketingDisabled = isModuleDisabled("marketing", packQuery.error);
  const error = firstBlockingError(packQuery.error);

  if (marketingDisabled && !error) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingPackDetail}
          subtitle="Детали контент-пакета."
        />
        <Alert variant="info">{moduleDisabledMessage("marketing")}</Alert>
      </div>
    );
  }

  if (packQuery.error) {
    const message =
      packQuery.error instanceof ApiError
        ? packQuery.error.message
        : "Не удалось загрузить pack.";
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingPackDetail}
          subtitle="Детали контент-пакета."
        />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const pack = packQuery.data;

  if (!pack) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingPackDetail}
          subtitle="Детали контент-пакета."
        />
        <Alert variant="info">Pack не найден.</Alert>
      </div>
    );
  }

  const nextAction = resolveMarketingNextAction(pack);

  return (
    <div className="page">
      <MarketingPageHeader
        title={pack.title}
        subtitle={`Pack detail · ${pack.slug}`}
      />

      <p className="muted">
        <Link to={`/workspace/${tenantSlug}/marketing/packs`}>← К списку публикаций</Link>
      </p>

      <div className="panel marketing-next-action">
        <h3>Следующее действие</h3>
        <p>{nextAction.message}</p>
        {nextAction.tabHint && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setActiveTab(nextAction.tabHint as PackTabId)}
          >
            Перейти: {nextAction.tabHint}
          </button>
        )}
        {nextAction.id === "add_media" && (
          <p className="muted">
            Медиа необязательно для preflight — можно сразу открыть вкладку Preflight.
          </p>
        )}
      </div>

      <div className="panel workspace-pack-meta">
        <dl className="detail-list">
          <dt>Статус</dt>
          <dd>{marketingPackStatusLabel(pack.status)}</dd>
          <dt>Preflight</dt>
          <dd>{marketingPreflightStatusLabel(pack.preflight_status)}</dd>
          <dt>Согласование</dt>
          <dd>{marketingApprovalStatusLabel(pack.approval_status)}</dd>
          <dt>Публикация</dt>
          <dd>{marketingPublishStatusLabel(pack.publish_status)}</dd>
          <dt>Тема</dt>
          <dd>{pack.topic?.title ?? "—"}</dd>
          <dt>Плановая дата</dt>
          <dd>{pack.planned_date}</dd>
          <dt>Обновлён</dt>
          <dd>{formatDate(pack.updated_at)}</dd>
        </dl>
      </div>

      <div className="tabs workspace-detail-tabs">
        {PACK_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? "tab active" : "tab"}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="panel marketing-pack-detail-panel">
        {activeTab === "texts" && <PackDetailTextsTab packId={packId} pack={pack} />}
        {activeTab === "media" && <PackDetailMediaTab packId={packId} pack={pack} />}
        {activeTab === "preflight" && (
          <PackDetailPreflightTab packId={packId} pack={pack} />
        )}
        {activeTab === "approval" && (
          <PackDetailApprovalTab packId={packId} pack={pack} />
        )}
        {activeTab === "publish" && <PackDetailPublishTab />}
        {activeTab === "logs" && <PackDetailLogsTab pack={pack} />}
      </div>
    </div>
  );
}
