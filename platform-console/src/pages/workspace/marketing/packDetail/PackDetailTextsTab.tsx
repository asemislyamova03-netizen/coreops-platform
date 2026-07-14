import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { updateMarketingPackText } from "../../../../api/marketing";
import { Alert } from "../../../../components/ui/Alert";
import type { MarketingChannel, MarketingPackDetail } from "../../../../types/marketing";
import { MARKETING_CHANNELS } from "../../../../types/marketing";
import { formatMarketingApiError } from "./marketingErrors";

interface PackDetailTextsTabProps {
  packId: string;
  pack: MarketingPackDetail;
}

type ChannelSaveState = "idle" | "saved" | "error";

export function PackDetailTextsTab({ packId, pack }: PackDetailTextsTabProps) {
  const queryClient = useQueryClient();
  const textByChannel = useMemo(() => {
    const map = new Map<string, (typeof pack.texts)[number]>();
    for (const row of pack.texts) {
      map.set(row.channel, row);
    }
    return map;
  }, [pack.texts]);

  const [drafts, setDrafts] = useState<Record<MarketingChannel, string>>(() =>
    buildDrafts(textByChannel),
  );
  const [saveState, setSaveState] = useState<Record<MarketingChannel, ChannelSaveState>>(() =>
    emptySaveState(),
  );
  const [saveErrors, setSaveErrors] = useState<Partial<Record<MarketingChannel, string>>>({});

  useEffect(() => {
    setDrafts(buildDrafts(textByChannel));
    setSaveState(emptySaveState());
    setSaveErrors({});
  }, [pack.updated_at, textByChannel]);

  const saveMutation = useMutation({
    mutationFn: ({ channel, text }: { channel: MarketingChannel; text: string }) =>
      updateMarketingPackText(packId, channel, { text }),
    onSuccess: async (_data, variables) => {
      setSaveState((prev) => ({ ...prev, [variables.channel]: "saved" }));
      setSaveErrors((prev) => ({ ...prev, [variables.channel]: undefined }));
      await queryClient.invalidateQueries({ queryKey: ["marketing-pack", packId] });
    },
    onError: (error, variables) => {
      setSaveState((prev) => ({ ...prev, [variables.channel]: "error" }));
      setSaveErrors((prev) => ({
        ...prev,
        [variables.channel]: formatMarketingApiError(error, "Не удалось сохранить текст."),
      }));
    },
  });

  return (
    <div className="marketing-pack-tab">
      <h3>Texts</h3>
      <p className="muted">
        Редактирование текстов по каналам. После сохранения pack detail обновляется; при изменении
        текстов backend может сбросить preflight/approval.
      </p>

      <div className="marketing-channel-list">
        {MARKETING_CHANNELS.map((channel) => {
          const saved = textByChannel.get(channel);
          const state = saveState[channel];
          return (
            <div key={channel} className="panel marketing-channel-block">
              <div className="marketing-channel-header">
                <strong>{channel}</strong>
                {saved && (
                  <span className="muted">
                    v{saved.version} · {saved.char_count} симв. · {saved.status}
                  </span>
                )}
              </div>

              <label className="form-field">
                <span className="form-label">Текст</span>
                <textarea
                  className="form-input workspace-textarea"
                  rows={5}
                  value={drafts[channel]}
                  onChange={(event) => {
                    setDrafts((prev) => ({ ...prev, [channel]: event.target.value }));
                    setSaveState((prev) => ({ ...prev, [channel]: "idle" }));
                  }}
                />
              </label>

              <div className="marketing-channel-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={saveMutation.isPending && saveMutation.variables?.channel === channel}
                  onClick={() => {
                    setSaveState((prev) => ({ ...prev, [channel]: "idle" }));
                    saveMutation.mutate({ channel, text: drafts[channel] });
                  }}
                >
                  {saveMutation.isPending && saveMutation.variables?.channel === channel
                    ? "Сохранение..."
                    : "Сохранить"}
                </button>
                {state === "saved" && <span className="marketing-save-ok">Сохранено</span>}
              </div>

              {saveErrors[channel] && <Alert variant="error">{saveErrors[channel]}</Alert>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function buildDrafts(textByChannel: Map<string, { text: string }>): Record<MarketingChannel, string> {
  return MARKETING_CHANNELS.reduce(
    (acc, channel) => {
      acc[channel] = textByChannel.get(channel)?.text ?? "";
      return acc;
    },
    {} as Record<MarketingChannel, string>,
  );
}

function emptySaveState(): Record<MarketingChannel, ChannelSaveState> {
  return MARKETING_CHANNELS.reduce(
    (acc, channel) => {
      acc[channel] = "idle";
      return acc;
    },
    {} as Record<MarketingChannel, ChannelSaveState>,
  );
}
