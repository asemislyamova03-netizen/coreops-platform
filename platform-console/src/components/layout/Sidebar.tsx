import { NavLink } from "react-router-dom";
import { ui } from "../../i18n/ruUi";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-title">Flexity</span>
        <span className="brand-subtitle">{ui.platformConsole}</span>
      </div>
      <nav className="sidebar-nav">
        <NavLink
          to="/tenants"
          className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
        >
          {ui.tenants}
        </NavLink>
      </nav>
    </aside>
  );
}
