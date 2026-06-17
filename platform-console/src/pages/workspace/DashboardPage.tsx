import { WorkspaceManagerSection } from "../../components/workspace/WorkspaceManagerSection";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function DashboardPage() {
  const { isLoading } = useWorkspaceLabels();

  return (
    <WorkspaceManagerSection
      title="Dashboard"
      subtitle="Рабочий стол менеджера: лиды, сделки, действия и финансы."
      plannedStage="W2.2"
      labelsLoading={isLoading}
      widgets={[
        {
          title: "New leads",
          description: "Новые входящие заявки в начале воронки.",
        },
        {
          title: "Active deals",
          description: "Активные сделки по стадиям pipeline.",
        },
        {
          title: "Next actions",
          description: "Задачи и следующие шаги по заявкам.",
        },
        {
          title: "Payments / debts",
          description: "Оплаты, счета и просроченная задолженность.",
        },
      ]}
    />
  );
}
