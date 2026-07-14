import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { runMarketingPreflight } from "../../../../api/marketing";
import { Alert } from "../../../../components/ui/Alert";
import type {
  MarketingPackDetail,
  MarketingPreflightResponse,
} from "../../../../types/marketing";
import { formatDate } from "../../../../workspace/formatters";
import { marketingChannelLabel, marketingPreflightStatusLabel } from "../marketingLabels";
import {
  channelCheckStatusLabel,
  formatPreflightIssueLine,
  normalizePreflightReport,
  preflightCheckLabel,
  preflightSummarySubtitle,
  preflightSummaryTitle,
  resolvePreflightSummaryTone,
  topicContextDisplayRows,
  topicContextHasAnyFilled,
  type NormalizedPreflightReport,
} from "../marketingPreflight";
import { formatMarketingApiError } from "./marketingErrors";

interface PackDetailPreflightTabProps {
  packId: string;
  pack: MarketingPackDetail;
}

function alertVariantForTone(
  tone: ReturnType<typeof resolvePreflightSummaryTone>,
): "error" | "info" | "success" {
  if (tone === "failed") return "error";
  if (tone === "passed") return "success";
  return "info";
}

function ChecklistMark({ passed, isBlockerRelated }: { passed: boolean; isBlockerRelated: boolean }) {
  if (passed) return <span className="marketing-check-mark is-pass">✓</span>;
  if (isBlockerRelated) return <span className="marketing-check-mark is-fail">✗</span>;
  return <span className="marketing-check-mark is-warn">!</span>;
}

export function PackDetailPreflightTab({ packId, pack }: PackDetailPreflightTabProps) {
  const queryClient = useQueryClient();
  const storedReport = useMemo(
    () => normalizePreflightReport(pack.preflight_report_json),
    [pack.preflight_report_json],
  );
  const [liveReport, setLiveReport] = useState<NormalizedPreflightReport | null>(null);

  const preflightMutation = useMutation({
    mutationFn: () => runMarketingPreflight(packId),
    onSuccess: async (response: MarketingPreflightResponse) => {
      setLiveReport(normalizePreflightReport(response));
      await queryClient.invalidateQueries({ queryKey: ["marketing-pack", packId] });
    },
  });

  const report = liveReport ?? (storedReport.hasReport ? storedReport : null);
  const tone = resolvePreflightSummaryTone(report);
  const blockers = report?.blockers ?? [];
  const warnings = report?.warnings ?? [];
  const checklist = report?.checklist ?? [];
  const blockerCodes = new Set(blockers.map((item) => item.code));

  return (
    <div className="marketing-pack-tab">
      <h3>Preflight</h3>
      <p className="muted">Проверки перед согласованием pack.</p>

      <dl className="detail-list marketing-status-block">
        <dt>Статус preflight</dt>
        <dd>{marketingPreflightStatusLabel(pack.preflight_status)}</dd>
        <dt>Статус pack</dt>
        <dd>{pack.status}</dd>
        <dt>Согласование</dt>
        <dd>{pack.approval_status}</dd>
        {pack.preflight_at && (
          <>
            <dt>Последний запуск</dt>
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

      <div className={`marketing-preflight-banner marketing-preflight-banner--${tone}`}>
        <Alert variant={alertVariantForTone(tone)}>
          <strong>{preflightSummaryTitle(tone)}</strong>
          <span className="marketing-preflight-banner-sub">{preflightSummarySubtitle(tone)}</span>
        </Alert>
      </div>

      {report && (
        <div className="marketing-preflight-report panel">
          {report.checked_at && (
            <p className="muted marketing-preflight-meta">
              Отчёт
              {report.version ? ` · ${report.version}` : ""} · {formatDate(report.checked_at)}
            </p>
          )}

          {blockers.length > 0 && (
            <div className="marketing-issue-list marketing-issue-list--blockers">
              <h4>Что нужно исправить</h4>
              <ul>
                {blockers.map((issue, index) => (
                  <li key={`blocker-${issue.code}-${index}`}>
                    <span className="marketing-issue-label">{formatPreflightIssueLine(issue)}</span>
                    <span className="muted marketing-issue-code">{issue.code}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {warnings.length > 0 && (
            <div className="marketing-issue-list marketing-issue-list--warnings">
              <h4>На что обратить внимание</h4>
              <p className="muted marketing-issue-note">Не блокируют утверждение.</p>
              <ul>
                {warnings.map((issue, index) => (
                  <li key={`warn-${issue.code}-${index}`}>
                    <span className="marketing-issue-label">{formatPreflightIssueLine(issue)}</span>
                    <span className="muted marketing-issue-code">{issue.code}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {checklist.length > 0 && (
            <div className="marketing-check-list">
              <h4>Чеклист качества</h4>
              <ul>
                {checklist.map((check, index) => (
                  <li key={`check-${check.code}-${index}`}>
                    <ChecklistMark
                      passed={check.passed}
                      isBlockerRelated={!check.passed && blockerCodes.has(check.code)}
                    />{" "}
                    {preflightCheckLabel(check.code)}
                    {check.channel ? ` (${marketingChannelLabel(check.channel)})` : ""}
                    {check.message ? (
                      <span className="muted"> — {check.message}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(report.topic_context_summary || report.version === "m7-c1") && (
            <div className="marketing-preflight-topic">
              <h4>Контекст темы</h4>
              {!topicContextHasAnyFilled(report.topic_context_summary) ? (
                <p className="muted">Контекст темы пока не заполнен</p>
              ) : (
                <dl className="detail-list marketing-preflight-topic-grid">
                  {topicContextDisplayRows(report.topic_context_summary!).map((row) => (
                    <div key={row.key} className="marketing-preflight-topic-row">
                      <dt>{row.label}</dt>
                      <dd className={row.filled ? undefined : "muted"}>
                        {row.filled ? row.value : "Не заполнено"}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          )}

          {report.channel_checks.length > 0 && (
            <div className="marketing-preflight-channels">
              <h4>Каналы</h4>
              <ul className="marketing-preflight-channel-list">
                {report.channel_checks.map((check) => (
                  <li key={check.channel}>
                    <strong>{marketingChannelLabel(check.channel)}</strong>
                    <span>
                      {check.present ? `${check.length} симв.` : "нет текста"} ·{" "}
                      {channelCheckStatusLabel(check)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report.media_checks && (
            <div className="marketing-preflight-media">
              <h4>Медиа</h4>
              <p>
                Файлов в метаданных: <strong>{report.media_checks.count}</strong>
                {" · "}
                {report.media_checks.missing ? (
                  <span className="marketing-preflight-media-warn">нет медиа (предупреждение)</span>
                ) : (
                  <span>есть медиа</span>
                )}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
