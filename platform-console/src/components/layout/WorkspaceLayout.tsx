import { Outlet } from "react-router-dom";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { WorkspaceSidebar } from "./WorkspaceSidebar";

export function WorkspaceLayout() {
  return (
    <div className="app-shell workspace-shell">
      <WorkspaceSidebar />
      <div className="app-main">
        <WorkspaceHeader />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
