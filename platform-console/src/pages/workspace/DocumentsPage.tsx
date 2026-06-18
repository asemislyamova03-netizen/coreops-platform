import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { listDocuments } from "../../api/documents";
import { ApiError } from "../../api/client";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { Table } from "../../components/ui/Table";
import type { Document } from "../../types/document";
import { getDocumentSignatureHint } from "../../workspace/documentHelpers";
import { formatDate } from "../../workspace/formatters";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function DocumentsPage() {
  const { tenantSlug = "" } = useParams();
  const { entityLabel, isLoading: labelsLoading } = useWorkspaceLabels();
  const documentLabel = entityLabel("document", "Документ");

  const documentsQuery = useQuery({
    queryKey: ["workspace-documents"],
    queryFn: () => listDocuments({ limit: 200 }),
    enabled: !labelsLoading,
  });

  if (labelsLoading || documentsQuery.isLoading) {
    return <Loading text="Загрузка документов..." />;
  }

  if (documentsQuery.error) {
    const message =
      documentsQuery.error instanceof ApiError
        ? documentsQuery.error.message
        : "Не удалось загрузить документы.";
    return (
      <div className="page">
        <PageHeader title="Documents" subtitle={documentLabel} />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const documents = documentsQuery.data ?? [];

  return (
    <div className="page">
      <PageHeader
        title="Documents"
        subtitle={`${documentLabel}, договоры и заявления · read-only`}
      />

      {documents.length === 0 ? (
        <Alert variant="info">Пока нет документов в tenant.</Alert>
      ) : (
        <div className="panel">
          <Table<Document>
            rowKey={(row) => row.id}
            data={documents}
            emptyText="Нет документов"
            columns={[
              {
                key: "title",
                header: "Название",
                render: (row) => row.title,
              },
              {
                key: "status",
                header: "Статус",
                render: (row) => (
                  <span className={`badge badge-${row.status}`}>{row.status}</span>
                ),
              },
              {
                key: "signature",
                header: "Подпись",
                render: (row) => getDocumentSignatureHint(row),
              },
              {
                key: "party",
                header: "Клиент",
                render: (row) =>
                  row.party_id ? (
                    <Link to={`/workspace/${tenantSlug}/clients/${row.party_id}`}>
                      <code>{row.party_id.slice(0, 8)}…</code>
                    </Link>
                  ) : (
                    "—"
                  ),
              },
              {
                key: "work_item",
                header: "Work item",
                render: (row) =>
                  row.work_item_id ? <code>{row.work_item_id.slice(0, 8)}…</code> : "—",
              },
              {
                key: "updated",
                header: "Обновлён",
                render: (row) => formatDate(row.updated_at),
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
