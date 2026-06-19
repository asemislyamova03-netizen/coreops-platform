import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { listDocuments } from "../../api/documents";
import { listInvoices, listPayments } from "../../api/finance";
import { getParty } from "../../api/parties";
import { listPipelines, listWorkItems } from "../../api/workflows";
import { ApiError } from "../../api/client";
import { WorkItemActivityComposer } from "../../components/workspace/WorkItemActivityComposer";
import { WorkItemStageSelect } from "../../components/workspace/WorkItemStageSelect";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { Table } from "../../components/ui/Table";
import type { Document } from "../../types/document";
import type { Invoice, Payment } from "../../types/finance";
import type { PipelineStage, WorkItem } from "../../types/workflows";
import { formatDate, formatMoney } from "../../workspace/formatters";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";
import { getPartyRole } from "../../types/party";

type TabId = "overview" | "deals" | "documents" | "finance";

function queryErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function ClientDetailPage() {
  const { tenantSlug = "", partyId = "" } = useParams();
  const { partyRoleLabel, entityLabel, isLoading: labelsLoading } = useWorkspaceLabels();
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const partyQuery = useQuery({
    queryKey: ["workspace-party", partyId],
    queryFn: () => getParty(partyId),
    enabled: Boolean(partyId) && !labelsLoading,
  });

  const workItemsQuery = useQuery({
    queryKey: ["workspace-party-work-items", partyId],
    queryFn: () => listWorkItems({ primary_party_id: partyId, limit: 200 }),
    enabled: Boolean(partyId) && !labelsLoading,
  });

  const invoicesQuery = useQuery({
    queryKey: ["workspace-party-invoices", partyId],
    queryFn: () => listInvoices({ party_id: partyId, limit: 100 }),
    enabled: Boolean(partyId) && !labelsLoading,
  });

  const paymentsQuery = useQuery({
    queryKey: ["workspace-party-payments", partyId],
    queryFn: () => listPayments({ party_id: partyId, limit: 100 }),
    enabled: Boolean(partyId) && !labelsLoading,
  });

  const documentsQuery = useQuery({
    queryKey: ["workspace-party-documents", partyId],
    queryFn: () => listDocuments({ party_id: partyId, limit: 200 }),
    enabled: Boolean(partyId) && !labelsLoading,
  });

  const pipelinesQuery = useQuery({
    queryKey: ["workspace-pipelines"],
    queryFn: listPipelines,
    enabled: Boolean(partyId) && !labelsLoading,
  });

  if (labelsLoading || partyQuery.isLoading) {
    return <Loading text="Загрузка карточки клиента..." />;
  }

  if (partyQuery.error || !partyQuery.data) {
    const message = queryErrorMessage(partyQuery.error, "Клиент не найден.");
    return (
      <div className="page">
        <Alert variant="error">{message}</Alert>
        <Link to={`/workspace/${tenantSlug}/clients`}>← К списку клиентов</Link>
      </div>
    );
  }

  const party = partyQuery.data;
  const role = getPartyRole(party);
  const roleLabel = role ? partyRoleLabel(role, role) : "—";
  const workItemLabel = entityLabel("work_item", "Заявка");

  const relatedDeals = workItemsQuery.data ?? [];
  const partyDocuments = documentsQuery.data ?? [];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <Link to={`/workspace/${tenantSlug}/clients`} className="muted workspace-back-link">
            ← Clients
          </Link>
          <h1>{party.display_name}</h1>
          <p className="muted">
            {roleLabel} · <span className={`badge badge-${party.status}`}>{party.status}</span>
          </p>
        </div>
      </div>

      <div className="tabs workspace-detail-tabs">
        {(
          [
            ["overview", "Overview"],
            ["deals", workItemLabel],
            ["documents", "Documents"],
            ["finance", "Finance"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={activeTab === id ? "tab active" : "tab"}
            onClick={() => setActiveTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="panel">
          <dl className="detail-list">
            <dt>Тип</dt>
            <dd>{party.party_type}</dd>
            <dt>Роль</dt>
            <dd>{roleLabel}</dd>
            <dt>Контакты</dt>
            <dd>
              {party.contact_methods.length === 0
                ? "—"
                : party.contact_methods.map((c) => (
                    <div key={c.id}>
                      {c.method_type}: {c.value}
                      {c.is_primary ? " (primary)" : ""}
                    </div>
                  ))}
            </dd>
            <dt>Адреса</dt>
            <dd>
              {party.addresses.length === 0
                ? "—"
                : party.addresses.map((a) => (
                    <div key={a.id}>
                      {[a.city, a.line1].filter(Boolean).join(", ") || "—"}
                    </div>
                  ))}
            </dd>
          </dl>
        </div>
      )}

      {activeTab === "deals" && (
        <DealsTab
          deals={relatedDeals}
          workItemLabel={workItemLabel}
          isLoading={workItemsQuery.isLoading}
          error={workItemsQuery.error}
          pipelines={pipelinesQuery.data ?? []}
          pipelinesLoading={pipelinesQuery.isLoading}
          pipelinesError={pipelinesQuery.error}
        />
      )}

      {activeTab === "documents" && (
        <DocumentsTab
          documents={partyDocuments}
          isLoading={documentsQuery.isLoading}
          error={documentsQuery.error}
        />
      )}

      {activeTab === "finance" && (
        <FinanceTab
          invoices={invoicesQuery.data ?? []}
          payments={paymentsQuery.data ?? []}
          invoicesLoading={invoicesQuery.isLoading}
          paymentsLoading={paymentsQuery.isLoading}
          invoicesError={invoicesQuery.error}
          paymentsError={paymentsQuery.error}
        />
      )}
    </div>
  );
}

function DealsTab({
  deals,
  workItemLabel,
  isLoading,
  error,
  pipelines,
  pipelinesLoading,
  pipelinesError,
}: {
  deals: WorkItem[];
  workItemLabel: string;
  isLoading: boolean;
  error: unknown;
  pipelines: Array<{ id: string; stages: PipelineStage[] }>;
  pipelinesLoading: boolean;
  pipelinesError: unknown;
}) {
  if (isLoading || pipelinesLoading) {
    return <Loading text="Загрузка заявок..." />;
  }
  if (error) {
    return (
      <Alert variant="error">
        {queryErrorMessage(error, "Не удалось загрузить связанные заявки.")}
      </Alert>
    );
  }
  if (pipelinesError) {
    return (
      <Alert variant="error">
        {queryErrorMessage(pipelinesError, "Не удалось загрузить воронки.")}
      </Alert>
    );
  }
  if (deals.length === 0) {
    return <Alert variant="info">Нет связанных {workItemLabel.toLowerCase()}.</Alert>;
  }

  const stagesByPipeline = new Map(
    pipelines.map((pipeline) => [pipeline.id, pipeline.stages] as const),
  );

  return (
    <div className="workspace-deals-list">
      {deals.map((deal) => {
        const stages = stagesByPipeline.get(deal.pipeline_id) ?? [];
        return (
          <div key={deal.id} className="panel workspace-deal-panel">
            <div className="workspace-deal-header">
              <h3>{deal.title}</h3>
              <span className={`badge badge-${deal.status}`}>{deal.status}</span>
            </div>
            <p className="muted workspace-deal-meta">{deal.work_item_type}</p>
            <WorkItemStageSelect workItem={deal} stages={stages} />
            <WorkItemActivityComposer workItemId={deal.id} />
          </div>
        );
      })}
    </div>
  );
}

function DocumentsTab({
  documents,
  isLoading,
  error,
}: {
  documents: Document[];
  isLoading: boolean;
  error: unknown;
}) {
  if (isLoading) {
    return <Loading text="Загрузка документов..." />;
  }
  if (error) {
    return (
      <Alert variant="error">
        {queryErrorMessage(error, "Не удалось загрузить документы клиента.")}
      </Alert>
    );
  }
  if (documents.length === 0) {
    return <Alert variant="info">Нет документов для этого клиента.</Alert>;
  }
  return (
    <div className="panel">
      <Table<Document>
        rowKey={(row) => row.id}
        data={documents}
        columns={[
          { key: "title", header: "Название", render: (r) => r.title },
          { key: "status", header: "Статус", render: (r) => r.status },
          {
            key: "work_item",
            header: "Work item",
            render: (r) => (r.work_item_id ? <code>{r.work_item_id}</code> : "—"),
          },
        ]}
      />
    </div>
  );
}

function FinanceTab({
  invoices,
  payments,
  invoicesLoading,
  paymentsLoading,
  invoicesError,
  paymentsError,
}: {
  invoices: Invoice[];
  payments: Payment[];
  invoicesLoading: boolean;
  paymentsLoading: boolean;
  invoicesError: unknown;
  paymentsError: unknown;
}) {
  return (
    <>
      <div className="panel workspace-detail-section">
        <h3>Счета</h3>
        {invoicesLoading ? (
          <Loading text="Загрузка счетов..." />
        ) : invoicesError ? (
          <Alert variant="error">
            {queryErrorMessage(invoicesError, "Не удалось загрузить счета.")}
          </Alert>
        ) : invoices.length === 0 ? (
          <p className="muted">Нет счетов.</p>
        ) : (
          <Table<Invoice>
            rowKey={(row) => row.id}
            data={invoices}
            columns={[
              { key: "number", header: "№", render: (r) => r.invoice_number },
              { key: "status", header: "Статус", render: (r) => r.status },
              {
                key: "total",
                header: "Сумма",
                render: (r) => formatMoney(r.total, r.currency),
              },
              {
                key: "balance",
                header: "Долг",
                render: (r) => formatMoney(r.balance_due, r.currency),
              },
            ]}
          />
        )}
      </div>
      <div className="panel workspace-detail-section">
        <h3>Оплаты</h3>
        {paymentsLoading ? (
          <Loading text="Загрузка оплат..." />
        ) : paymentsError ? (
          <Alert variant="error">
            {queryErrorMessage(paymentsError, "Не удалось загрузить оплаты.")}
          </Alert>
        ) : payments.length === 0 ? (
          <p className="muted">Нет оплат.</p>
        ) : (
          <Table<Payment>
            rowKey={(row) => row.id}
            data={payments}
            columns={[
              { key: "number", header: "№", render: (r) => r.payment_number },
              { key: "status", header: "Статус", render: (r) => r.status },
              {
                key: "amount",
                header: "Сумма",
                render: (r) => formatMoney(r.amount, r.currency),
              },
              { key: "date", header: "Дата", render: (r) => formatDate(r.payment_date) },
            ]}
          />
        )}
      </div>
    </>
  );
}
