import {
  CRM_BOARD_VIEW_OPTIONS,
  type CrmBoardViewMode,
} from "../../workspace/crmPipelineBoardHelpers";

interface CrmBoardViewSwitcherProps {
  value: CrmBoardViewMode;
  onChange: (value: CrmBoardViewMode) => void;
}

export function CrmBoardViewSwitcher({ value, onChange }: CrmBoardViewSwitcherProps) {
  return (
    <div className="crm-board-view-toolbar">
      <span className="crm-board-view-label">Вид:</span>
      <div className="crm-board-view-toggle" role="group" aria-label="Вид CRM-доски">
        {CRM_BOARD_VIEW_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`btn btn-secondary crm-board-view-btn${
              value === option.value ? " is-active" : ""
            }`}
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
