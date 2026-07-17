import {
  CRM_DISPLAY_MODE_OPTIONS,
  type CrmDisplayMode,
} from "../../workspace/crmPipelineBoardHelpers";

interface CrmDisplayModeSwitcherProps {
  value: CrmDisplayMode;
  onChange: (value: CrmDisplayMode) => void;
}

export function CrmDisplayModeSwitcher({ value, onChange }: CrmDisplayModeSwitcherProps) {
  return (
    <div className="crm-board-view-toolbar crm-display-mode-toolbar">
      <span className="crm-board-view-label">Отображение:</span>
      <div className="crm-board-view-toggle" role="group" aria-label="Режим отображения CRM">
        {CRM_DISPLAY_MODE_OPTIONS.map((option) => (
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
