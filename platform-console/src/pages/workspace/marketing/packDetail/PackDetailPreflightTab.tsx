import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { runMarketingPreflight } from "../../../../api/marketing";
import { Alert } from "../../../../components/ui/Alert";
import type { MarketingPackDetail, MarketingPreflightResponse } from "../../../../types/marketing";
import { formatDate } from "../../../../workspace/formatters";
import { formatMarketingApiError } from "./marketingErrors";

interface PackDetailPreflightTabProps {
  packId: string;
  pack: MarketingPackDetail;
}

export function PackDetailPreflightTab({ packId, pack }: PackDetailPreflightTabProps) {
  const queryClient = useQueryClient();
  const [lastReport, setLastReport] = useState<MarketingPreflightResponse | null>(null);

  const preflightMutation = useMutation({
    mutationFn: () => runMarketingPreflight(packId),
    onSuccess: async (report) => {
      setLastReport(report);
      await queryClient.invalidateQueries({ queryKey: ["marketing-pack", packId] });
    },
  });

  const report = lastReport;
  const errors = report?.errors ?? [];
  const warnings = report?.warnings ?? [];

  return (
    <div className="marketing-pack-tab">
      <h3>Preflight</h3>
      <p className="muted">Проверки перед согласованием pack.</p>

      <dl className="detail-list marketing-status-block">
        <dt>preflight_status</dt>
        <dd>{pack.preflight_status}</dd>
        <dt>pack status</dt>
        <dd>{pack.status}</dd>
        <dt>approval_status</dt>
        <dd>{pack.approval_status}</dd>
        {pack.preflight_at && (
          <>
            <dt>preflight_at</dt>
            <dd>{formatDate(pack.preflight_at)}</dd>
          </>
        )}
      </dl>

      <button
        type="button"
        className="btn btn-primary"
        disabled={preflightMutation.isPending}
        onClick={() => preflightMutation.mutate()}
      >
        {preflightMutation.isPending ? "Проверка..." : "Запустить preflight"}
      </button>

      {preflightMutation.isError && (
        <Alert variant="error">
          {formatMarketingApiError(preflightMutation.error, "Не удалось запустить preflight.")}
        </Alert>
      )}

      {report && (
        <div className="marketing-preflight-report panel">
          <h4>
            Отчёт preflight · {report.status} · {formatDate(report.checked_at)}
          </h4>

          {errors.length === 0 && warnings.length === 0 ? (
            <Alert variant="info">Ошибок и предупреждений нет.</Alert>
          ) : (
            <>
              {errors.length > 0 && (
                <div className="marketing-issue-list">
                  <h5>Errors</h5>
                  <ul>
                    {errors.map((issue, index) => (
                      <li key={`${issue.code}-${index}`}>
                        <strong>{issue.code}</strong>
                        {issue.channel ? ` (${issue.channel})` : ""}: {issue.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {warnings.length > 0 && (
                <div className="marketing-issue-list">
                  <h5>Warnings</h5>
                  <ul>
                    {warnings.map((issue, index) => (
                      <li key={`${issue.code}-${index}`}>
                        <strong>{issue.code}</strong>
                        {issue.channel ? ` (${issue.channel})` : ""}: {issue.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {report.checks.length > 0 && (
            <div className="marketing-check-list">
              <h5>Checks</h5>
              <ul>
                {report.checks.map((check, index) => (
                  <li key={`${check.code}-${index}`}>
                    {check.passed ? "✓" : "✗"} {check.code}
                    {check.channel ? ` (${check.channel})` : ""}
                    {check.message ? ` — ${check.message}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
