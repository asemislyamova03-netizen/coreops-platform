import { NavLink, useParams } from "react-router-dom";
import { ui } from "../../i18n/ruUi";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

const NAV_ITEMS = [
  { segment: "dashboard", label: ui.dashboard },
  { segment: "crm", label: ui.crmPipeline },
  { segment: "clients", label: ui.clients },
  { segment: "documents", label: ui.documents },
  { segment: "finance", label: ui.finance },
  { segment: "reports", label: ui.reports },
] as const;

export function WorkspaceSidebar() {
  const { tenantSlug = "" } = useParams();
  const { crmSectionTitle, clientsSectionTitle } = useWorkspaceLabels();

  const navHints: Record<string, string | undefined> = {
    crm: crmSectionTitle,
    clients: clientsSectionTitle,
  };

  return (
    <aside className="sidebar workspace-sidebar">
      <div className="sidebar-brand">
        <span className="brand-title">Flexity</span>
        <span className="brand-subtitle">{ui.managerWorkspace}</span>
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.segment}
            to={`/workspace/${tenantSlug}/${item.segment}`}
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            <span className="workspace-nav-label">{item.label}</span>
            {navHints[item.segment] && (
              <span className="workspace-nav-hint">{navHints[item.segment]}</span>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
