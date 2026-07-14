import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import {
  addMarketingPackMedia,
  deleteMarketingMedia,
  updateMarketingMedia,
} from "../../../../api/marketing";
import { Alert } from "../../../../components/ui/Alert";
import type { MarketingMediaAsset, MarketingPackDetail } from "../../../../types/marketing";
import { formatDate } from "../../../../workspace/formatters";
import { formatMarketingApiError } from "./marketingErrors";

interface PackDetailMediaTabProps {
  packId: string;
  pack: MarketingPackDetail;
}

const emptyForm = {
  file_name: "",
  mime_type: "image/jpeg",
  storage_provider: "git_path",
  storage_key: "",
  preview_url: "",
  public_url: "",
  alt_text: "",
  width: "",
  height: "",
};

export function PackDetailMediaTab({ packId, pack }: PackDetailMediaTabProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState(emptyForm);
  const [editError, setEditError] = useState<string | null>(null);

  const addMutation = useMutation({
    mutationFn: () =>
      addMarketingPackMedia(packId, {
        file_name: form.file_name.trim(),
        mime_type: form.mime_type.trim(),
        storage_provider: form.storage_provider.trim() || "git_path",
        storage_key: form.storage_key.trim(),
        preview_url: form.preview_url.trim() || undefined,
        public_url: form.public_url.trim() || undefined,
        alt_text: form.alt_text.trim() || undefined,
        width: parseOptionalInt(form.width),
        height: parseOptionalInt(form.height),
      }),
    onSuccess: async () => {
      setForm(emptyForm);
      setFormError(null);
      setFormSuccess("Metadata сохранена.");
      await queryClient.invalidateQueries({ queryKey: ["marketing-pack", packId] });
    },
    onError: (error) => {
      setFormSuccess(null);
      setFormError(formatMarketingApiError(error, "Не удалось добавить media metadata."));
    },
  });

  const updateMutation = useMutation({
    mutationFn: () => {
      if (!editingId) {
        throw new Error("Нет выбранного media asset.");
      }
      return updateMarketingMedia(editingId, {
        file_name: editForm.file_name.trim() || undefined,
        mime_type: editForm.mime_type.trim() || undefined,
        storage_provider: editForm.storage_provider.trim() || undefined,
        storage_key: editForm.storage_key.trim() || undefined,
        preview_url: editForm.preview_url.trim() || undefined,
        public_url: editForm.public_url.trim() || undefined,
        alt_text: editForm.alt_text.trim() || undefined,
        width: parseOptionalInt(editForm.width),
        height: parseOptionalInt(editForm.height),
      });
    },
    onSuccess: async () => {
      setEditingId(null);
      setEditError(null);
      await queryClient.invalidateQueries({ queryKey: ["marketing-pack", packId] });
    },
    onError: (error) => {
      setEditError(formatMarketingApiError(error, "Не удалось обновить media metadata."));
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (assetId: string) => deleteMarketingMedia(assetId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["marketing-pack", packId] });
    },
  });

  const activeAssets = pack.media_assets.filter((asset) => asset.status !== "archived");

  function startEdit(asset: MarketingMediaAsset) {
    setEditingId(asset.id);
    setEditError(null);
    setEditForm({
      file_name: asset.file_name,
      mime_type: asset.mime_type,
      storage_provider: asset.storage_provider,
      storage_key: asset.storage_key,
      preview_url: asset.preview_url ?? "",
      public_url: asset.public_url ?? "",
      alt_text: asset.alt_text ?? "",
      width: asset.width != null ? String(asset.width) : "",
      height: asset.height != null ? String(asset.height) : "",
    });
  }

  return (
    <div className="marketing-pack-tab">
      <h3>Media</h3>
      <Alert variant="info">
        Бинарная загрузка файла пока недоступна. Здесь регистрируется только metadata / ссылка
        (storage_key, preview_url, public_url).
      </Alert>

      <form
        className="panel marketing-media-form"
        onSubmit={(event: FormEvent) => {
          event.preventDefault();
          setFormSuccess(null);
          if (!form.file_name.trim() || !form.storage_key.trim()) {
            setFormError("Укажите file_name и storage_key.");
            return;
          }
          setFormError(null);
          addMutation.mutate();
        }}
      >
        <h4>Добавить metadata</h4>
        <MediaMetadataFields form={form} onChange={setForm} />

        {formError && <Alert variant="error">{formError}</Alert>}
        {formSuccess && <Alert variant="info">{formSuccess}</Alert>}

        <button type="submit" className="btn btn-primary" disabled={addMutation.isPending}>
          {addMutation.isPending ? "Сохранение..." : "Добавить metadata"}
        </button>
      </form>

      <div className="marketing-media-list">
        <h4>Media assets</h4>
        {activeAssets.length === 0 ? (
          <Alert variant="info">Медиа-ассеты пока не добавлены.</Alert>
        ) : (
          activeAssets.map((asset) => (
            <div key={asset.id} className="panel marketing-media-row">
              {editingId === asset.id ? (
                <form
                  onSubmit={(event: FormEvent) => {
                    event.preventDefault();
                    if (!editForm.file_name.trim() || !editForm.storage_key.trim()) {
                      setEditError("Укажите file_name и storage_key.");
                      return;
                    }
                    setEditError(null);
                    updateMutation.mutate();
                  }}
                >
                  <h4>Редактировать metadata</h4>
                  <MediaMetadataFields form={editForm} onChange={setEditForm} />
                  {editError && <Alert variant="error">{editError}</Alert>}
                  <div className="marketing-media-row-actions">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={updateMutation.isPending}
                    >
                      {updateMutation.isPending ? "Сохранение..." : "Сохранить"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={updateMutation.isPending}
                      onClick={() => {
                        setEditingId(null);
                        setEditError(null);
                      }}
                    >
                      Отмена
                    </button>
                  </div>
                </form>
              ) : (
                <MediaAssetRow
                  asset={asset}
                  archiving={archiveMutation.isPending && archiveMutation.variables === asset.id}
                  archiveError={
                    archiveMutation.isError && archiveMutation.variables === asset.id
                      ? formatMarketingApiError(archiveMutation.error, "Не удалось архивировать.")
                      : null
                  }
                  onEdit={() => startEdit(asset)}
                  onArchive={() => archiveMutation.mutate(asset.id)}
                />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function MediaMetadataFields({
  form,
  onChange,
}: {
  form: typeof emptyForm;
  onChange: (next: typeof emptyForm) => void;
}) {
  return (
    <div className="marketing-form-grid">
      <label className="form-field">
        <span className="form-label">file_name</span>
        <input
          className="form-input"
          value={form.file_name}
          onChange={(event) => onChange({ ...form, file_name: event.target.value })}
        />
      </label>
      <label className="form-field">
        <span className="form-label">mime_type</span>
        <input
          className="form-input"
          value={form.mime_type}
          onChange={(event) => onChange({ ...form, mime_type: event.target.value })}
        />
      </label>
      <label className="form-field">
        <span className="form-label">storage_provider</span>
        <input
          className="form-input"
          value={form.storage_provider}
          onChange={(event) => onChange({ ...form, storage_provider: event.target.value })}
        />
      </label>
      <label className="form-field">
        <span className="form-label">storage_key</span>
        <input
          className="form-input"
          value={form.storage_key}
          onChange={(event) => onChange({ ...form, storage_key: event.target.value })}
        />
      </label>
      <label className="form-field">
        <span className="form-label">preview_url (optional)</span>
        <input
          className="form-input"
          value={form.preview_url}
          onChange={(event) => onChange({ ...form, preview_url: event.target.value })}
        />
      </label>
      <label className="form-field">
        <span className="form-label">public_url / asset url (optional)</span>
        <input
          className="form-input"
          value={form.public_url}
          onChange={(event) => onChange({ ...form, public_url: event.target.value })}
        />
      </label>
      <label className="form-field">
        <span className="form-label">alt_text (optional)</span>
        <input
          className="form-input"
          value={form.alt_text}
          onChange={(event) => onChange({ ...form, alt_text: event.target.value })}
        />
      </label>
      <label className="form-field">
        <span className="form-label">width (optional)</span>
        <input
          className="form-input"
          type="number"
          min={1}
          value={form.width}
          onChange={(event) => onChange({ ...form, width: event.target.value })}
        />
      </label>
      <label className="form-field">
        <span className="form-label">height (optional)</span>
        <input
          className="form-input"
          type="number"
          min={1}
          value={form.height}
          onChange={(event) => onChange({ ...form, height: event.target.value })}
        />
      </label>
    </div>
  );
}

function MediaAssetRow({
  asset,
  archiving,
  archiveError,
  onEdit,
  onArchive,
}: {
  asset: MarketingMediaAsset;
  archiving: boolean;
  archiveError: string | null;
  onEdit: () => void;
  onArchive: () => void;
}) {
  return (
    <>
      <div className="marketing-media-row-header">
        <strong>{asset.file_name}</strong>
        <span className="badge">{asset.status}</span>
      </div>
      <dl className="detail-list marketing-media-meta">
        <dt>role</dt>
        <dd>{asset.role}</dd>
        <dt>mime_type</dt>
        <dd>{asset.mime_type}</dd>
        <dt>storage</dt>
        <dd>
          {asset.storage_provider} · <code>{asset.storage_key}</code>
        </dd>
        {asset.preview_url && (
          <>
            <dt>preview_url</dt>
            <dd>{asset.preview_url}</dd>
          </>
        )}
        {asset.public_url && (
          <>
            <dt>public_url</dt>
            <dd>{asset.public_url}</dd>
          </>
        )}
        {asset.alt_text && (
          <>
            <dt>alt_text</dt>
            <dd>{asset.alt_text}</dd>
          </>
        )}
        {(asset.width || asset.height) && (
          <>
            <dt>size</dt>
            <dd>
              {asset.width ?? "—"} × {asset.height ?? "—"}
            </dd>
          </>
        )}
        <dt>updated</dt>
        <dd>{formatDate(asset.updated_at)}</dd>
      </dl>
      <div className="marketing-media-row-actions">
        <button type="button" className="btn btn-secondary" onClick={onEdit}>
          Редактировать
        </button>
        <button type="button" className="btn btn-secondary" disabled={archiving} onClick={onArchive}>
          {archiving ? "Архивация..." : "Архивировать"}
        </button>
      </div>
      {archiveError && <Alert variant="error">{archiveError}</Alert>}
    </>
  );
}

function parseOptionalInt(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}
