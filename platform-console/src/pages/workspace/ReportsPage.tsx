import { WorkspaceManagerSection } from "../../components/workspace/WorkspaceManagerSection";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function ReportsPage() {
  const { isLoading } = useWorkspaceLabels();

  return (
    <WorkspaceManagerSection
      title="Reports"
      subtitle="Базовая аналитика и отчёты менеджера."
      plannedStage="W3+"
      labelsLoading={isLoading}
      widgets={[
        {
          title: "Basic analytics",
          description: "Сводные показатели по воронке, конверсии и финансам.",
        },
      ]}
    />
  );
}
