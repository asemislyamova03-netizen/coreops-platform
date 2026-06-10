import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { AccessDeniedPage } from "./pages/AccessDeniedPage";
import { LoginPage } from "./pages/LoginPage";
import { TenantCreatePage } from "./pages/TenantCreatePage";
import { TenantDetailPage } from "./pages/TenantDetailPage";
import { TenantsListPage } from "./pages/TenantsListPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/tenants" replace />} />
          <Route path="/tenants" element={<TenantsListPage />} />
          <Route path="/tenants/new" element={<TenantCreatePage />} />
          <Route path="/tenants/:tenantId" element={<TenantDetailPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/tenants" replace />} />
    </Routes>
  );
}
