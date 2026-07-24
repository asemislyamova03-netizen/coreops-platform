import { useQuery } from "@tanstack/react-query";
import { listMarketingPublishingConnections } from "../../../api/marketingPublishingConnections";
import { ApiError } from "../../../api/client";
import { Alert } from "../../../components/ui/Alert";
import { Loading } from "../../../components/ui/Loading";
import { Table } from "../../../components/ui/Table";
import { ui } from "../../../i18n/ruUi";
import type { MarketingPublishingConnection } from "../../../types/marketingPublishingConnection";
import { formatDate } from "../../../workspace/formatters";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import {
  firstBlockingError,
  isModuleDisabled,
  moduleDisabledMessage,
} from "../../../workspace/moduleErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";
import {
  CONNECTIONS_EMPTY_STATE,
  CONNECTIONS_PAGE_SUBTITLE,
  CONNECTIONS_WIZARD_NEXT_STAGE_NOTE,
  publishingConnectionErrorDisplay,
  publishingConnectionStatusLabel,
  publishingProviderLabel,
  publishingTokenStatusLabel,
} from "./marketingConnectionLabels";

function hasSecretLabel(hasSecret: boolean): string {
  return hasSecret ? "да" : "нет";
}

export function MarketingConnectionsPage() {
  const { isLoading: labelsLoading } = useWorkspaceLabels();

  const connectionsQuery = useQuery({
    queryKey: ["marketing-publishing-connections"],
    queryFn: listMarketingPublishingConnections,
    enabled: !labelsLoading,
  });

  if (labelsLoading || connectionsQuery.isLoading) {
    return <Loading text="Загрузка подключений..." />;
  }

  const marketingDisabled = isModuleDisabled("marketing", connectionsQuery.error);
  const error = firstBlockingError(connectionsQuery.error);

  if (marketingDisabled && !error) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingConnections}
          subtitle={CONNECTIONS_PAGE_SUBTITLE}
        />
        <Alert variant="info">{moduleDisabledMessage("marketing")}</Alert>
      </div>
    );
  }

  if (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Не удалось загрузить список подключений.";
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingConnections}
          subtitle={CONNECTIONS_PAGE_SUBTITLE}
        />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const connections = connectionsQuery.data ?? [];

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingConnections}
        subtitle={CONNECTIONS_PAGE_SUBTITLE}
      />

      <Alert variant="info">{CONNECTIONS_WIZARD_NEXT_STAGE_NOTE}</Alert>

      {connections.length === 0 ? (
        <div className="panel">
          <p>{CONNECTIONS_EMPTY_STATE}</p>
          <p className="muted">{CONNECTIONS_WIZARD_NEXT_STAGE_NOTE}</p>
        </div>
      ) : (
        <div className="panel">
          <Table<MarketingPublishingConnection>
            rowKey={(row) => row.id}
            emptyText={CONNECTIONS_EMPTY_STATE}
            columns={[
              {
                key: "provider",
                header: "Провайдер",
                render: (row) => publishingProviderLabel(row.provider),
              },
              {
                key: "account",
                header: "Аккаунт",
                render: (row) => row.account_display_name || "—",
              },
              {
                key: "status",
                header: "Статус подключения",
                render: (row) => publishingConnectionStatusLabel(row.status),
              },
              {
                key: "token_status",
                header: "Статус токена",
                render: (row) => publishingTokenStatusLabel(row.token_status),
              },
              {
                key: "has_secret",
                header: "Секрет сохранён",
                render: (row) => hasSecretLabel(row.has_secret),
              },
              {
                key: "last_checked_at",
                header: "Последняя проверка",
                render: (row) => formatDate(row.last_checked_at),
              },
              {
                key: "expires_at",
                header: "Срок действия",
                render: (row) => formatDate(row.expires_at),
              },
              {
                key: "error",
                header: "Ошибка",
                render: (row) =>
                  publishingConnectionErrorDisplay(
                    row.last_error_code,
                    row.last_error_message_redacted,
                  ),
              },
            ]}
            data={connections}
          />
        </div>
      )}
    </div>
  );
}
