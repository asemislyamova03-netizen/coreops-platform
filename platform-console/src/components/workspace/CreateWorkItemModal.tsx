import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { createParty, listParties, matchParties } from "../../api/parties";
import { createWorkItem, listPipelines } from "../../api/workflows";
import { ApiError } from "../../api/client";
import { Alert } from "../ui/Alert";
import { Loading } from "../ui/Loading";
import type { ContactMethodCreate, PartyMatchHit } from "../../types/party";
import type { Pipeline } from "../../types/workflows";
import { getPartyRole } from "../../types/party";
import { useTenantWorkspace } from "../../auth/TenantWorkspaceContext";
import { pickDefaultPipeline } from "../../workspace/formatters";
import {
  isPartyVisibleInClientsList,
  pickWorkItemParticipantRole,
} from "../../workspace/labelHelpers";
import {
  PARTY_MATCH_DEBOUNCE_MS,
  buildPartyMatchPayload,
  formatMatchedOn,
  hasExactMatch,
  matchTypeLabel,
  partyMatchFingerprint,
  pickVisibleMatches,
} from "../../workspace/partyMatchUiHelpers";
import { useLeadSources } from "../../workspace/useLeadSources";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";
import { WorkspaceModal } from "./WorkspaceModal";

interface CreateWorkItemModalProps {
  onClose: () => void;
  defaultPipeline?: Pipeline | null;
}

type PartyLinkMode = "new" | "existing";

function firstStageId(pipeline: Pipeline): string | null {
  if (pipeline.stages.length === 0) return null;
  return [...pipeline.stages].sort((a, b) => a.sort_order - b.sort_order)[0]?.id ?? null;
}

function buildContactMethods(phone: string, email: string): ContactMethodCreate[] {
  const methods: ContactMethodCreate[] = [];
  const trimmedPhone = phone.trim();
  const trimmedEmail = email.trim();

  if (trimmedPhone) {
    methods.push({
      method_type: "phone",
      value: trimmedPhone,
      is_primary: methods.length === 0,
    });
  }
  if (trimmedEmail) {
    methods.push({
      method_type: "email",
      value: trimmedEmail,
      is_primary: methods.length === 0,
    });
  }

  return methods;
}

