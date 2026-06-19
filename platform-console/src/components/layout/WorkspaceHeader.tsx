import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import {
  membershipRoleLabel,
  useTenantWorkspace,
} from "../../auth/TenantWorkspaceContext";
import { Button } from "../ui/Button";
import { Select } from "../ui/Select";
import { ui } from "../../i18n/ruUi";

export function WorkspaceHeader() {
  const { me, logout, isProviderOwner } = useAuth();
  const { tenant, membership } = useTenantWorkspace();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const tenantOptions = (me?.tenants ?? []).map((item) => ({
    value: item.tenant_slug,
    label: `${item.tenant_name} (${item.tenant_slug})`,
  }));

  return (
    <header className="header workspace-header">
      <div className="workspace-header-main">
        <div>
          <h2 className="workspace-tenant-title">{tenant?.tenantName ?? ui.organization}</h2>
          <p className="muted workspace-tenant-meta">
            <code>{tenant?.tenantSlug}</code>
            {" · "}
            роль: {membershipRoleLabel(membership?.role ?? tenant?.role ?? null)}
          </p>
        </div>
        {tenantOptions.length > 1 && tenant && (
          <Select
            label={ui.organization}
            name="workspace_tenant_switch"
            value={tenant.tenantSlug}
            onChange={(event) => {
              const slug = event.target.value;
              const currentPath = window.location.pathname.split("/").pop() ?? "dashboard";
              navigate(`/workspace/${slug}/${currentPath}`);
            }}
            options={tenantOptions}
          />
        )}
      </div>
      <div className="workspace-header-actions">
        {isProviderOwner && (
          <Link to="/tenants">
            <Button variant="secondary">{ui.platformConsole}</Button>
          </Link>
        )}
        <div className="header-user">
          <span className="header-name">{me?.user.full_name}</span>
          <span className="header-email">{me?.user.email}</span>
        </div>
        <Button variant="secondary" onClick={handleLogout}>
          Выйти
        </Button>
      </div>
    </header>
  );
}
