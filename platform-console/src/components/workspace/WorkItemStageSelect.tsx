import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { moveWorkItemStage } from "../../api/workflows";
import { ApiError } from "../../api/client";
import { Alert } from "../ui/Alert";
import type { PipelineStage, WorkItem } from "../../types/workflows";

interface WorkItemStageSelectProps {
  workItem: WorkItem;
  stages: PipelineStage[];
  onMoved?: () => void;
  compact?: boolean;
}

export function WorkItemStageSelect({
  workItem,
  stages,
  onMoved,
  compact = false,
}: WorkItemStageSelectProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const sortedStages = [...stages].sort((a, b) => a.sort_order - b.sort_order);
  const otherStages = sortedStages.filter((stage) => stage.id !== workItem.stage_id);

  const mutation = useMutation({
    mutationFn: (stageId: string) =>
      moveWorkItemStage(workItem.id, { stage_id: stageId }),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["workspace-work-items"] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-party-work-items"] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-work-item", workItem.id] });
      onMoved?.();
    },
    onError: (err) => {
      setError(
        err instanceof ApiError ? err.message : "Не удалось сменить стадию.",
      );
    },
  });

  if (otherStages.length === 0) {
    return compact ? null : <p className="muted">Нет других стадий.</p>;
  }

  return (
    <div className={compact ? "workspace-stage-select compact" : "workspace-stage-select"}>
      <label className="form-field">
        {!compact && <span className="form-label">Переместить на стадию</span>}
        <select
          className="form-select"
          value=""
          disabled={mutation.isPending}
          onChange={(event) => {
            const stageId = event.target.value;
            if (!stageId) return;
            setError(null);
            mutation.mutate(stageId);
            event.target.value = "";
          }}
        >
          <option value="">{mutation.isPending ? "Перемещение..." : "Сменить стадию"}</option>
          {otherStages.map((stage) => (
            <option key={stage.id} value={stage.id}>
              {stage.name}
            </option>
          ))}
        </select>
      </label>
      {error && <Alert variant="error">{error}</Alert>}
    </div>
  );
}
