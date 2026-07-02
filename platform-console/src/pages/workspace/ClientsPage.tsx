import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { listParties } from "../../api/parties";
import { ApiError } from "../../api/client";
import { CreateClientModal } from "../../components/workspace/CreateClientModal";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { Table } from "../../components/ui/Table";
import type { Party } from "../../types/party";
import { getPartyRole } from "../../types/party";
import { formatCommonStatus, formatPartyType, ui } from "../../i18n/ruUi";
import { isPartyVisibleInClientsList } from "../../workspace/labelHelpers";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function ClientsPage() {
  const { tenantSlug = "" } = useParams();
  const navigate = useNavigate();
  const {
    clientsSectionTitle,
    defaultPartyRole,
    entityLabel,
    labels,
    partyRoleLabel,
    isLoading: labelsLoading,
  } = useWorkspaceLabels();
  const partyLabel = entityLabel("party", "Контрагент");
  const partyLabelLower = partyLabel.toLowerCase();
  const defaultRoleLabel = partyRoleLabel(defaultPartyRole, defaultPartyRole);
  const createButtonLabel = `Создать ${partyLabelLower}`;
  const [showCreateModal, setShowCreateModal] = useState(false);

  const partiesQuery = useQuery({
    queryKey: ["workspace-parties", "clients"],
    queryFn: () => listParties({ limit: 200 }),
    enabled: !labelsLoading,
  });

  const clients = useMemo(() => {
    return (partiesQuery.data ?? []).filter((party) =>
      isPartyVisibleInClientsList(getPartyRole(party), labels),
    );
  }, [labels, partiesQuery.data]);

  if (labelsLoading || partiesQuery.isLoading) {
    return <Loading text={`Загрузка ${partyLabelLower}...`} />;
  }

  if (partiesQuery.error) {
    const message =
      partiesQuery.error instanceof ApiError
        ? partiesQuery.error.message
        : `Не удалось загрузить список ${partyLabelLower}.`;
    return (
      <div className="page">
        <PageHeader title={ui.clients} subtitle={clientsSectionTitle} />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title={ui.clients}
        subtitle={`${clientsSectionTitle} · ${defaultRoleLabel}`}
        action={
          <button type="button" className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            {createButtonLabel}
          </button>
        }
      />

      {clients.length === 0 ? (
        <Alert variant="info">
          Пока нет записей. Нажмите «{createButtonLabel}», чтобы добавить первую.
        </Alert>
      ) : (
        <div className="panel">
          <Table<Party>
            rowKey={(row) => row.id}
            data={clients}
            emptyText={`Нет ${partyLabelLower}`}
            onRowClick={(row) => navigate(`/workspace/${tenantSlug}/clients/${row.id}`)}
            columns={[
              {
                key: "name",
                header: "Имя",
                render: (row) => row.display_name,
              },
              {
                key: "type",
                header: "Тип",
                render: (row) => formatPartyType(row.party_type),
              },
              {
                key: "status",
                header: "Статус",
                render: (row) => (
                  <span className={`badge badge-${row.status}`}>
                    {formatCommonStatus(row.status)}
                  </span>
                ),
              },
              {
                key: "contacts",
                header: "Контакты",
                render: (row) =>
                  row.contact_methods.length > 0
                    ? row.contact_methods
                        .slice(0, 2)
                        .map((c) => c.value)
                        .join(", ")
                    : "—",
              },
              {
                key: "link",
                header: "",
                render: (row) => (
                  <Link to={`/workspace/${tenantSlug}/clients/${row.id}`}>Открыть</Link>
                ),
              },
            ]}
          />
        </div>
      )}

      {showCreateModal && (
        <CreateClientModal onClose={() => setShowCreateModal(false)} />
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
