import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { listParties } from "../../api/parties";
import { ApiError } from "../../api/client";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { Table } from "../../components/ui/Table";
import { getPartyRole, type Party } from "../../types/party";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function ClientsPage() {
  const { tenantSlug = "" } = useParams();
  const navigate = useNavigate();
  const { clientsSectionTitle, partyRoleLabel, isLoading: labelsLoading } = useWorkspaceLabels();
  const guardianLabel = partyRoleLabel("guardian", "Родитель");

  const partiesQuery = useQuery({
    queryKey: ["workspace-parties"],
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
        <PageHeader title="Clients" subtitle={clientsSectionTitle} />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const guardians = (partiesQuery.data ?? []).filter(
    (party) => getPartyRole(party) === "guardian",
  );

  return (
    <div className="page">
      <PageHeader title="Clients" subtitle={`${clientsSectionTitle} · ${guardianLabel}`} />

      {guardians.length === 0 ? (
        <Alert variant="info">
          Пока нет клиентов с ролью «{guardianLabel}». Данные появятся после добавления
          контрагентов в tenant.
        </Alert>
      ) : (
        <div className="panel">
          <Table<Party>
            rowKey={(row) => row.id}
            data={guardians}
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
                render: (row) => row.party_type,
              },
              {
                key: "status",
                header: "Статус",
                render: (row) => (
                  <span className={`badge badge-${row.status}`}>{row.status}</span>
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
    </div>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        <p className="muted">{subtitle}</p>
      </div>
    </div>
  );
}
