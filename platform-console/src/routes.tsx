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
import { ClientDetailPage } from "./pages/workspace/ClientDetailPage";
import { ClientsPage } from "./pages/workspace/ClientsPage";
import { CrmPage } from "./pages/workspace/CrmPage";
import { DashboardPage } from "./pages/workspace/DashboardPage";
import { DocumentsPage } from "./pages/workspace/DocumentsPage";
import { FinancePage } from "./pages/workspace/FinancePage";
import { MarketingDashboardPage } from "./pages/workspace/marketing/MarketingDashboardPage";
import { MarketingPackDetailPage } from "./pages/workspace/marketing/MarketingPackDetailPage";
import { MarketingPacksPage } from "./pages/workspace/marketing/MarketingPacksPage";
import { MarketingTopicsPage } from "./pages/workspace/marketing/MarketingTopicsPage";
import { ReportsPage } from "./pages/workspace/ReportsPage";
import { WorkspaceAccessDeniedPage } from "./pages/workspace/WorkspaceAccessDeniedPage";
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
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="crm" element={<CrmPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="clients/:partyId" element={<ClientDetailPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="finance" element={<FinancePage />} />
          <Route path="marketing" element={<MarketingDashboardPage />} />
          <Route path="marketing/topics" element={<MarketingTopicsPage />} />
          <Route path="marketing/packs" element={<MarketingPacksPage />} />
          <Route path="marketing/packs/:packId" element={<MarketingPackDetailPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="children" element={<Navigate to="../clients" replace />} />
          <Route path="parents" element={<Navigate to="../clients" replace />} />
          <Route path="services" element={<Navigate to="../dashboard" replace />} />
          <Route path="invoices" element={<Navigate to="../finance" replace />} />
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
