import { Alert } from "../../../../components/ui/Alert";
import type { MarketingPackDetail } from "../../../../types/marketing";
import { formatDate } from "../../../../workspace/formatters";

interface PackDetailLogsTabProps {
  pack: MarketingPackDetail;
}

export function PackDetailLogsTab({ pack }: PackDetailLogsTabProps) {
  const logs = pack.publish_logs;

  return (
    <div className="marketing-pack-tab">
      <h3>Logs</h3>
      <p className="muted">Read-only журнал публикаций из pack detail.</p>

      {logs.length === 0 ? (
        <Alert variant="info">Записей журнала пока нет.</Alert>
      ) : (
        <div className="panel">
          <ul className="marketing-logs-list">
            {logs.map((log) => (
              <li key={log.id}>
                <strong>{log.channel}</strong> · {log.action} · {log.status}
                {log.published_at ? ` · ${formatDate(log.published_at)}` : ""}
                {" · "}
                {formatDate(log.created_at)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