export function CreateWorkItemModal({ onClose, defaultPipeline }: CreateWorkItemModalProps) {
  const queryClient = useQueryClient();
  const { tenant } = useTenantWorkspace();
  const { sources: leadSources } = useLeadSources(tenant?.tenantId ?? null);
  const { defaultPartyRole, entityLabel, labels, partyRoleLabel } = useWorkspaceLabels();
  const workItemLabel = entityLabel("work_item", "Заявка");
  const partyLabel = entityLabel("party", "Контрагент");
  const partyLabelLower = partyLabel.toLowerCase();
  const workItemLabelLower = workItemLabel.toLowerCase();
  const participantRole = pickWorkItemParticipantRole(defaultPartyRole);
  const roleLabel = partyRoleLabel(defaultPartyRole, defaultPartyRole);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sourceCode, setSourceCode] = useState("manual");
  const [sourceNote, setSourceNote] = useState("");
  const [partyLinkMode, setPartyLinkMode] = useState<PartyLinkMode>("new");
  const [partyId, setPartyId] = useState("");
  const [newContactName, setNewContactName] = useState("");
  const [newContactPhone, setNewContactPhone] = useState("");
  const [newContactEmail, setNewContactEmail] = useState("");
  const [pipelineId, setPipelineId] = useState(defaultPipeline?.id ?? "");
  const [formError, setFormError] = useState<string | null>(null);

  const [matchHits, setMatchHits] = useState<PartyMatchHit[]>([]);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [dismissedMatchKey, setDismissedMatchKey] = useState<string | null>(null);
  const [dismissedHadExact, setDismissedHadExact] = useState(false);
  const [selectedMatchName, setSelectedMatchName] = useState<string | null>(null);
  const matchRequestId = useRef(0);

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
  const hasLeadSources = leadSources.length > 0;
  const showSourceNote = hasLeadSources && sourceCode === "other";

  const matchPayload = useMemo(
    () =>
      buildPartyMatchPayload({
        name: newContactName,
        phone: newContactPhone,
        email: newContactEmail,
      }),
    [newContactEmail, newContactName, newContactPhone],
  );
  const currentMatchKey = matchPayload ? partyMatchFingerprint(matchPayload) : null;
  const visibleMatches = pickVisibleMatches(matchHits);
  const showMatchPanel =
    partyLinkMode === "new" &&
    visibleMatches.length > 0 &&
    currentMatchKey !== null &&
    dismissedMatchKey !== currentMatchKey;
  const exactPresent = hasExactMatch(visibleMatches);

  useEffect(() => {
    if (!hasLeadSources) {
      return;
    }
    if (!leadSources.some((item) => item.code === sourceCode)) {
      const manual = leadSources.find((item) => item.code === "manual");
      setSourceCode(manual?.code ?? leadSources[0]?.code ?? "manual");
    }
  }, [hasLeadSources, leadSources, sourceCode]);

  useEffect(() => {
    if (partyLinkMode !== "new") {
      setMatchHits([]);
      setMatchError(null);
      setMatchLoading(false);
      return;
    }

    if (!matchPayload || !currentMatchKey) {
      setMatchHits([]);
      setMatchError(null);
      setMatchLoading(false);
      return;
    }

    if (dismissedMatchKey === currentMatchKey) {
      return;
    }

    const requestId = ++matchRequestId.current;
    setMatchLoading(true);
    setMatchError(null);

    const timer = window.setTimeout(() => {
      void matchParties(matchPayload)
        .then((response) => {
          if (matchRequestId.current !== requestId) {
            return;
          }
          setMatchHits(response.matches);
          setMatchLoading(false);
        })
        .catch((error) => {
          if (matchRequestId.current !== requestId) {
            return;
          }
          setMatchHits([]);
          setMatchLoading(false);
          setMatchError(
            error instanceof ApiError
              ? error.message
              : "Не удалось проверить совпадения контактов.",
          );
        });
    }, PARTY_MATCH_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timer);
    };
  }, [currentMatchKey, dismissedMatchKey, matchPayload, partyLinkMode]);

  const useExistingMatch = (hit: PartyMatchHit) => {
    setPartyLinkMode("existing");
    setPartyId(hit.party_id);
    setSelectedMatchName(hit.display_name);
    setMatchHits([]);
    setMatchError(null);
    setDismissedMatchKey(null);
    setFormError(null);
  };

  const continueAsNew = () => {
    if (currentMatchKey) {
      setDismissedMatchKey(currentMatchKey);
      setDismissedHadExact(hasExactMatch(visibleMatches));
    }
    setMatchHits([]);
  };

  const mutation = useMutation({
    mutationFn: async () => {
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
      if (hasLeadSources && !sourceCode) {
        throw new Error("Выберите источник лида.");
      }

      const resolvedSource = hasLeadSources ? sourceCode : null;
      const trimmedSourceNote = sourceNote.trim();
      const customFields =
        showSourceNote && trimmedSourceNote ? { source_note: trimmedSourceNote } : undefined;

      let resolvedPartyId: string;
      if (partyLinkMode === "new") {
        const trimmedName = newContactName.trim();
        if (!trimmedName) {
          throw new Error(`Укажите имя ${partyLabelLower}.`);
        }
        const party = await createParty({
          party_type: "person",
          display_name: trimmedName,
          party_role: defaultPartyRole,
          metadata_json: resolvedSource ? { source: resolvedSource } : {},
          contact_methods: buildContactMethods(newContactPhone, newContactEmail),
        });
        resolvedPartyId = party.id;
      } else {
        if (!partyId) {
          throw new Error(
            `Выберите ${partyLabelLower} из списка или переключитесь на «Новый ${partyLabelLower}».`,
          );
        }
        resolvedPartyId = partyId;
      }

      return createWorkItem({
        pipeline_id: selectedPipeline.id,
        stage_id: stageId,
        work_item_type: "inquiry",
        title: trimmedTitle,
        description: description.trim() || null,
        source: resolvedSource,
        primary_party_id: resolvedPartyId,
        participants: [{ party_id: resolvedPartyId, role: participantRole }],
        custom_fields: customFields,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workspace-work-items"] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-party-work-items"] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-parties"] });
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

  if (pipelinesQuery.isLoading) {
    return (
      <WorkspaceModal title={createTitle} onClose={onClose}>
        <Loading text="Загрузка формы..." />
      </WorkspaceModal>
    );
  }

  if (pipelinesQuery.error) {
    const message =
      pipelinesQuery.error instanceof ApiError
        ? pipelinesQuery.error.message
        : "Не удалось загрузить данные для формы.";
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

        <fieldset className="form-field">
          <span className="form-label">{partyLabel}</span>
          <div className="actions-row" style={{ gap: "1rem", marginBottom: "0.75rem" }}>
            <label className="muted" style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <input
                type="radio"
                name="party-link-mode"
                checked={partyLinkMode === "new"}
                onChange={() => {
                  setPartyLinkMode("new");
                  setSelectedMatchName(null);
                }}
              />
              Новый {partyLabelLower}
            </label>
            <label className="muted" style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <input
                type="radio"
                name="party-link-mode"
                checked={partyLinkMode === "existing"}
                onChange={() => {
                  setPartyLinkMode("existing");
                  setMatchHits([]);
                  setMatchError(null);
                  setDismissedMatchKey(null);
                }}
              />
              Существующий
            </label>
          </div>

          {partyLinkMode === "new" ? (
            <>
              <label className="form-field">
                <span className="form-label">Имя {partyLabelLower}</span>
                <input
                  className="form-input"
                  value={newContactName}
                  onChange={(event) => {
                    setNewContactName(event.target.value);
                    setDismissedMatchKey(null);
                    setDismissedHadExact(false);
                  }}
                  required
                  maxLength={255}
                />
              </label>

              <label className="form-field">
                <span className="form-label">Телефон</span>
                <input
                  className="form-input"
                  value={newContactPhone}
                  onChange={(event) => {
                    setNewContactPhone(event.target.value);
                    setDismissedMatchKey(null);
                    setDismissedHadExact(false);
                  }}
                  placeholder="Необязательно"
                />
              </label>

              <label className="form-field">
                <span className="form-label">Email</span>
                <input
                  className="form-input"
                  type="email"
                  value={newContactEmail}
                  onChange={(event) => {
                    setNewContactEmail(event.target.value);
                    setDismissedMatchKey(null);
                    setDismissedHadExact(false);
                  }}
                  placeholder="Необязательно"
                />
              </label>

              {matchLoading && (
                <p className="muted workspace-form-hint">Проверяем совпадения контактов…</p>
              )}

              {matchError && (
                <Alert variant="info">
                  Не удалось проверить совпадения: {matchError}. Можно продолжить создание лида.
                </Alert>
              )}

              {showMatchPanel && (
                <div
                  className={`crm-party-match-panel${
                    exactPresent ? " crm-party-match-panel--exact" : " crm-party-match-panel--weak"
                  }`}
                >
                  <div className="crm-party-match-title">
                    {exactPresent ? "Похожий контакт найден" : "Возможно, это тот же человек"}
                  </div>
                  {exactPresent && (
                    <p className="muted crm-party-match-hint">
                      Контакт с такими данными уже есть. Рекомендуем использовать существующий.
                    </p>
                  )}
                  <ul className="crm-party-match-list">
                    {visibleMatches.map((hit) => {
                      const recent = hit.recent_work_items[0];
                      return (
                        <li key={hit.party_id} className="crm-party-match-item">
                          <div className="crm-party-match-item-main">
                            <strong>{hit.display_name}</strong>
                            <span className="muted">
                              {matchTypeLabel(hit.match_type)}
                              {hit.matched_on.length > 0
                                ? ` · ${formatMatchedOn(hit.matched_on)}`
                                : ""}
                            </span>
                            {recent && (
                              <span className="muted">
                                Недавнее обращение: {recent.title}
                              </span>
                            )}
                          </div>
                          <button
                            type="button"
                            className="btn btn-primary crm-party-match-use-btn"
                            onClick={() => useExistingMatch(hit)}
                          >
                            Использовать этот контакт
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={continueAsNew}
                  >
                    Создать нового
                  </button>
                </div>
              )}

              {!showMatchPanel &&
                dismissedHadExact &&
                dismissedMatchKey === currentMatchKey &&
                currentMatchKey && (
                  <p className="muted workspace-form-hint">
                    Контакт с такими данными уже есть, но вы можете создать нового.
                  </p>
                )}

              <p className="muted workspace-form-hint">
                {partyLabel} · роль: <code>{roleLabel}</code> ({defaultPartyRole})
              </p>
              <p className="muted workspace-form-hint">
                Telegram / WhatsApp в форме пока не вводятся — match по ним будет после появления
                полей (сейчас: имя, телефон, email).
              </p>
            </>
          ) : partiesQuery.isLoading ? (
            <Loading text={`Загрузка списка ${partyLabelLower}...`} />
          ) : partiesQuery.error ? (
            <Alert variant="error">
              {partiesQuery.error instanceof ApiError
                ? partiesQuery.error.message
                : `Не удалось загрузить список ${partyLabelLower}.`}
            </Alert>
          ) : (
            <>
              {selectedMatchName && (
                <Alert variant="info">
                  Выбран контакт из совпадений: <strong>{selectedMatchName}</strong>. Новый{" "}
                  {partyLabelLower} создаваться не будет.
                </Alert>
              )}
              <label className="form-field">
                <span className="form-label">Выберите {partyLabelLower}</span>
                <select
                  className="form-select"
                  value={partyId}
                  onChange={(event) => {
                    setPartyId(event.target.value);
                    setSelectedMatchName(null);
                  }}
                >
                  <option value="">— выберите из списка —</option>
                  {partyId &&
                    !partyOptions.some((party) => party.id === partyId) && (
                      <option value={partyId}>
                        {selectedMatchName ?? `Контакт ${partyId.slice(0, 8)}…`}
                      </option>
                    )}
                  {partyOptions.map((party) => (
                    <option key={party.id} value={party.id}>
                      {party.display_name}
                    </option>
                  ))}
                </select>
                {partyOptions.length === 0 && !partyId && (
                  <p className="muted workspace-form-hint">
                    Список пуст. Переключитесь на «Новый {partyLabelLower}».
                  </p>
                )}
              </label>
            </>
          )}
        </fieldset>

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
          {hasLeadSources ? (
            <>
              <select
                className="form-select"
                value={sourceCode}
                onChange={(event) => setSourceCode(event.target.value)}
              >
                {leadSources.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label_ru}
                  </option>
                ))}
              </select>
              {showSourceNote && (
                <input
                  className="form-input"
                  value={sourceNote}
                  onChange={(event) => setSourceNote(event.target.value)}
                  placeholder="Уточните источник"
                  style={{ marginTop: "0.5rem" }}
                />
              )}
            </>
          ) : (
            <p className="muted workspace-form-hint">
              Справочник источников не настроен для этой организации.
            </p>
          )}
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
