import { WorkspaceManagerSection } from "../../components/workspace/WorkspaceManagerSection";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

export function ClientsPage() {
  const { clientsSectionTitle, isLoading } = useWorkspaceLabels();

  return (
    <WorkspaceManagerSection
      title="Clients"
      subtitle={clientsSectionTitle}
      plannedStage="W2.3"
      labelsLoading={isLoading}
      widgets={[
        {
          title: "Client list",
          description:
            "Список контрагентов (родителей/клиентов). Дети — внутри карточки клиента, не отдельный раздел.",
        },
      ]}
    />
  );
}
