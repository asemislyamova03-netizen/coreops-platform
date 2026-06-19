import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
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
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

const DEFAULT_CLIENT_PARTY_ROLE = "client";

/** W3.1 creates `client`; legacy seeded `guardian` rows stay visible in the list. */
function isVisibleClientParty(party: Party): boolean {
  const role = getPartyRole(party);
  return role === null || role === DEFAULT_CLIENT_PARTY_ROLE || role === "guardian";
}

export function ClientsPage() {
  const { tenantSlug = "" } = useParams();
  const navigate = useNavigate();
  const { clientsSectionTitle, partyRoleLabel, isLoading: labelsLoading } = useWorkspaceLabels();
  const clientRoleLabel = partyRoleLabel(DEFAULT_CLIENT_PARTY_ROLE, "Клиент");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const partiesQuery = useQuery({
    queryKey: ["workspace-parties", "clients"],
    queryFn: () => listParties({ limit: 200 }),
    enabled: !labelsLoading,
  });

  if (labelsLoading || partiesQuery.isLoading) {
    return <Loading text="Загрузка клиентов..." />;
  }

  if (partiesQuery.error) {
    const message =
      partiesQuery.error instanceof ApiError
        ? partiesQuery.error.message
        : "Не удалось загрузить список клиентов.";
    return (
      <div className="page">
        <PageHeader title={ui.clients} subtitle={clientsSectionTitle} />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const clients = (partiesQuery.data ?? []).filter(isVisibleClientParty);

  return (
    <div className="page">
      <PageHeader
        title={ui.clients}
        subtitle={`${clientsSectionTitle} · ${clientRoleLabel}`}
        action={
          <button type="button" className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            Создать клиента
          </button>
        }
      />

      {clients.length === 0 ? (
        <Alert variant="info">
          Пока нет клиентов. Нажмите «Создать клиента», чтобы добавить первого.
        </Alert>
      ) : (
        <div className="panel">
          <Table<Party>
            rowKey={(row) => row.id}
            data={clients}
            emptyText="Нет клиентов"
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
