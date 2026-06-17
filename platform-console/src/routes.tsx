import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { TenantWorkspaceGuard } from "./auth/TenantWorkspaceGuard";
import { AppLayout } from "./components/layout/AppLayout";
import { WorkspaceLayout } from "./components/layout/WorkspaceLayout";
import { AccessDeniedPage } from "./pages/AccessDeniedPage";
import { LoginPage } from "./pages/LoginPage";
import { TenantCreatePage } from "./pages/TenantCreatePage";
import { TenantDetailPage } from "./pages/TenantDetailPage";
import { TenantsListPage } from "./pages/TenantsListPage";
import { WorkspaceAccessDeniedPage } from "./pages/workspace/WorkspaceAccessDeniedPage";
import { WorkspacePlaceholderPage } from "./pages/workspace/WorkspacePlaceholderPage";
import { RootRedirect } from "./routes/RootRedirect";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />
      <Route path="/workspace-access-denied" element={<WorkspaceAccessDeniedPage />} />
      <Route path="/workspace/:tenantSlug" element={<TenantWorkspaceGuard />}>
        <Route element={<WorkspaceLayout />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route
            path="dashboard"
            element={
              <WorkspacePlaceholderPage
                title="Dashboard"
                description="Сводка по детскому саду и ключевые показатели."
                plannedStage="W2"
              />
            }
          />
          <Route
            path="children"
            element={
              <WorkspacePlaceholderPage
                title="Children"
                description="Список воспитанников и карточки детей."
                plannedStage="W2"
              />
            }
          />
          <Route
            path="parents"
            element={
              <WorkspacePlaceholderPage
                title="Parents"
                description="Родители и законные представители."
                plannedStage="W2"
              />
            }
          />
          <Route
            path="services"
            element={
              <WorkspacePlaceholderPage
                title="Services"
                description="Услуги, тарифы и каталог kindergarten_basic."
                plannedStage="W2"
              />
            }
          />
          <Route
            path="invoices"
            element={
              <WorkspacePlaceholderPage
                title="Invoices"
                description="Счета, оплаты и финансовые операции."
                plannedStage="W3"
              />
            }
          />
          <Route
            path="documents"
            element={
              <WorkspacePlaceholderPage
                title="Documents"
                description="Договоры, шаблоны и документооборот."
                plannedStage="W3"
              />
            }
          />
        </Route>
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/tenants" replace />} />
          <Route path="/tenants" element={<TenantsListPage />} />
          <Route path="/tenants/new" element={<TenantCreatePage />} />
          <Route path="/tenants/:tenantId" element={<TenantDetailPage />} />
        </Route>
      </Route>
      <Route path="*" element={<RootRedirect />} />
    </Routes>
  );
}
