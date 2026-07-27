import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  activateMarketingGuide,
  createMarketingGuide,
  getActiveMarketingGuide,
  updateMarketingGuide,
} from "../../../api/marketing";
import { ApiError } from "../../../api/client";
import { Alert } from "../../../components/ui/Alert";
import { Loading } from "../../../components/ui/Loading";
import type { MarketingGuide, MarketingGuideCreatePayload } from "../../../types/marketing";
import { ui } from "../../../i18n/ruUi";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import {
  firstBlockingError,
  isModuleDisabled,
  moduleDisabledMessage,
} from "../../../workspace/moduleErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";
import { formatMarketingApiError } from "./packDetail/marketingErrors";

type GuideForm = {
  business_name: string;
  business_summary: string;
  products_services: string;
  audiences: string;
  goals: string;
  channels: string;
  default_frequency: string;
  tone_rules: string;
  constraints: string;
  sources_notes: string;
};

const EMPTY: GuideForm = {
  business_name: "",
  business_summary: "",
  products_services: "",
  audiences: "",
  goals: "",
  channels: "telegram, instagram, threads, insights",
  default_frequency: "daily",
  tone_rules: "",
  constraints: "",
  sources_notes: "",
};

function formFromGuide(guide: MarketingGuide): GuideForm {
  return {
    business_name: guide.business_name,
    business_summary: guide.business_summary,
    products_services: guide.products_services,
    audiences: guide.audiences,
    goals: guide.goals,
    channels: (guide.channels ?? []).join(", "),
    default_frequency: guide.default_frequency,
    tone_rules: guide.tone_rules ?? "",
    constraints: guide.constraints ?? "",
    sources_notes: guide.sources_notes ?? "",
  };
}

function toPayload(form: GuideForm, activate: boolean): MarketingGuideCreatePayload {
  return {
    business_name: form.business_name.trim(),
    business_summary: form.business_summary.trim(),
    products_services: form.products_services.trim(),
    audiences: form.audiences.trim(),
    goals: form.goals.trim(),
    channels: form.channels
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    default_frequency: form.default_frequency.trim() || "daily",
    tone_rules: form.tone_rules.trim() || null,
    constraints: form.constraints.trim() || null,
    sources_notes: form.sources_notes.trim() || null,
    activate,
  };
}

export function MarketingGuidePage() {
  const queryClient = useQueryClient();
  const { isLoading: labelsLoading } = useWorkspaceLabels();
  const [form, setForm] = useState<GuideForm>(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  const activeQuery = useQuery({
    queryKey: ["marketing-guide-active"],
    queryFn: getActiveMarketingGuide,
    enabled: !labelsLoading,
    retry: false,
  });

  useEffect(() => {
    if (activeQuery.data) {
      setForm(formFromGuide(activeQuery.data));
      setEditingId(activeQuery.data.id);
    }
  }, [activeQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async (activate: boolean) => {
      const createPayload = toPayload(form, activate);
      if (editingId) {
        const { activate: _ignored, ...updatePayload } = createPayload;
        const updated = await updateMarketingGuide(editingId, updatePayload);
        if (activate) {
          return activateMarketingGuide(editingId);
        }
        return updated;
      }
      return createMarketingGuide(createPayload);
    },
    onSuccess: async (guide) => {
      setFormError(null);
      setEditingId(guide.id);
      setForm(formFromGuide(guide));
      await queryClient.invalidateQueries({ queryKey: ["marketing-guide-active"] });
    },
    onError: (error) => {
      setFormError(formatMarketingApiError(error, "Не удалось сохранить Guide."));
    },
  });

  if (labelsLoading || (activeQuery.isLoading && !activeQuery.isError)) {
    return <Loading text="Загрузка Marketing Guide..." />;
  }

  const marketingDisabled = isModuleDisabled("marketing", activeQuery.error);
  const blocking = firstBlockingError(activeQuery.error);
  const notFound =
    activeQuery.error instanceof ApiError && activeQuery.error.status === 404;

  if (marketingDisabled && !blocking && !notFound) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingGuide}
          subtitle="Бриф tenant для планирования контента."
        />
        <Alert variant="info">{moduleDisabledMessage("marketing")}</Alert>
      </div>
    );
  }

  if (blocking && !notFound) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingGuide}
          subtitle="Бриф tenant для планирования контента."
        />
        <Alert variant="error">{formatMarketingApiError(blocking, "Не удалось загрузить Guide.")}</Alert>
      </div>
    );
  }

  function onSubmit(event: FormEvent, activate: boolean) {
    event.preventDefault();
    if (!form.business_name.trim() || !form.business_summary.trim()) {
      setFormError("Заполните название бизнеса и краткое описание.");
      return;
    }
    saveMutation.mutate(activate);
  }

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingGuide}
        subtitle="Один active guide на tenant. AI API в этом срезе нет — только бриф."
      />
      {notFound ? (
        <Alert variant="info">Active guide ещё нет — создайте черновик или сразу активируйте.</Alert>
      ) : null}
      {activeQuery.data ? (
        <p className="muted">
          Active v{activeQuery.data.version} · {activeQuery.data.status} · id{" "}
          {activeQuery.data.id.slice(0, 8)}…
        </p>
      ) : null}
      {formError ? <Alert variant="error">{formError}</Alert> : null}

      <form className="panel marketing-topic-create" onSubmit={(e) => onSubmit(e, false)}>
        <div className="marketing-form-grid">
          {(
            [
              ["business_name", "Бизнес / бренд"],
              ["business_summary", "Кратко о бизнесе"],
              ["products_services", "Продукты / услуги"],
              ["audiences", "Аудитории"],
              ["goals", "Цели периода"],
              ["channels", "Каналы (через запятую)"],
              ["default_frequency", "Частота"],
              ["tone_rules", "Tone rules"],
              ["constraints", "Ограничения"],
              ["sources_notes", "Notes по источникам"],
            ] as const
          ).map(([key, label]) => (
            <label
              key={key}
              className={`form-field ${
                key === "business_name" || key === "default_frequency" || key === "channels"
                  ? ""
                  : "marketing-form-span-2"
              }`}
            >
              <span className="form-label">{label}</span>
              {key === "business_name" ||
              key === "default_frequency" ||
              key === "channels" ? (
                <input
                  className="form-input"
                  value={form[key]}
                  onChange={(event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))}
                />
              ) : (
                <textarea
                  className="form-input marketing-textarea"
                  rows={3}
                  value={form[key]}
                  onChange={(event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))}
                />
              )}
            </label>
          ))}
        </div>
        <div className="form-actions">
          <button type="submit" className="btn" disabled={saveMutation.isPending}>
            Сохранить
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={saveMutation.isPending}
            onClick={(event) => onSubmit(event, true)}
          >
            Сохранить и активировать
          </button>
        </div>
      </form>
    </div>
  );
}
