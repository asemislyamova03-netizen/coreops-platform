import { Alert } from "../../../../components/ui/Alert";
import {
  HISTORICAL_PUBLICATION_NOTE,
  MARKETING_PUBLISH_DISABLED_MESSAGE,
} from "../marketingLabels";

interface PackDetailPublishTabProps {
  hasHistoricalPublication: boolean;
}

export function PackDetailPublishTab({
  hasHistoricalPublication,
}: PackDetailPublishTabProps) {
  return (
    <div className="marketing-pack-tab">
      <h3>Publish</h3>
      <Alert variant="info">{MARKETING_PUBLISH_DISABLED_MESSAGE}</Alert>
      {hasHistoricalPublication && <Alert variant="info">{HISTORICAL_PUBLICATION_NOTE}</Alert>}
      <p className="muted">
        На этом этапе нет действия публикации. Export, Margosya и live publish — отдельный gate.
      </p>
    </div>
  );
}
