import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { setWorkspaceTenantId } from "../../api/workspaceTenant";
import { useTenantWorkspace } from "../../auth/TenantWorkspaceContext";
import { WorkspaceLabelsProvider } from "../../workspace/WorkspaceLabelsContext";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { WorkspaceSidebar } from "./WorkspaceSidebar";

export function WorkspaceLayout() {
  const { tenant } = useTenantWorkspace();

  useEffect(() => {
    setWorkspaceTenantId(tenant?.tenantId ?? null);
    return () => setWorkspaceTenantId(null);
  }, [tenant?.tenantId]);

  return (
    <WorkspaceLabelsProvider tenantId={tenant?.tenantId ?? null}>
      <div className="app-shell workspace-shell">
        <WorkspaceSidebar />
        <div className="app-main">
          <WorkspaceHeader />
          <main className="app-content">
            <Outlet />
          </main>
        </div>
      </div>
    </WorkspaceLabelsProvider>
  );
}
