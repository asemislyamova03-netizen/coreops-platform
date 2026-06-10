import { NavLink } from "react-router-dom";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-title">Flexity</span>
        <span className="brand-subtitle">Platform Console</span>
      </div>
      <nav className="sidebar-nav">
        <NavLink
          to="/tenants"
          className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
        >
          Tenants
        </NavLink>
      </nav>
    </aside>
  );
}
