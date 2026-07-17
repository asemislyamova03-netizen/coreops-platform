import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getParty, updateParty } from "../../api/parties";
import {
  closeWorkItem,
  getWorkItem,
  listWorkItems,
  reopenWorkItem,
  updateWorkItem,
} from "../../api/workflows";
import { ApiError } from "../../api/client";
import { useTenantWorkspace } from "../../auth/TenantWorkspaceContext";
import { Alert } from "../ui/Alert";
import { Loading } from "../ui/Loading";
import { formatCommonStatus } from "../../i18n/ruUi";
import type { LeadSource } from "../../types/leadSources";
import type { DispositionCode, Pipeline, PipelineStage } from "../../types/workflows";
import {
  contactMethodsChanged,
  getEmailFromContactMethods,
  getPhoneFromContactMethods,
  mergePhoneEmailContactMethods,
} from "../../workspace/contactMethodHelpers";
import { formatDate } from "../../workspace/formatters";
import {
  DISPOSITION_CODES,
  getDispositionLabel,
  isRejectedWithMissingDisposition,
  readDisposition,
  readDispositionNote,
} from "../../workspace/leadDispositionHelpers";
import { getPartyRole } from "../../types/party";
import {
  buildMarkAsClientPayload,
  getLeadClientStatusView,
} from "../../workspace/leadClientStatusHelpers";
import { buildLeadApplicationDataView } from "../../workspace/leadApplicationDataHelpers";
import { resolveLeadSourceLabel } from "../../workspace/leadSourceHelpers";
import { getLeadStageHelp } from "../../workspace/leadStageHelpHelpers";
import { scrollToPipelineStage } from "../../workspace/crmPipelineBoardHelpers";
import {
  PARTY_HISTORY_FETCH_LIMIT,
  selectPartyHistoryItems,
} from "../../workspace/partyWorkItemHistoryHelpers";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";
import { WorkspaceModal } from "./WorkspaceModal";

interface LeadDetailModalProps {
  workItemId: string;
  pipeline: Pipeline;
  leadSources: LeadSource[];
  onClose: () => void;
  onWorkItemClosed?: () => void;
  onWorkItemReopened?: () => void;
  onOpenWorkItem?: (workItemId: string) => void;
}

function stageName(stages: PipelineStage[], stageId: string): string {
  return stages.find((stage) => stage.id === stageId)?.name ?? "—";
}

function stageCode(stages: PipelineStage[], stageId: string): string | null {
  return stages.find((stage) => stage.id === stageId)?.code ?? null;
}

function readSourceNote(customFields: Record<string, unknown>): string {
  const value = customFields.source_note;
  return typeof value === "string" ? value : "";
}

