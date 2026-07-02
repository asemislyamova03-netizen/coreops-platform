import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { listParties } from "../../api/parties";
import { createWorkItem, listPipelines } from "../../api/workflows";
import { ApiError } from "../../api/client";
import { Alert } from "../ui/Alert";
import { Loading } from "../ui/Loading";
import type { Pipeline } from "../../types/workflows";
import { getPartyRole } from "../../types/party";
import { pickDefaultPipeline } from "../../workspace/formatters";
import {
  isPartyVisibleInClientsList,
  pickWorkItemParticipantRole,
} from "../../workspace/labelHelpers";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";
import { WorkspaceModal } from "./WorkspaceModal";

interface CreateWorkItemModalProps {
  onClose: () => void;
  defaultPipeline?: Pipeline | null;
}

function firstStageId(pipeline: Pipeline): string | null {
  if (pipeline.stages.length === 0) return null;
  return [...pipeline.stages].sort((a, b) => a.sort_order - b.sort_order)[0]?.id ?? null;
}

export function CreateWorkItemModal({ onClose, defaultPipeline }: CreateWorkItemModalProps) {
  const queryClient = useQueryClient();
  const { defaultPartyRole, entityLabel, labels } = useWorkspaceLabels();
  const workItemLabel = entityLabel("work_item", "Заявка");
  const partyLabel = entityLabel("party", "Контрагент");
  const partyLabelLower = partyLabel.toLowerCase();
  const workItemLabelLower = workItemLabel.toLowerCase();
  const participantRole = pickWorkItemParticipantRole(defaultPartyRole);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [source, setSource] = useState("");
  const [partyId, setPartyId] = useState("");
  const [pipelineId, setPipelineId] = useState(defaultPipeline?.id ?? "");
  const [formError, setFormError] = useState<string | null>(null);

  const pipelinesQuery = useQuery({
    queryKey: ["workspace-pipelines"],
    queryFn: listPipelines,
  });

  const partiesQuery = useQuery({
    queryKey: ["workspace-parties", "for-work-item"],
    queryFn: () => listParties({ limit: 200 }),
  });

  const pipelines = pipelinesQuery.data ?? [];
  const selectedPipeline =
    pipelines.find((pipeline) => pipeline.id === pipelineId) ??
    defaultPipeline ??
    pickDefaultPipeline(pipelines);

  const partyOptions = useMemo(
    () =>
      (partiesQuery.data ?? []).filter((party) =>
        isPartyVisibleInClientsList(getPartyRole(party), labels),
      ),
    [labels, partiesQuery.data],
  );

  const createTitle = `Создать ${workItemLabelLower}`;

  const mutation = useMutation({
    mutationFn: () => {
      const trimmedTitle = title.trim();
      if (!trimmedTitle) {
        throw new Error(`Укажите название ${workItemLabelLower}.`);
      }
      if (!selectedPipeline) {
        throw new Error("Воронка не выбрана.");
      }
      const stageId = firstStageId(selectedPipeline);
      if (!stageId) {
        throw new Error("У воронки нет стадий.");
      }
      if (!partyId) {
        throw new Error(`Выберите ${partyLabelLower}.`);
      }

      return createWorkItem({
        pipeline_id: selectedPipeline.id,
        stage_id: stageId,
        work_item_type: "inquiry",
        title: trimmedTitle,
        description: description.trim() || null,
        source: source.trim() || null,
        primary_party_id: partyId,
        participants: [{ party_id: partyId, role: participantRole }],
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workspace-work-items"] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-party-work-items"] });
      onClose();
    },
    onError: (error) => {
      setFormError(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : `Не удалось создать ${workItemLabelLower}.`,
      );
    },
  });

  if (pipelinesQuery.isLoading || partiesQuery.isLoading) {
    return (
      <WorkspaceModal title={createTitle} onClose={onClose}>
        <Loading text="Загрузка формы..." />
      </WorkspaceModal>
    );
  }

  if (pipelinesQuery.error || partiesQuery.error) {
    const message =
      (pipelinesQuery.error instanceof ApiError && pipelinesQuery.error.message) ||
      (partiesQuery.error instanceof ApiError && partiesQuery.error.message) ||
      "Не удалось загрузить данные для формы.";
    return (
      <WorkspaceModal title={createTitle} onClose={onClose}>
        <Alert variant="error">{message}</Alert>
      </WorkspaceModal>
    );
  }

  return (
    <WorkspaceModal title={createTitle} onClose={onClose}>
      <form
        className="workspace-form"
        onSubmit={(event) => {
          event.preventDefault();
          setFormError(null);
          mutation.mutate();
        }}
      >
        {formError && <Alert variant="error">{formError}</Alert>}

        <label className="form-field">
          <span className="form-label">Название</span>
          <input
            className="form-input"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            required
            maxLength={255}
            autoFocus
          />
        </label>

        <label className="form-field">
          <span className="form-label">Воронка</span>
          <select
            className="form-select"
            value={selectedPipeline?.id ?? ""}
            onChange={(event) => setPipelineId(event.target.value)}
            required
          >
            {pipelines.map((pipeline) => (
              <option key={pipeline.id} value={pipeline.id}>
                {pipeline.name}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span className="form-label">{partyLabel}</span>
          <select
            className="form-select"
            value={partyId}
            onChange={(event) => setPartyId(event.target.value)}
            required
          >
            <option value="">Выберите {partyLabelLower}</option>
            {partyOptions.map((party) => (
              <option key={party.id} value={party.id}>
                {party.display_name}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span className="form-label">Описание</span>
          <textarea
            className="form-input workspace-textarea"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
          />
        </label>

        <label className="form-field">
          <span className="form-label">Источник</span>
          <input
            className="form-input"
            value={source}
            onChange={(event) => setSource(event.target.value)}
            placeholder="Необязательно"
          />
        </label>

        <div className="actions-row workspace-form-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Отмена
          </button>
          <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Сохранение..." : "Создать"}
          </button>
        </div>
      </form>
    </WorkspaceModal>
  );
}
