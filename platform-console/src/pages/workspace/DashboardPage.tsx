import { Link } from "react-router-dom";
import { ApiError } from "../../api/client";
import { DashboardKpiCard } from "../../components/workspace/DashboardKpiCard";
import { Alert } from "../../components/ui/Alert";
import { Loading } from "../../components/ui/Loading";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";
import { formatMoney } from "../../workspace/formatters";
import { useDashboardData } from "../../workspace/useDashboardData";
import { ui } from "../../i18n/ruUi";

export function DashboardPage() {
  const { isLoading: labelsLoading } = useWorkspaceLabels();
  const { metrics, isLoading, error } = useDashboardData(!labelsLoading);

  if (labelsLoading || isLoading) {
    return <Loading text="Загрузка рабочего стола..." />;
  }

  if (error) {
    const message =
      error instanceof ApiError ? error.message : "Не удалось загрузить данные рабочего стола.";
    return (
      <div className="page">
        <PageHeader title={ui.dashboard} subtitle="Рабочий стол менеджера" />
        <Alert variant="error">{message}</Alert>
      </div>
    );
  }

  const { financeSummary, pipeline } = metrics;
  const currency = financeSummary?.currency ?? "RUB";

  return (
    <div className="page">
      <PageHeader
        title={ui.dashboard}
        subtitle={
          pipeline
            ? `Рабочий стол менеджера · ${pipeline.name}`
            : "Рабочий стол менеджера"
        }
      />

      <div className="workspace-kpi-grid">
        <DashboardKpiCard
          label="Новые заявки"
          value={String(metrics.newLeadsCount)}
          hint="Стадии: новая заявка, первичный контакт"
        />
        <DashboardKpiCard
          label="Активные заявки"
          value={String(metrics.activeDealsCount)}
          hint="Открытые заявки в нетерминальных стадиях"
        />
        <DashboardKpiCard
          label="Открытые счета"
          value={String(financeSummary?.open_invoices_count ?? 0)}
          hint={
            financeSummary
              ? formatMoney(financeSummary.total_outstanding, currency)
              : "—"
          }
        />
        <DashboardKpiCard
          label="Просроченная дебиторка"
          value={String(metrics.overdueReceivablesCount)}
          hint={
            financeSummary
              ? formatMoney(financeSummary.overdue_amount, currency)
              : "—"
          }
        />
        <DashboardKpiCard
          label="Документы на подпись"
          value={String(metrics.pendingDocumentsCount)}
          hint="Документы, ожидающие подписи"
        />
      </div>

      <div className="workspace-dashboard-links panel">
        <h3>Быстрые разделы</h3>
        <div className="workspace-quick-links">
          <Link to="../crm">{ui.crmPipeline}</Link>
          <Link to="../clients">{ui.clients}</Link>
          <Link to="../documents">{ui.documents}</Link>
          <Link to="../finance">{ui.finance}</Link>
        </div>
      </div>
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
