import type { ReactNode } from "react";

interface WorkspaceModalProps {
  title: string;
  children: ReactNode;
  onClose: () => void;
}

export function WorkspaceModal({ title, children, onClose }: WorkspaceModalProps) {
  return (
    <div
      className="workspace-modal-overlay"
      role="presentation"
      onClick={onClose}
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
    >
      <div
        className="workspace-modal panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workspace-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="workspace-modal-header">
          <h2 id="workspace-modal-title">{title}</h2>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Закрыть
          </button>
        </header>
        <div className="workspace-modal-body">{children}</div>
      </div>
    </div>
  );
}
