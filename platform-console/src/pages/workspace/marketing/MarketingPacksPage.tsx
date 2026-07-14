import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { listMarketingPacks } from "../../../api/marketing";
import { ApiError } from "../../../api/client";
import { Alert } from "../../../components/ui/Alert";
import { Loading } from "../../../components/ui/Loading";
import { Table } from "../../../components/ui/Table";
import type {
  MarketingApprovalStatus,
  MarketingPackStatus,
  MarketingPackSummary,
  MarketingPreflightStatus,
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
import {
  marketingApprovalStatusLabel,
  marketingPackStatusLabel,
  marketingPreflightStatusLabel,
} from "./marketingLabels";

const PACK_STATUS_OPTIONS: Array<MarketingPackStatus | ""> = [
  "",
  "draft",
  "preflight_failed",
  "ready_for_approval",
  "approved",
  "scheduled",
  "publishing",
  "published",
  "failed",
  "archived",
];

const APPROVAL_STATUS_OPTIONS: Array<MarketingApprovalStatus | ""> = [
  "",
  "draft",
  "pending",
  "approved",
  "rejected",
];

const PREFLIGHT_STATUS_OPTIONS: Array<MarketingPreflightStatus | ""> = [
  "",
  "not_run",
  "passed",
  "failed",
];

export function MarketingPacksPage() {
  const { tenantSlug = "" } = useParams();
  const { isLoading: labelsLoading } = useWorkspaceLabels();

  const [statusFilter, setStatusFilter] = useState<MarketingPackStatus | "">("");
  const [approvalFilter, setApprovalFilter] = useState<MarketingApprovalStatus | "">("");
  const [preflightFilter, setPreflightFilter] = useState<MarketingPreflightStatus | "">("");

  const packsQuery = useQuery({
    queryKey: ["marketing-packs"],
    queryFn: () => listMarketingPacks({ limit: 200 }),
    enabled: !labelsLoading,
  });

  const filteredPacks = useMemo(() => {
    const packs = packsQuery.data ?? [];
    return packs.filter((pack) => {
      if (statusFilter && pack.status !== statusFilter) return false;
      if (approvalFilter && pack.approval_status !== approvalFilter) return false;
      if (preflightFilter && pack.preflight_status !== preflightFilter) return false;
      return true;
    });
  }, [packsQuery.data, statusFilter, approvalFilter, preflightFilter]);

  if (labelsLoading || packsQuery.isLoading) {
    return <Loading text="Загрузка публикаций..." />;
  }

  const marketingDisabled = isModuleDisabled("marketing", packsQuery.error);
  const error = firstBlockingError(packsQuery.error);

  if (marketingDisabled && !error) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingPacks}
          subtitle="Контент-пакеты по каналам и этапам согласования."
        />
        <Alert variant="info">{moduleDisabledMessage("marketing")}</Alert>
      </div>
    );
  }

  if (packsQuery.error) {
    const message =
      packsQuery.error instanceof ApiError
        ? packsQuery.error.message
        : "Не удалось загрузить публикации.";
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingPacks}
          subtitle="Контент-пакеты по каналам и этапам согласования."
        />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const packs = packsQuery.data ?? [];
  const hasFilters = Boolean(statusFilter || approvalFilter || preflightFilter);

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingPacks}
        subtitle="Контент-пакеты: статусы, согласование и переход в редактор."
      />

      <div className="panel marketing-packs-filters">
        <div className="marketing-form-grid">
          <label className="form-field">
            <span className="form-label">Статус</span>
            <select
              className="form-input"
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value as MarketingPackStatus | "")
              }
            >
              {PACK_STATUS_OPTIONS.map((value) => (
                <option key={value || "all"} value={value}>
                  {value ? marketingPackStatusLabel(value) : "Все"}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">Согласование</span>
            <select
              className="form-input"
              value={approvalFilter}
              onChange={(event) =>
                setApprovalFilter(event.target.value as MarketingApprovalStatus | "")
              }
            >
              {APPROVAL_STATUS_OPTIONS.map((value) => (
                <option key={value || "all"} value={value}>
                  {value ? marketingApprovalStatusLabel(value) : "Все"}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">Preflight</span>
            <select
              className="form-input"
              value={preflightFilter}
              onChange={(event) =>
                setPreflightFilter(event.target.value as MarketingPreflightStatus | "")
              }
            >
              {PREFLIGHT_STATUS_OPTIONS.map((value) => (
                <option key={value || "all"} value={value}>
                  {value ? marketingPreflightStatusLabel(value) : "Все"}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {packs.length === 0 ? (
        <Alert variant="info">
          Пока нет публикаций. Возьмите утверждённую тему в работу на странице «Темы».
        </Alert>
      ) : filteredPacks.length === 0 ? (
        <Alert variant="info">Нет пакетов по выбранным фильтрам.</Alert>
      ) : (
        <div className="panel">
          <Table<MarketingPackSummary>
            rowKey={(row) => row.id}
            data={filteredPacks}
            emptyText="Нет публикаций"
            columns={[
              {
                key: "title",
                header: "Название",
                render: (row) => (
                  <Link to={`/workspace/${tenantSlug}/marketing/packs/${row.id}`}>
                    {row.title}
                  </Link>
                ),
              },
              {
                key: "topic",
                header: "Тема",
                render: (row) => row.topic?.title ?? "—",
              },
              {
                key: "status",
                header: "Статус",
                render: (row) => (
                  <span className="badge">{marketingPackStatusLabel(row.status)}</span>
                ),
              },
              {
                key: "approval",
                header: "Согласование",
                render: (row) => marketingApprovalStatusLabel(row.approval_status),
              },
              {
                key: "preflight",
                header: "Preflight",
                render: (row) => marketingPreflightStatusLabel(row.preflight_status),
              },
              {
                key: "updated",
                header: "Обновлён",
                render: (row) => formatDate(row.updated_at),
              },
              {
                key: "open",
                header: "",
                render: (row) => (
                  <Link
                    className="btn btn-secondary"
                    to={`/workspace/${tenantSlug}/marketing/packs/${row.id}`}
                  >
                    Открыть
                  </Link>
                ),
              },
            ]}
          />
          {hasFilters && (
            <p className="muted">
              Показано {filteredPacks.length} из {packs.length}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
