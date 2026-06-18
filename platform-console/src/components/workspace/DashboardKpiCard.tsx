interface DashboardKpiCardProps {
  label: string;
  value: string;
  hint?: string;
}

export function DashboardKpiCard({ label, value, hint }: DashboardKpiCardProps) {
  return (
    <div className="panel workspace-kpi-card">
      <p className="workspace-kpi-label">{label}</p>
      <p className="workspace-kpi-value">{value}</p>
      {hint && <p className="muted workspace-kpi-hint">{hint}</p>}
    </div>
  );
}
