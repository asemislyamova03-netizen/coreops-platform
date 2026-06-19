import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createWorkItemActivity, getWorkItem } from "../../api/workflows";
import { ApiError } from "../../api/client";
import { Alert } from "../ui/Alert";
import { Loading } from "../ui/Loading";
import { formatActivityType } from "../../i18n/ruUi";
import { formatDate } from "../../workspace/formatters";

interface WorkItemActivityComposerProps {
  workItemId: string;
}

export function WorkItemActivityComposer({ workItemId }: WorkItemActivityComposerProps) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ["workspace-work-item", workItemId],
    queryFn: () => getWorkItem(workItemId),
  });

  const mutation = useMutation({
    mutationFn: (text: string) =>
      createWorkItemActivity(workItemId, {
        activity_type: "note",
        title: text,
      }),
    onSuccess: () => {
      setComment("");
      setFormError(null);
      void queryClient.invalidateQueries({ queryKey: ["workspace-work-item", workItemId] });
    },
    onError: (error) => {
      setFormError(
        error instanceof ApiError ? error.message : "Не удалось добавить комментарий.",
      );
    },
  });

  const activities = detailQuery.data?.activities ?? [];

  return (
    <div className="workspace-activity-block">
      <form
        className="workspace-activity-form"
        onSubmit={(event) => {
          event.preventDefault();
          const text = comment.trim();
          if (!text) {
            setFormError("Введите текст комментария.");
            return;
          }
          setFormError(null);
          mutation.mutate(text);
        }}
      >
        <label className="form-field">
          <span className="form-label">Комментарий</span>
          <textarea
            className="form-input workspace-textarea"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            rows={2}
            placeholder="Добавить заметку по заявке"
          />
        </label>
        {formError && <Alert variant="error">{formError}</Alert>}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "Сохранение..." : "Добавить комментарий"}
        </button>
      </form>

      {detailQuery.isLoading && <Loading text="Загрузка комментариев..." />}

      {detailQuery.error && (
        <Alert variant="error">
          {detailQuery.error instanceof ApiError
            ? detailQuery.error.message
            : "Не удалось загрузить комментарии."}
        </Alert>
      )}

      {activities.length > 0 && (
        <ul className="workspace-activity-list">
          {activities.map((activity) => (
            <li key={activity.id} className="workspace-activity-item">
              <div className="workspace-activity-title">{activity.title}</div>
              <div className="muted workspace-activity-meta">
                {formatActivityType(activity.activity_type)} · {formatDate(activity.occurred_at)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