export function LeadDetailModal({
  workItemId,
  pipeline,
  leadSources,
  onClose,
  onWorkItemClosed,
  onWorkItemReopened,
  onOpenWorkItem,
}: LeadDetailModalProps) {
  const queryClient = useQueryClient();
  const { tenant } = useTenantWorkspace();
  const { entityLabel } = useWorkspaceLabels();
  const workItemLabel = entityLabel("work_item", "Заявка");
  const partyLabel = entityLabel("party", "Контрагент");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sourceCode, setSourceCode] = useState("");
  const [sourceNote, setSourceNote] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [originalContactName, setOriginalContactName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [dispositionError, setDispositionError] = useState<string | null>(null);
  const [closeDisposition, setCloseDisposition] = useState<DispositionCode | "">("");
  const [closeNote, setCloseNote] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [markClientMessage, setMarkClientMessage] = useState<string | null>(null);
  const [markClientError, setMarkClientError] = useState<string | null>(null);

  const workItemQuery = useQuery({
    queryKey: ["workspace-work-item", workItemId],
    queryFn: () => getWorkItem(workItemId),
  });

  const partyId = workItemQuery.data?.primary_party_id ?? null;

  const partyQuery = useQuery({
    queryKey: ["workspace-party", partyId],
    queryFn: () => getParty(partyId!),
    enabled: Boolean(partyId),
  });

  const partyHistoryQuery = useQuery({
    queryKey: ["workspace-party-work-items", partyId],
    queryFn: () =>
      listWorkItems({ primary_party_id: partyId!, limit: PARTY_HISTORY_FETCH_LIMIT }),
    enabled: Boolean(partyId),
  });

  const historyItems = useMemo(
    () => selectPartyHistoryItems(partyHistoryQuery.data ?? [], workItemId),
    [partyHistoryQuery.data, workItemId],
  );

  const sortedStages = useMemo(
    () => [...pipeline.stages].sort((a, b) => a.sort_order - b.sort_order),
    [pipeline.stages],
  );

  const hasLeadSources = leadSources.length > 0;
  const existingSourceNote = workItemQuery.data
    ? readSourceNote(workItemQuery.data.custom_fields)
    : "";
  const showSourceNote =
    hasLeadSources && (sourceCode === "other" || Boolean(existingSourceNote.trim()));

  useEffect(() => {
    if (!workItemQuery.data || hydrated) {
      return;
    }
    const item = workItemQuery.data;
    setTitle(item.title);
    setDescription(item.description ?? "");
    setSourceCode(item.source ?? (hasLeadSources ? "manual" : ""));
    setSourceNote(readSourceNote(item.custom_fields));
    setHydrated(true);
  }, [workItemQuery.data, hydrated, hasLeadSources]);

  useEffect(() => {
    if (!partyQuery.data || !hydrated) {
      return;
    }
    const party = partyQuery.data;
    setContactName(party.display_name);
    setOriginalContactName(party.display_name);
    setContactPhone(getPhoneFromContactMethods(party.contact_methods));
    setContactEmail(getEmailFromContactMethods(party.contact_methods));
  }, [partyQuery.data, hydrated]);

  const invalidateWorkItemCaches = () => {
    void queryClient.invalidateQueries({ queryKey: ["workspace-work-items"] });
    void queryClient.invalidateQueries({ queryKey: ["workspace-work-item", workItemId] });
    void queryClient.invalidateQueries({ queryKey: ["workspace-party-work-items"] });
  };

  const closeMutation = useMutation({
    mutationFn: async () => {
      if (!closeDisposition) {
        throw new Error("Выберите причину закрытия.");
      }
      const label = getDispositionLabel(closeDisposition);
      if (!window.confirm(`Закрыть обращение с причиной «${label}»?`)) {
        throw new Error("CLOSE_CANCELLED");
      }
      const trimmedNote = closeNote.trim();
      return closeWorkItem(workItemId, {
        disposition: closeDisposition,
        disposition_note: trimmedNote || null,
      });
    },
    onSuccess: () => {
      setDispositionError(null);
      setCloseNote("");
      invalidateWorkItemCaches();
      onWorkItemClosed?.();
    },
    onError: (error) => {
      if (error instanceof Error && error.message === "CLOSE_CANCELLED") {
        return;
      }
      setDispositionError(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Не удалось закрыть обращение.",
      );
    },
  });

  const reopenMutation = useMutation({
    mutationFn: async () => {
      if (!window.confirm("Вернуть обращение в работу?")) {
        throw new Error("REOPEN_CANCELLED");
      }
      return reopenWorkItem(workItemId);
    },
    onSuccess: () => {
      setDispositionError(null);
      setCloseDisposition("");
      setCloseNote("");
      invalidateWorkItemCaches();
      onWorkItemReopened?.();
      scrollToPipelineStage("new_lead");
    },
    onError: (error) => {
      if (error instanceof Error && error.message === "REOPEN_CANCELLED") {
        return;
      }
      setDispositionError(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Не удалось вернуть обращение в работу.",
      );
    },
  });

  const markAsClientMutation = useMutation({
    mutationFn: async () => {
      if (!partyId) {
        throw new Error("Контакт не привязан.");
      }
      return updateParty(partyId, buildMarkAsClientPayload());
    },
    onSuccess: () => {
      setMarkClientError(null);
      setMarkClientMessage("Контакт отмечен как клиент.");
      void queryClient.invalidateQueries({ queryKey: ["workspace-parties"] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-party", partyId] });
    },
    onError: (error) => {
      setMarkClientMessage(null);
      setMarkClientError(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Не удалось отметить контакт как клиента.",
      );
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const trimmedTitle = title.trim();
      if (!trimmedTitle) {
        throw new Error("Укажите название.");
      }
      if (hasLeadSources && !sourceCode) {
        throw new Error("Выберите источник.");
      }

      const item = workItemQuery.data;
      if (!item) {
        throw new Error("Заявка не загружена.");
      }

      const trimmedSourceNote = sourceNote.trim();
      const customFieldsPayload =
        showSourceNote || existingSourceNote
          ? { source_note: trimmedSourceNote || null }
          : undefined;

      const workItemPayload: Parameters<typeof updateWorkItem>[1] = {};
      if (trimmedTitle !== item.title) {
        workItemPayload.title = trimmedTitle;
      }
      const nextDescription = description.trim() || null;
      if (nextDescription !== item.description) {
        workItemPayload.description = nextDescription;
      }
      const nextSource = hasLeadSources ? sourceCode : item.source;
      if (nextSource !== item.source) {
        workItemPayload.source = nextSource;
      }
      if (customFieldsPayload) {
        const nextNote = customFieldsPayload.source_note;
        const prevNote = readSourceNote(item.custom_fields) || null;
        if (nextNote !== prevNote) {
          workItemPayload.custom_fields = customFieldsPayload;
        }
      }

      const tasks: Promise<unknown>[] = [];
      if (Object.keys(workItemPayload).length > 0) {
        tasks.push(updateWorkItem(workItemId, workItemPayload));
      }

      const party = partyQuery.data;
      if (party) {
        const trimmedName = contactName.trim();
        if (!trimmedName) {
          throw new Error(`Укажите имя ${partyLabel.toLowerCase()}.`);
        }
        if (
          contactMethodsChanged(
            party.contact_methods,
            trimmedName,
            originalContactName,
            contactPhone,
            contactEmail,
          )
        ) {
          tasks.push(
            updateParty(party.id, {
              display_name: trimmedName,
              contact_methods: mergePhoneEmailContactMethods(
                party.contact_methods,
                contactPhone,
                contactEmail,
              ),
            }),
          );
        } else if (trimmedName !== originalContactName.trim()) {
          tasks.push(updateParty(party.id, { display_name: trimmedName }));
        }
      }

      if (tasks.length === 0) {
        return;
      }
      await Promise.all(tasks);
    },
    onSuccess: () => {
      setFormError(null);
      void queryClient.invalidateQueries({ queryKey: ["workspace-work-items"] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-work-item", workItemId] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-party-work-items"] });
      void queryClient.invalidateQueries({ queryKey: ["workspace-parties"] });
      if (partyId) {
        void queryClient.invalidateQueries({ queryKey: ["workspace-party", partyId] });
      }
      onClose();
    },
    onError: (error) => {
      setFormError(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Не удалось сохранить изменения.",
      );
    },
  });

  const modalTitle = `${workItemLabel}: детали`;

  if (workItemQuery.isLoading) {
    return (
      <WorkspaceModal title={modalTitle} onClose={onClose}>
        <Loading text="Загрузка заявки..." />
      </WorkspaceModal>
    );
  }

  if (workItemQuery.error || !workItemQuery.data) {
    const message =
      workItemQuery.error instanceof ApiError
        ? workItemQuery.error.message
        : "Не удалось загрузить заявку.";
    return (
      <WorkspaceModal title={modalTitle} onClose={onClose}>
        <Alert variant="error">{message}</Alert>
      </WorkspaceModal>
    );
  }

  const item = workItemQuery.data;
  const tenantSlug = tenant?.tenantSlug ?? "";
  const currentStageCode = stageCode(sortedStages, item.stage_id);
  const isRejected = currentStageCode === "rejected";
  const storedDisposition = readDisposition(item.custom_fields);
  const storedDispositionNote = readDispositionNote(item.custom_fields);
  const missingDispositionWarning = isRejectedWithMissingDisposition(
    item.custom_fields,
    currentStageCode,
  );
  const showOtherNoteWarning =
    closeDisposition === "other" && !closeNote.trim() && !closeMutation.isPending;
  const dispositionBusy = closeMutation.isPending || reopenMutation.isPending;
  const applicationData = buildLeadApplicationDataView(item, {
    sourceLabel: resolveLeadSourceLabel(leadSources, item.source),
  });
  const stageHelp = getLeadStageHelp(currentStageCode);
  const clientStatus = getLeadClientStatusView({
    hasParty: Boolean(partyId && partyQuery.data),
    stageCode: currentStageCode,
    partyRole: partyQuery.data ? getPartyRole(partyQuery.data) : null,
  });

  return (
    <WorkspaceModal title={modalTitle} onClose={onClose}>
      <form
        className="workspace-form"
        onSubmit={(event) => {
          event.preventDefault();
          setFormError(null);
          saveMutation.mutate();
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
          />
        </label>

        <div className="form-field">
          <span className="form-label">Стадия</span>
          <p className="workspace-readonly-field">{stageName(sortedStages, item.stage_id)}</p>
          <p className="muted workspace-form-hint">
            Сменить стадию можно на карточке в kanban.
          </p>
          {stageHelp && (
            <div className="crm-stage-help" role="note">
              <p className="crm-stage-help-title">{stageHelp.title}</p>
              <p className="muted crm-stage-help-text">{stageHelp.help}</p>
            </div>
          )}
        </div>

        <label className="form-field">
          <span className="form-label">Источник</span>
          {hasLeadSources ? (
            <>
              <select
                className="form-select"
                value={sourceCode}
                onChange={(event) => setSourceCode(event.target.value)}
              >
                {leadSources.map((source) => (
                  <option key={source.code} value={source.code}>
                    {source.label_ru}
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
            <p className="workspace-readonly-field muted">{item.source ?? "—"}</p>
          )}
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

        {applicationData.shouldShow && (
          <div className="workspace-form-section crm-application-data">
            <h3 className="workspace-form-section-title">Данные заявки</h3>
            <dl className="crm-application-data-grid">
              {applicationData.rows.map((row) => (
                <div key={row.key} className="crm-application-data-row">
                  <dt className="crm-application-data-label">{row.label}</dt>
                  <dd className="crm-application-data-value">
                    {row.href ? (
                      <a
                        href={row.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="crm-application-data-link"
                        title={row.href}
                      >
                        {row.value}
                      </a>
                    ) : (
                      row.value
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        <div className="workspace-form-section">
          <h3 className="workspace-form-section-title">{partyLabel}</h3>
          {partyId && partyQuery.isLoading && <Loading text={`Загрузка ${partyLabel.toLowerCase()}...`} />}
          {partyId && partyQuery.error && (
            <Alert variant="error">
              {partyQuery.error instanceof ApiError
                ? partyQuery.error.message
                : `Не удалось загрузить ${partyLabel.toLowerCase()}.`}
            </Alert>
          )}
          {!partyId && <p className="muted">Контакт не привязан.</p>}
          {partyId && partyQuery.data && (
            <>
              {tenantSlug && (
                <p className="workspace-form-hint">
                  <Link to={`/workspace/${tenantSlug}/clients/${partyId}`}>
                    Открыть карточку {partyLabel.toLowerCase()}
                  </Link>
                </p>
              )}
              <label className="form-field">
                <span className="form-label">Имя</span>
                <input
                  className="form-input"
                  value={contactName}
                  onChange={(event) => setContactName(event.target.value)}
                  required
                  maxLength={255}
                />
              </label>
              <label className="form-field">
                <span className="form-label">Телефон</span>
                <input
                  className="form-input"
                  value={contactPhone}
                  onChange={(event) => setContactPhone(event.target.value)}
                />
              </label>
              <label className="form-field">
                <span className="form-label">Email</span>
                <input
                  className="form-input"
                  type="email"
                  value={contactEmail}
                  onChange={(event) => setContactEmail(event.target.value)}
                />
              </label>

              {clientStatus.shouldShowClientBlock && (
                <div className="crm-client-status" role="group" aria-label="Клиент">
                  <div className="crm-client-status-header">
                    <span className="crm-client-status-title">Клиент</span>
                    {clientStatus.showClientBadge && (
                      <span className="badge badge-active">{clientStatus.badgeLabel}</span>
                    )}
                  </div>
                  {clientStatus.helpText && (
                    <p className="muted crm-client-status-help">{clientStatus.helpText}</p>
                  )}
                  {markClientError && <Alert variant="error">{markClientError}</Alert>}
                  {markClientMessage && <Alert variant="success">{markClientMessage}</Alert>}
                  {clientStatus.canMarkAsClient && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={markAsClientMutation.isPending}
                      onClick={() => {
                        setMarkClientError(null);
                        setMarkClientMessage(null);
                        markAsClientMutation.mutate();
                      }}
                    >
                      {markAsClientMutation.isPending ? "Сохранение..." : "Сделать клиентом"}
                    </button>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {partyId && (
          <div className="workspace-form-section">
            <h3 className="workspace-form-section-title">История обращений контакта</h3>
            {partyHistoryQuery.isLoading && (
              <Loading text="Загрузка истории обращений..." />
            )}
            {partyHistoryQuery.isError && (
              <Alert variant="info">Не удалось загрузить историю обращений</Alert>
            )}
            {partyHistoryQuery.isSuccess && historyItems.length === 0 && (
              <p className="muted">Других обращений пока нет</p>
            )}
            {partyHistoryQuery.isSuccess && historyItems.length > 0 && (
              <ul className="crm-party-history-list">
                {historyItems.map((historyItem) => {
                  const sourceLabel = resolveLeadSourceLabel(leadSources, historyItem.source);
                  const disposition = readDisposition(historyItem.custom_fields);
                  const dispositionLabel = disposition
                    ? getDispositionLabel(disposition)
                    : null;
                  const stageLabel = stageName(sortedStages, historyItem.stage_id);
                  const otherPipeline =
                    historyItem.pipeline_id !== pipeline.id &&
                    !sortedStages.some((stage) => stage.id === historyItem.stage_id);

                  return (
                    <li key={historyItem.id} className="crm-party-history-item">
                      <div className="crm-party-history-item-main">
                        <div className="crm-party-history-title">{historyItem.title}</div>
                        <div className="crm-party-history-meta muted">
                          <span>{formatDate(historyItem.updated_at)}</span>
                          {sourceLabel && <span>· {sourceLabel}</span>}
                          <span>· {otherPipeline ? "другая воронка" : stageLabel}</span>
                          <span>· {formatCommonStatus(historyItem.status)}</span>
                          {dispositionLabel && <span>· {dispositionLabel}</span>}
                        </div>
                      </div>
                      {onOpenWorkItem && (
                        <button
                          type="button"
                          className="btn btn-secondary crm-party-history-open-btn"
                          onClick={() => onOpenWorkItem(historyItem.id)}
                        >
                          Открыть
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}

        <div className="workspace-form-section">
          <h3 className="workspace-form-section-title">Статус обращения</h3>
          {dispositionError && <Alert variant="error">{dispositionError}</Alert>}

          {!isRejected ? (
            <>
              <label className="form-field">
                <span className="form-label">Пометить как</span>
                <select
                  className="form-select"
                  value={closeDisposition}
                  disabled={dispositionBusy}
                  onChange={(event) =>
                    setCloseDisposition(event.target.value as DispositionCode | "")
                  }
                >
                  <option value="">Выберите причину</option>
                  {DISPOSITION_CODES.map((code) => (
                    <option key={code} value={code}>
                      {getDispositionLabel(code)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span className="form-label">Пояснение</span>
                <textarea
                  className="form-input workspace-textarea"
                  value={closeNote}
                  disabled={dispositionBusy}
                  onChange={(event) => setCloseNote(event.target.value)}
                  placeholder="Необязательно"
                  rows={2}
                />
              </label>

              {showOtherNoteWarning && (
                <Alert variant="info">
                  Лучше добавить пояснение, но можно сохранить без него.
                </Alert>
              )}

              <div className="actions-row">
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={!closeDisposition || dispositionBusy}
                  onClick={() => {
                    setDispositionError(null);
                    closeMutation.mutate();
                  }}
                >
                  {closeMutation.isPending ? "Закрытие..." : "Закрыть обращение"}
                </button>
              </div>
            </>
          ) : (
            <>
              {missingDispositionWarning ? (
                <Alert variant="info">Причина закрытия не указана</Alert>
              ) : (
                <p className="workspace-readonly-field">
                  Причина закрытия: {getDispositionLabel(storedDisposition)}
                </p>
              )}
              {storedDispositionNote.trim() && (
                <p className="workspace-readonly-field muted">
                  Пояснение: {storedDispositionNote}
                </p>
              )}
              <div className="actions-row">
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={dispositionBusy}
                  onClick={() => {
                    setDispositionError(null);
                    reopenMutation.mutate();
                  }}
                >
                  {reopenMutation.isPending ? "Возврат..." : "Вернуть в работу"}
                </button>
              </div>
            </>
          )}
        </div>

        <div className="workspace-form-meta muted">
          <div>Создано: {formatDate(item.created_at)}</div>
          <div>Обновлено: {formatDate(item.updated_at)}</div>
        </div>

        <div className="actions-row workspace-form-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Закрыть
          </button>
          <button type="submit" className="btn btn-primary" disabled={saveMutation.isPending || dispositionBusy}>
            {saveMutation.isPending ? "Сохранение..." : "Сохранить"}
          </button>
        </div>
      </form>
    </WorkspaceModal>
  );
}
