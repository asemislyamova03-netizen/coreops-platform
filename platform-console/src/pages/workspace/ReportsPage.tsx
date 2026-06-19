import { ui } from "../../i18n/ruUi";
import { WorkspaceManagerSection } from "../../components/workspace/WorkspaceManagerSection";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function ReportsPage() {
  const { isLoading } = useWorkspaceLabels();

  return (
    <WorkspaceManagerSection
      title={ui.reports}
      subtitle="Базовая аналитика и отчёты менеджера."
      plannedStage="W3+"
      labelsLoading={isLoading}
      widgets={[
        {
          title: "Базовая аналитика",
          description: "Сводные показатели по воронке, конверсии и финансам.",
        },
      ]}
    />
  );
}
