import { WorkspaceManagerSection } from "../../components/workspace/WorkspaceManagerSection";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function FinancePage() {
  const { entityLabel, isLoading } = useWorkspaceLabels();
  const invoice = entityLabel("invoice", "Счёт");
  const payment = entityLabel("payment", "Оплата");

  return (
    <WorkspaceManagerSection
      title="Finance"
      subtitle={`${invoice}, ${payment}, задолженность`}
      plannedStage="W2.5"
      labelsLoading={isLoading}
      widgets={[
        {
          title: "Invoices",
          description: "Список счетов tenant.",
        },
        {
          title: "Payments",
          description: "Поступившие оплаты и аллокации.",
        },
        {
          title: "Debts",
          description: "Дебиторка и просрочки (receivables).",
        },
      ]}
    />
  );
}
