import { NavLink, useParams } from "react-router-dom";

const NAV_ITEMS = [
  { segment: "dashboard", label: "Dashboard" },
  { segment: "children", label: "Children" },
  { segment: "parents", label: "Parents" },
  { segment: "services", label: "Services" },
  { segment: "invoices", label: "Invoices" },
  { segment: "documents", label: "Documents" },
] as const;

export function WorkspaceSidebar() {
  const { tenantSlug = "" } = useParams();

  return (
    <aside className="sidebar workspace-sidebar">
      <div className="sidebar-brand">
        <span className="brand-title">Flexity</span>
        <span className="brand-subtitle">Tenant Workspace</span>
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.segment}
            to={`/workspace/${tenantSlug}/${item.segment}`}
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
