import type { PipelineStage } from "../../types/workflows";
import type { CrmListStageFilter } from "../../workspace/crmPipelineBoardHelpers";

interface CrmStageFilterProps {
  stages: PipelineStage[];
  value: CrmListStageFilter;
  onChange: (value: CrmListStageFilter) => void;
}

export function CrmStageFilter({ stages, value, onChange }: CrmStageFilterProps) {
  const sortedStages = [...stages].sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div className="crm-board-view-toolbar crm-stage-filter-toolbar">
      <label className="crm-board-view-label" htmlFor="crm-list-stage-filter">
        Стадия:
      </label>
      <select
        id="crm-list-stage-filter"
        className="form-select crm-stage-filter-select"
        value={value}
        onChange={(event) => {
          const next = event.target.value;
          onChange(next === "all" ? "all" : next);
        }}
      >
        <option value="all">Все стадии</option>
        {sortedStages.map((stage) => (
          <option key={stage.id} value={stage.id}>
            {stage.name}
          </option>
        ))}
      </select>
    </div>
  );
}
