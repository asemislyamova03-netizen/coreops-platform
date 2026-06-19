import { Alert } from "../ui/Alert";
import { Loading } from "../ui/Loading";
import { PlaceholderWidgetGrid } from "./PlaceholderWidgetGrid";

interface WorkspaceManagerSectionProps {
  title: string;
  subtitle: string;
  plannedStage: string;
  widgets: Array<{ title: string; description: string }>;
  labelsLoading?: boolean;
}

export function WorkspaceManagerSection({
  title,
  subtitle,
  plannedStage,
  widgets,
  labelsLoading = false,
}: WorkspaceManagerSectionProps) {
  if (labelsLoading) {
    return <Loading text="Загрузка настроек организации..." />;
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{title}</h1>
          <p className="muted">{subtitle}</p>
        </div>
      </div>

      <Alert variant="info">
        Основа рабочего места менеджера ({plannedStage}). Раздел готов к подключению API в
        следующих слайсах.
      </Alert>

      <PlaceholderWidgetGrid widgets={widgets} />
    </div>
  );
}
