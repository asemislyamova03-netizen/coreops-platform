import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  exportMarketingContentPlanPrompt,
  getActiveMarketingGuide,
  listMarketingRubrics,
} from "../../../api/marketing";
import { ApiError } from "../../../api/client";
import { Alert } from "../../../components/ui/Alert";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Loading } from "../../../components/ui/Loading";
import { ui } from "../../../i18n/ruUi";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import { formatMarketingApiError } from "./packDetail/marketingErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";
import { PLAN_CHANNEL_OPTIONS } from "./marketingPlanLabels";

export function MarketingPlanPromptPage() {
  const { tenantSlug = "" } = useParams();
  const { isLoading: labelsLoading } = useWorkspaceLabels();
  const base = `/workspace/${tenantSlug}/marketing`;

  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [targetCount, setTargetCount] = useState("8");
  const [frequency, setFrequency] = useState("");
  const [channels, setChannels] = useState<string[]>(["telegram", "instagram"]);
  const [extra, setExtra] = useState("");
  const [copyDone, setCopyDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const guideQuery = useQuery({
    queryKey: ["marketing-guide-active"],
    queryFn: getActiveMarketingGuide,
    enabled: !labelsLoading,
    retry: false,
  });
  const rubricsQuery = useQuery({
    queryKey: ["marketing-rubrics-active"],
    queryFn: () => listMarketingRubrics({ status: "active" }),
    enabled: !labelsLoading,
  });

  const exportMutation = useMutation({
    mutationFn: exportMarketingContentPlanPrompt,
    onError: (err) => setError(formatMarketingApiError(err, "Не удалось сформировать промпт.")),
    onSuccess: () => setError(null),
  });

  const guideMissing =
    guideQuery.error instanceof ApiError && guideQuery.error.status === 404;
  const rubrics = rubricsQuery.data ?? [];
  const prompt = exportMutation.data;

  const selectedRubricIds = useMemo(() => rubrics.map((r) => r.id), [rubrics]);

  if (labelsLoading || (guideQuery.isLoading && !guideQuery.isError) || rubricsQuery.isLoading) {
    return <Loading text="Подготовка prompt export..." />;
  }

  function toggleChannel(channel: string) {
    setChannels((prev) =>
      prev.includes(channel) ? prev.filter((c) => c !== channel) : [...prev, channel],
    );
  }

  function onExport(event: FormEvent) {
    event.preventDefault();
    setCopyDone(false);
    if (!periodStart || !periodEnd || channels.length === 0) {
      setError("Укажите период и хотя бы один канал.");
      return;
    }
    const count = targetCount.trim() ? Number(targetCount) : null;
    exportMutation.mutate({
      period_start: periodStart,
      period_end: periodEnd,
      channels,
      target_item_count: count && Number.isFinite(count) ? count : null,
      frequency: frequency.trim() || null,
      rubric_ids: selectedRubricIds.length ? selectedRubricIds : null,
      additional_instructions: extra.trim() || null,
      language: "ru",
    });
  }

  async function copyPrompt() {
    if (!prompt?.prompt_text) return;
    await navigator.clipboard.writeText(prompt.prompt_text);
    setCopyDone(true);
  }

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingPlanPrompt}
        subtitle="Скопируйте промпт во внешний AI. Flexity сам модели не вызывает."
      />
      <p>
        <Link to={`${base}/plans`}>← К контент-планам</Link>
      </p>

      {guideMissing ? (
        <Alert variant="info">
          Active Marketing Guide не настроен.{" "}
          <Link to={`${base}/guide`}>Откройте Guide</Link> и активируйте его.
        </Alert>
      ) : null}
      {!guideMissing && rubrics.length === 0 ? (
        <Alert variant="info">
          Нет active рубрик. <Link to={`${base}/rubrics`}>Создайте рубрики</Link>, затем
          сформируйте промпт.
        </Alert>
      ) : null}

      {error ? <Alert variant="error">{error}</Alert> : null}

      <form className="panel marketing-form-grid" onSubmit={onExport}>
        <Input
          label="Начало периода"
          type="date"
          value={periodStart}
          onChange={(e) => setPeriodStart(e.target.value)}
        />
        <Input
          label="Конец периода"
          type="date"
          value={periodEnd}
          onChange={(e) => setPeriodEnd(e.target.value)}
        />
        <Input
          label="Число публикаций"
          value={targetCount}
          onChange={(e) => setTargetCount(e.target.value)}
        />
        <Input
          label="Или частота (если без числа)"
          value={frequency}
          placeholder="daily / 3x week"
          onChange={(e) => setFrequency(e.target.value)}
        />
        <fieldset>
          <legend>Каналы</legend>
          {PLAN_CHANNEL_OPTIONS.map((channel) => (
            <label key={channel} style={{ display: "inline-flex", marginRight: "0.75rem" }}>
              <input
                type="checkbox"
                checked={channels.includes(channel)}
                onChange={() => toggleChannel(channel)}
              />{" "}
              {channel}
            </label>
          ))}
        </fieldset>
        <label className="form-field marketing-form-span-2">
          <span className="form-label">Дополнительные инструкции</span>
          <textarea
            className="form-input"
            rows={4}
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
          />
        </label>
        <p className="muted">
          Будут использованы: Guide v{guideQuery.data?.version ?? "—"}, active rubrics:{" "}
          {rubrics.map((r) => r.code).join(", ") || "—"}.
        </p>
        <Button
          type="submit"
          disabled={exportMutation.isPending || guideMissing || rubrics.length === 0}
        >
          {exportMutation.isPending ? "Формирование…" : "Сформировать промпт"}
        </Button>
      </form>

      {prompt ? (
        <section className="panel" style={{ marginTop: "1rem" }}>
          <h2>Промпт готов</h2>
          <p className="muted">
            schema {prompt.schema_version} · guide v{prompt.guide_version} · рубрики:{" "}
            {prompt.rubric_codes.join(", ")}
          </p>
          <Button type="button" onClick={() => void copyPrompt()}>
            {copyDone ? "Скопировано" : "Копировать промпт"}
          </Button>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              marginTop: "1rem",
              maxHeight: "28rem",
              overflow: "auto",
            }}
          >
            {prompt.prompt_text}
          </pre>
          <p className="muted" style={{ marginTop: "1rem" }}>
            Дальше: вставьте ответ модели в{" "}
            <Link to={`${base}/plans/import`}>Импорт JSON</Link>.
          </p>
        </section>
      ) : null}
    </div>
  );
}
