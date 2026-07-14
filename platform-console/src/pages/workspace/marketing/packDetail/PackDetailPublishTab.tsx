import { Alert } from "../../../../components/ui/Alert";
import { MARKETING_PUBLISH_DISABLED_MESSAGE } from "../marketingLabels";

export function PackDetailPublishTab() {
  return (
    <div className="marketing-pack-tab">
      <h3>Publish</h3>
      <Alert variant="info">{MARKETING_PUBLISH_DISABLED_MESSAGE}</Alert>
      <p className="muted">
        На этом этапе нет действия публикации. Export, Margosya и live publish — отдельный gate.
      </p>
    </div>
  );
}
