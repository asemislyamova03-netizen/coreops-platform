import { WorkspaceManagerSection } from "../../components/workspace/WorkspaceManagerSection";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function DocumentsPage() {
  const { entityLabel, isLoading } = useWorkspaceLabels();
  const documentLabel = entityLabel("document", "Документ");

  return (
    <WorkspaceManagerSection
      title="Documents"
      subtitle={`${documentLabel}, договоры и заявления`}
      plannedStage="W2.5"
      labelsLoading={isLoading}
      widgets={[
        {
          title: "Contracts & documents",
          description: "Договоры, заявления и статусы подписи.",
        },
      ]}
    />
  );
}
