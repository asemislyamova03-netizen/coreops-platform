import {
  CRM_CARD_DENSITY_OPTIONS,
  type CrmCardDensity,
} from "../../workspace/crmPipelineBoardHelpers";

interface CrmCardDensitySwitcherProps {
  value: CrmCardDensity;
  onChange: (value: CrmCardDensity) => void;
}

export function CrmCardDensitySwitcher({ value, onChange }: CrmCardDensitySwitcherProps) {
  return (
    <div className="crm-board-view-toolbar crm-card-density-toolbar">
      <span className="crm-board-view-label">Вид карточек:</span>
      <div className="crm-board-view-toggle" role="group" aria-label="Плотность карточек CRM">
        {CRM_CARD_DENSITY_OPTIONS.map((option) => (
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
