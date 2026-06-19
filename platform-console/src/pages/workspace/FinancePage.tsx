import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  getFinanceSummary,
  listInvoices,
  listPayments,
  listReceivables,
} from "../../api/finance";
import { ApiError } from "../../api/client";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { Table } from "../../components/ui/Table";
import type { Invoice, Payment, Receivable } from "../../types/finance";
import { formatMoney } from "../../workspace/formatters";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function FinancePage() {
  const { tenantSlug = "" } = useParams();
  const { entityLabel, isLoading: labelsLoading } = useWorkspaceLabels();
  const invoiceLabel = entityLabel("invoice", "Счёт");
  const paymentLabel = entityLabel("payment", "Оплата");

  const summaryQuery = useQuery({
    queryKey: ["workspace-finance-summary"],
    queryFn: () => getFinanceSummary(),
    enabled: !labelsLoading,
  });

  const invoicesQuery = useQuery({
    queryKey: ["workspace-finance-invoices"],
    queryFn: () => listInvoices({ limit: 200 }),
    enabled: !labelsLoading,
  });

  const paymentsQuery = useQuery({
    queryKey: ["workspace-finance-payments"],
    queryFn: () => listPayments({ limit: 200 }),
    enabled: !labelsLoading,
  });

  const receivablesQuery = useQuery({
    queryKey: ["workspace-finance-receivables"],
    queryFn: listReceivables,
    enabled: !labelsLoading,
  });

  const isLoading =
    labelsLoading ||
    summaryQuery.isLoading ||
    invoicesQuery.isLoading ||
    paymentsQuery.isLoading ||
    receivablesQuery.isLoading;

  if (isLoading) {
    return <Loading text="Загрузка финансов..." />;
  }

  const error =
    summaryQuery.error ??
    invoicesQuery.error ??
    paymentsQuery.error ??
    receivablesQuery.error;

  if (error) {
    const message =
      error instanceof ApiError ? error.message : "Не удалось загрузить финансовые данные.";
    return (
      <div className="page">
        <PageHeader title="Finance" subtitle={`${invoiceLabel}, ${paymentLabel}`} />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const summary = summaryQuery.data;
  const currency = summary?.currency ?? "RUB";
  const invoices = invoicesQuery.data ?? [];
  const payments = paymentsQuery.data ?? [];
  const receivables = receivablesQuery.data ?? [];

  return (
    <div className="page">
      <PageHeader
        title="Finance"
        subtitle={`${invoiceLabel}, ${paymentLabel}, задолженность · read-only`}
      />

      {summary && (
        <div className="workspace-finance-summary">
          <SummaryCard label="Выставлено" value={formatMoney(summary.total_invoiced, currency)} />
          <SummaryCard label="Оплачено" value={formatMoney(summary.total_paid, currency)} />
          <SummaryCard
            label="Дебиторка"
            value={formatMoney(summary.total_outstanding, currency)}
            hint={`${summary.open_invoices_count} открытых`}
          />
          <SummaryCard
            label="Просрочено"
            value={formatMoney(summary.overdue_amount, currency)}
            hint={`${summary.overdue_invoices_count} счетов`}
          />
        </div>
      )}

      <FinanceSection title={invoiceLabel}>
        {invoices.length === 0 ? (
          <p className="muted">Нет счетов.</p>
        ) : (
          <Table<Invoice>
            rowKey={(row) => row.id}
            data={invoices}
            columns={[
              { key: "number", header: "№", render: (r) => r.invoice_number },
              { key: "status", header: "Статус", render: (r) => r.status },
              {
                key: "party",
                header: "Клиент",
                render: (r) => (
                  <Link to={`/workspace/${tenantSlug}/clients/${r.party_id}`}>
                    <code>{r.party_id.slice(0, 8)}…</code>
                  </Link>
                ),
              },
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
              { key: "due", header: "Срок", render: (r) => r.due_date ?? "—" },
            ]}
          />
        )}
      </FinanceSection>

      <FinanceSection title={paymentLabel}>
        {payments.length === 0 ? (
          <p className="muted">Нет оплат.</p>
        ) : (
          <Table<Payment>
            rowKey={(row) => row.id}
            data={payments}
            columns={[
              { key: "number", header: "№", render: (r) => r.payment_number },
              { key: "status", header: "Статус", render: (r) => r.status },
              {
                key: "party",
                header: "Клиент",
                render: (r) =>
                  r.party_id ? (
                    <Link to={`/workspace/${tenantSlug}/clients/${r.party_id}`}>
                      <code>{r.party_id.slice(0, 8)}…</code>
                    </Link>
                  ) : (
                    "—"
                  ),
              },
              {
                key: "amount",
                header: "Сумма",
                render: (r) => formatMoney(r.amount, r.currency),
              },
              { key: "date", header: "Дата", render: (r) => r.payment_date },
            ]}
          />
        )}
      </FinanceSection>

      <FinanceSection title="Дебиторка (receivables)">
        {receivables.length === 0 ? (
          <p className="muted">Нет открытой дебиторки.</p>
        ) : (
          <Table<Receivable>
            rowKey={(row) => row.invoice_id}
            data={receivables}
            columns={[
              { key: "number", header: "№", render: (r) => r.invoice_number },
              { key: "status", header: "Статус", render: (r) => r.status },
              {
                key: "party",
                header: "Клиент",
                render: (r) => (
                  <Link to={`/workspace/${tenantSlug}/clients/${r.party_id}`}>
                    <code>{r.party_id.slice(0, 8)}…</code>
                  </Link>
                ),
              },
              {
                key: "balance",
                header: "Долг",
                render: (r) => formatMoney(r.balance_due, r.currency),
              },
              {
                key: "overdue",
                header: "Просрочка",
                render: (r) => (r.is_overdue ? "Да" : "—"),
              },
              { key: "due", header: "Срок", render: (r) => r.due_date ?? "—" },
            ]}
          />
        )}
      </FinanceSection>
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

function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="panel workspace-kpi-card">
      <p className="workspace-kpi-label">{label}</p>
      <p className="workspace-kpi-value">{value}</p>
      {hint && <p className="muted workspace-kpi-hint">{hint}</p>}
    </div>
  );
}

function FinanceSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="panel workspace-detail-section">
      <h3>{title}</h3>
      {children}
    </div>
  );
}
