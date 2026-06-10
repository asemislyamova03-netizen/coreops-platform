import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { listTenants } from "../api/tenants";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Loading } from "../components/ui/Loading";
import { Table } from "../components/ui/Table";
import type { Tenant } from "../types/tenant";

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "short",
  timeStyle: "short",
});

export function TenantsListPage() {
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({
    queryKey: ["tenants"],
    queryFn: listTenants,
  });

  if (isLoading) return <Loading />;
  if (error) {
    return <Alert variant="error">Не удалось загрузить tenants: {String(error)}</Alert>;
  }

  const tenants = data ?? [];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Tenants</h1>
          <p className="muted">Управление клиентскими организациями платформы</p>
        </div>
        <Link to="/tenants/new">
          <Button>Создать tenant</Button>
        </Link>
      </div>

      <Table<Tenant>
        data={tenants}
        rowKey={(row) => row.id}
        onRowClick={(row) => navigate(`/tenants/${row.id}`)}
        emptyText="Tenants пока нет. Создайте первый."
        columns={[
          { key: "name", header: "Название", render: (row) => row.name },
          { key: "slug", header: "Slug", render: (row) => row.slug },
          {
            key: "status",
            header: "Статус",
            render: (row) => <span className={`badge badge-${row.status}`}>{row.status}</span>,
          },
          {
            key: "created_at",
            header: "Создан",
            render: (row) => dateFormatter.format(new Date(row.created_at)),
          },
        ]}
      />
    </div>
  );
}
