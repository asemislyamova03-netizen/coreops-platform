import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  activateMarketingRubric,
  archiveMarketingRubric,
  createMarketingRubric,
  deactivateMarketingRubric,
  listMarketingRubrics,
  seedMarketingRubricDefaults,
  updateMarketingRubric,
} from "../../../api/marketing";
import { Alert } from "../../../components/ui/Alert";
import { Loading } from "../../../components/ui/Loading";
import { Table } from "../../../components/ui/Table";
import type { MarketingRubric } from "../../../types/marketing";
import { ui } from "../../../i18n/ruUi";
import { useWorkspaceLabels } from "../../../workspace/WorkspaceLabelsContext";
import {
  firstBlockingError,
  isModuleDisabled,
  moduleDisabledMessage,
} from "../../../workspace/moduleErrors";
import { MarketingPageHeader } from "./MarketingPageHeader";
import { formatMarketingApiError } from "./packDetail/marketingErrors";

export function MarketingRubricsPage() {
  const queryClient = useQueryClient();
  const { isLoading: labelsLoading } = useWorkspaceLabels();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [sortOrder, setSortOrder] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [seedNote, setSeedNote] = useState<string | null>(null);

  const rubricsQuery = useQuery({
    queryKey: ["marketing-rubrics-all"],
    queryFn: () => listMarketingRubrics({ include_archived: true }),
    enabled: !labelsLoading,
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["marketing-rubrics-all"] });
    await queryClient.invalidateQueries({ queryKey: ["marketing-rubrics-active"] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createMarketingRubric({
        code: code.trim(),
        name: name.trim(),
        description: description.trim() || null,
        content_instructions: instructions.trim() || null,
        sort_order: sortOrder,
      }),
    onSuccess: async () => {
      setError(null);
      setCode("");
      setName("");
      setDescription("");
      setInstructions("");
      await refresh();
    },
    onError: (err) => setError(formatMarketingApiError(err, "Не удалось создать рубрику.")),
  });

  const seedMutation = useMutation({
    mutationFn: () => seedMarketingRubricDefaults(false),
    onSuccess: async (result) => {
      setSeedNote(
        `Seed: created=${result.created}, skipped=${result.skipped}, updated=${result.updated}`,
      );
      await refresh();
    },
    onError: (err) => setError(formatMarketingApiError(err, "Не удалось выполнить seed.")),
  });

  if (labelsLoading || rubricsQuery.isLoading) {
    return <Loading text="Загрузка рубрик..." />;
  }

  const marketingDisabled = isModuleDisabled("marketing", rubricsQuery.error);
  const blocking = firstBlockingError(rubricsQuery.error);

  if (marketingDisabled && !blocking) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingRubrics}
          subtitle="Постоянный справочник рубрик tenant."
        />
        <Alert variant="info">{moduleDisabledMessage("marketing")}</Alert>
      </div>
    );
  }

  if (blocking) {
    return (
      <div className="page">
        <MarketingPageHeader
          title={ui.marketingRubrics}
          subtitle="Постоянный справочник рубрик tenant."
        />
        <Alert variant="error">{formatMarketingApiError(blocking, "Не удалось загрузить рубрики.")}</Alert>
      </div>
    );
  }

  const rows = rubricsQuery.data ?? [];

  function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!code.trim() || !name.trim()) {
      setError("Нужны code и name.");
      return;
    }
    createMutation.mutate();
  }

  async function runLifecycle(
    action: "activate" | "deactivate" | "archive",
    rubric: MarketingRubric,
  ) {
    setError(null);
    try {
      if (action === "activate") await activateMarketingRubric(rubric.id);
      if (action === "deactivate") await deactivateMarketingRubric(rubric.id);
      if (action === "archive") await archiveMarketingRubric(rubric.id);
      await refresh();
    } catch (err) {
      setError(formatMarketingApiError(err, "Не удалось изменить статус рубрики."));
    }
  }

  async function rename(rubric: MarketingRubric) {
    const next = window.prompt("Новое имя рубрики", rubric.name);
    if (!next || !next.trim()) return;
    try {
      await updateMarketingRubric(rubric.id, { name: next.trim() });
      await refresh();
    } catch (err) {
      setError(formatMarketingApiError(err, "Не удалось переименовать рубрику."));
    }
  }

  return (
    <div className="page">
      <MarketingPageHeader
        title={ui.marketingRubrics}
        subtitle="Reusable directory. Не путать с Topics (расходуемые идеи публикаций)."
      />
      {error ? <Alert variant="error">{error}</Alert> : null}
      {seedNote ? <Alert variant="info">{seedNote}</Alert> : null}

      <div className="panel">
        <button
          type="button"
          className="btn"
          disabled={seedMutation.isPending}
          onClick={() => seedMutation.mutate()}
        >
          Seed defaults (idempotent, этот tenant)
        </button>
      </div>

      <form className="panel marketing-topic-create" onSubmit={onCreate}>
        <h3>Новая рубрика</h3>
        <div className="marketing-form-grid">
          <label className="form-field">
            <span className="form-label">code</span>
            <input
              className="form-input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="asem_column"
            />
          </label>
          <label className="form-field">
            <span className="form-label">name</span>
            <input
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="form-field">
            <span className="form-label">sort_order</span>
            <input
              className="form-input"
              type="number"
              value={sortOrder}
              onChange={(e) => setSortOrder(Number(e.target.value) || 0)}
            />
          </label>
          <label className="form-field marketing-form-span-2">
            <span className="form-label">description</span>
            <textarea
              className="form-input marketing-textarea"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <label className="form-field marketing-form-span-2">
            <span className="form-label">content_instructions</span>
            <textarea
              className="form-input marketing-textarea"
              rows={2}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
            />
          </label>
        </div>
        <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
          Создать
        </button>
      </form>

      <div className="panel">
        <Table<MarketingRubric>
          rowKey={(row) => row.id}
          emptyText="Рубрик пока нет — создайте или выполните seed."
          columns={[
            { key: "code", header: "code", render: (row) => row.code },
            { key: "name", header: "name", render: (row) => row.name },
            { key: "status", header: "status", render: (row) => row.status },
            { key: "sort", header: "sort", render: (row) => String(row.sort_order) },
            {
              key: "actions",
              header: "actions",
              render: (row) => (
                <div className="table-actions">
                  <button type="button" className="btn btn-sm" onClick={() => rename(row)}>
                    Rename
                  </button>
                  {row.status !== "active" ? (
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => runLifecycle("activate", row)}
                    >
                      Activate
                    </button>
                  ) : null}
                  {row.status === "active" ? (
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => runLifecycle("deactivate", row)}
                    >
                      Deactivate
                    </button>
                  ) : null}
                  {row.status !== "archived" ? (
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => runLifecycle("archive", row)}
                    >
                      Archive
                    </button>
                  ) : null}
                </div>
              ),
            },
          ]}
          data={rows}
        />
      </div>
    </div>
  );
}
