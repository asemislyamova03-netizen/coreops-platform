import type { SelectHTMLAttributes } from "react";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
  emptyLabel?: string;
}

export function Select({
  label,
  id,
  options,
  emptyLabel,
  className = "",
  ...props
}: SelectProps) {
  const selectId = id || props.name;
  return (
    <label className={`form-field ${className}`.trim()} htmlFor={selectId}>
      <span className="form-label">{label}</span>
      <select id={selectId} className="form-select" {...props}>
        {emptyLabel !== undefined && <option value="">{emptyLabel}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}
