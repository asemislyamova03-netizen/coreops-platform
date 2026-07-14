import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { approveMarketingPack, rejectMarketingPack } from "../../../../api/marketing";
import { ApiError } from "../../../../api/client";
import { Alert } from "../../../../components/ui/Alert";
import type { MarketingPackDetail } from "../../../../types/marketing";
import { formatDate } from "../../../../workspace/formatters";
import { formatMarketingApiError } from "./marketingErrors";

interface PackDetailApprovalTabProps {
  packId: string;
  pack: MarketingPackDetail;
}

export function PackDetailApprovalTab({ packId, pack }: PackDetailApprovalTabProps) {
  const queryClient = useQueryClient();
  const [rejectReason, setRejectReason] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const canApprove = pack.preflight_status === "passed";

  const approveMutation = useMutation({
    mutationFn: () => approveMarketingPack(packId),
    onSuccess: async () => {
      setActionMessage("Pack согласован.");
      await queryClient.invalidateQueries({ queryKey: ["marketing-pack", packId] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectMarketingPack(packId, rejectReason.trim() || undefined),
    onSuccess: async () => {
      setRejectReason("");
      setActionMessage("Pack отклонён, статус сброшен в draft.");
      await queryClient.invalidateQueries({ queryKey: ["marketing-pack", packId] });
    },
  });

  const actionError = approveMutation.error ?? rejectMutation.error;
  const friendlyActionError =
    actionError instanceof ApiError && actionError.status === 409
      ? formatMarketingApiError(actionError, "Действие недоступно для текущего статуса pack.")
      : actionError
        ? formatMarketingApiError(actionError, "Не удалось выполнить действие.")
        : null;

  return (
    <div className="marketing-pack-tab">
      <h3>Approval</h3>
      <p className="muted">Согласование pack после успешного preflight.</p>

      <dl className="detail-list marketing-status-block">
        <dt>approval_status</dt>
        <dd>{pack.approval_status}</dd>
        <dt>preflight_status</dt>
        <dd>{pack.preflight_status}</dd>
        <dt>pack status</dt>
        <dd>{pack.status}</dd>
        {pack.approved_at && (
          <>
            <dt>approved_at</dt>
            <dd>{formatDate(pack.approved_at)}</dd>
          </>
        )}
      </dl>

      {!canApprove && (
        <Alert variant="info">
          Approve доступен только после успешного preflight (без блокирующих ошибок). Запустите
          проверку на вкладке Preflight. Предупреждения не блокируют согласование.
        </Alert>
      )}
      {canApprove && (
        <Alert variant="info">
          Preflight пройден. Предупреждения (если были) не мешают согласованию.
        </Alert>
      )}

      <div className="marketing-approval-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={!canApprove || approveMutation.isPending || rejectMutation.isPending}
          onClick={() => {
            setActionMessage(null);
            approveMutation.mutate();
          }}
        >
          {approveMutation.isPending ? "Согласование..." : "Approve"}
        </button>

        <div className="marketing-reject-block">
          <label className="form-field">
            <span className="form-label">Причина отклонения (optional)</span>
            <input
              className="form-input"
              value={rejectReason}
              onChange={(event) => setRejectReason(event.target.value)}
              placeholder="Необязательно"
            />
          </label>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={rejectMutation.isPending || approveMutation.isPending}
            onClick={() => {
              setActionMessage(null);
              rejectMutation.mutate();
            }}
          >
            {rejectMutation.isPending ? "Отклонение..." : "Reject"}
          </button>
        </div>
      </div>

      {actionMessage && <Alert variant="info">{actionMessage}</Alert>}
      {friendlyActionError && <Alert variant="error">{friendlyActionError}</Alert>}
    </div>
  );
}
