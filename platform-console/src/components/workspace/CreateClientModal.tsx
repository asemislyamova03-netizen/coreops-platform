import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { createParty } from "../../api/parties";
import { ApiError } from "../../api/client";
import { Alert } from "../ui/Alert";
import type { ContactMethodType } from "../../types/party";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";
import { WorkspaceModal } from "./WorkspaceModal";

interface CreateClientModalProps {
  onClose: () => void;
  onCreated?: (partyId: string) => void;
}

function detectContactType(value: string): ContactMethodType {
  return value.includes("@") ? "email" : "phone";
}

export function CreateClientModal({ onClose, onCreated }: CreateClientModalProps) {
  const queryClient = useQueryClient();
  const { defaultPartyRole, entityLabel, partyRoleLabel } = useWorkspaceLabels();
  const partyLabel = entityLabel("party", "Контрагент");
  const partyLabelLower = partyLabel.toLowerCase();
  const roleLabel = partyRoleLabel(defaultPartyRole, defaultPartyRole);

  const [displayName, setDisplayName] = useState("");
  const [contact, setContact] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const createTitle = useMemo(() => `Создать ${partyLabelLower}`, [partyLabelLower]);

  const mutation = useMutation({
    mutationFn: () => {
      const trimmedName = displayName.trim();
      if (!trimmedName) {
        throw new Error(`Укажите имя ${partyLabelLower}.`);
      }
      const trimmedContact = contact.trim();
      return createParty({
        party_type: "person",
        display_name: trimmedName,
        party_role: defaultPartyRole,
        contact_methods: trimmedContact
          ? [
              {
                method_type: detectContactType(trimmedContact),
                value: trimmedContact,
                is_primary: true,
              },
            ]
          : [],
      });
    },
    onSuccess: (party) => {
      void queryClient.invalidateQueries({ queryKey: ["workspace-parties"] });
      onCreated?.(party.id);
      onClose();
    },
    onError: (error) => {
      setFormError(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : `Не удалось создать ${partyLabelLower}.`,
      );
    },
  });

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
          <span className="form-label">Имя {partyLabelLower}</span>
          <input
            className="form-input"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            required
            maxLength={255}
            autoFocus
          />
        </label>

        <label className="form-field">
          <span className="form-label">Телефон или email</span>
          <input
            className="form-input"
            value={contact}
            onChange={(event) => setContact(event.target.value)}
            placeholder="Необязательно"
          />
        </label>

        <p className="muted workspace-form-hint">
          {partyLabel} · роль: <code>{roleLabel}</code> ({defaultPartyRole})
        </p>

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
