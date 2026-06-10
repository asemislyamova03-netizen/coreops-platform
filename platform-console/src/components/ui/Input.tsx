import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Input({ label, id, className = "", ...props }: InputProps) {
  const inputId = id || props.name;
  return (
    <label className={`form-field ${className}`.trim()} htmlFor={inputId}>
      <span className="form-label">{label}</span>
      <input id={inputId} className="form-input" {...props} />
    </label>
  );
}
