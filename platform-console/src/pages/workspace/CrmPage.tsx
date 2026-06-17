import { WorkspaceManagerSection } from "../../components/workspace/WorkspaceManagerSection";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function CrmPage() {
  const { crmSectionTitle, isLoading } = useWorkspaceLabels();

  return (
    <WorkspaceManagerSection
      title="CRM"
      subtitle={crmSectionTitle}
      plannedStage="W2.2"
      labelsLoading={isLoading}
      widgets={[
        {
          title: "Pipeline",
          description: "Воронка продаж/поступления и стадии заявок.",
        },
      ]}
    />
  );
}
