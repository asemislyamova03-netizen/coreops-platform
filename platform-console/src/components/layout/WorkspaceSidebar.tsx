import { NavLink, useParams } from "react-router-dom";
import { useWorkspaceLabels } from "../../workspace/WorkspaceLabelsContext";

const NAV_ITEMS = [
  { segment: "dashboard", label: "Dashboard" },
  { segment: "crm", label: "CRM" },
  { segment: "clients", label: "Clients" },
  { segment: "documents", label: "Documents" },
  { segment: "finance", label: "Finance" },
  { segment: "reports", label: "Reports" },
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
        <span className="brand-subtitle">Manager Workspace</span>
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
