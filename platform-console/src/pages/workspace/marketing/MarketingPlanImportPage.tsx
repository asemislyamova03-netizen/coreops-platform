import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChangeEvent, FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  commitMarketingContentPlanImport,
  listMarketingRubrics,
  previewMarketingContentPlanImport,
} from "../../../api/marketing";
import { Alert } from "../../../components/ui/Alert";
import { Button } from "../../../components/ui/Button";
import { Loading } from "../../../components/ui/Loading";
import { ui } from "../../../i18n/ruUi";
import type { MarketingContentPlanImportPreviewResponse } from "../../../types/marketing";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import { formatMarketingApiError } from "./packDetail/marketingErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";

export function MarketingPlanImportPage() {
  const { tenantSlug = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isLoading: labelsLoading } = useWorkspaceLabels();
  const base = `/workspace/${tenantSlug}/marketing`;

  const [rawJson, setRawJson] = useState("");
  const [preview, setPreview] = useState<MarketingContentPlanImportPreviewResponse | null>(
    null,
  );
  const [rubricMap, setRubricMap] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const rubricsQuery = useQuery({
    queryKey: ["marketing-rubrics-active"],
    queryFn: () => listMarketingRubrics({ status: "active" }),
    enabled: !labelsLoading,
  });
  const rubrics = rubricsQuery.data ?? [];

  const previewMutation = useMutation({
    mutationFn: previewMarketingContentPlanImport,
    onSuccess: (data) => {
      setPreview(data);
      setError(null);
    },
    onError: (err) => {
      setPreview(null);
      setError(formatMarketingApiError(err, "Preview не выполнен."));
    },
  });
  const commitMutation = useMutation({
    mutationFn: commitMarketingContentPlanImport,
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({ queryKey: ["marketing-content-plans"] });
      navigate(`${base}/plans/${data.plan.id}`);
    },
    onError: (err) => setError(formatMarketingApiError(err, "Import commit не выполнен.")),
  });

  const parsedPlan = useMemo(() => {
    const trimmed = rawJson.trim();
    if (!trimmed) return null;
    try {
      return JSON.parse(trimmed) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [rawJson]);

  if (labelsLoading || rubricsQuery.isLoading) {
    return <Loading text="Загрузка импорта..." />;
  }

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setRawJson(String(reader.result ?? ""));
      setPreview(null);
    };
    reader.readAsText(file);
  }

  function onPreview(event: FormEvent) {
    event.preventDefault();
    if (!rawJson.trim()) {
      setError("Вставьте JSON или загрузите .json файл.");
      return;
    }
    if (!parsedPlan) {
      setError("JSON невалиден — исправьте текст перед preview.");
      return;
    }
    previewMutation.mutate({
      plan: parsedPlan,
      rubric_code_map: Object.keys(rubricMap).length ? rubricMap : undefined,
    });
  }

  function onCommit() {
    if (!preview?.valid || !parsedPlan) return;
    if (
      !window.confirm(
        preview.fingerprint_already_imported
          ? "Такой импорт уже был. Повторить commit (replay без дубля)?"
          : `Импортировать план: ${preview.resolved_items.length} строк?`,
      )
    ) {
      return;
    }
    commitMutation.mutate({
      plan: parsedPlan,
      rubric_code_map: Object.keys(rubricMap).length ? rubricMap : undefined,
    });
  }

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingPlanImport}
        subtitle="Preview без записи. Commit создаёт draft-план и строки. Файл никуда не уходит."
      />
      <p>
        <Link to={`${base}/plans`}>← К контент-планам</Link>
      </p>

      {error ? <Alert variant="error">{error}</Alert> : null}

      <form className="panel" onSubmit={onPreview}>
        <label>
          JSON плана (m7.5.plan.v1)
          <textarea
            className="form-input"
            rows={14}
            value={rawJson}
            onChange={(e) => {
              setRawJson(e.target.value);
              setPreview(null);
            }}
            placeholder='{"schema_version":"m7.5.plan.v1", ...}'
          />
        </label>
        <label style={{ display: "block", marginTop: "0.75rem" }}>
          Или локальный .json файл
          <input type="file" accept="application/json,.json" onChange={onFile} />
        </label>
        <div style={{ marginTop: "1rem" }}>
          <Button type="submit" disabled={previewMutation.isPending}>
            {previewMutation.isPending ? "Проверка…" : "Preview"}
          </Button>
        </div>
      </form>

      {preview ? (
        <section className="panel" style={{ marginTop: "1rem" }}>
          <h2>Результат preview</h2>
          <p>
            Валидность: <strong>{preview.valid ? "OK" : "есть ошибки"}</strong>
            {" · "}
            строк: {preview.resolved_items.length}
            {parsedPlan && typeof parsedPlan.period_start === "string" ? (
              <>
                {" · "}
                период: {String(parsedPlan.period_start)} → {String(parsedPlan.period_end)}
              </>
            ) : null}
          </p>
          {preview.fingerprint_already_imported ? (
            <Alert variant="info">
              Такой план уже импортировался ранее. Commit вернёт существующий план (replay), без
              дубля.
            </Alert>
          ) : null}

          {preview.errors.length > 0 ? (
            <Alert variant="error">
              <ul>
                {preview.errors.map((issue) => (
                  <li key={`${issue.code}-${issue.path}`}>
                    {issue.path}: {issue.message}
                  </li>
                ))}
              </ul>
            </Alert>
          ) : null}
          {preview.warnings.length > 0 ? (
            <Alert variant="info">
              <ul>
                {preview.warnings.map((issue) => (
                  <li key={`${issue.code}-${issue.path}`}>
                    {issue.path}: {issue.message}
                  </li>
                ))}
              </ul>
            </Alert>
          ) : null}

          {preview.unknown_rubric_codes.length > 0 ? (
            <div style={{ marginTop: "1rem" }}>
              <h3>Неизвестные rubric_code</h3>
              <p className="muted">
                Сопоставьте с active рубрикой tenant или{" "}
                <Link to={`${base}/rubrics`}>создайте рубрику</Link>, затем повторите preview.
                Автосоздание запрещено.
              </p>
              {preview.unknown_rubric_codes.map((code) => (
                <label key={code} style={{ display: "block", marginBottom: "0.5rem" }}>
                  {code} →{" "}
                  <select
                    className="form-select"
                    value={rubricMap[code] ?? ""}
                    onChange={(e) => {
                      const value = e.target.value;
                      setRubricMap((prev) => {
                        const next = { ...prev };
                        if (!value) delete next[code];
                        else next[code] = value;
                        return next;
                      });
                      setPreview(null);
                    }}
                  >
                    <option value="">Не выбрано</option>
                    {rubrics.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.name} ({row.code})
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              <Button
                type="button"
                variant="secondary"
                disabled={previewMutation.isPending || !parsedPlan}
                onClick={() =>
                  parsedPlan &&
                  previewMutation.mutate({
                    plan: parsedPlan,
                    rubric_code_map: Object.keys(rubricMap).length ? rubricMap : undefined,
                  })
                }
              >
                Повторить preview с mapping
              </Button>
            </div>
          ) : null}

          <div style={{ marginTop: "1rem" }}>
            <Button
              type="button"
              disabled={!preview.valid || commitMutation.isPending}
              onClick={onCommit}
            >
              {commitMutation.isPending ? "Импорт…" : "Commit import"}
            </Button>
            {!preview.valid ? (
              <p className="muted">Commit доступен только после успешного preview.</p>
            ) : (
              <p className="muted">После импорта откроется карточка draft-плана.</p>
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
