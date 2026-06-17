import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { hasTokens } from "../auth/tokenStorage";
import { Loading } from "../components/ui/Loading";
import { resolveHomePath } from "./resolveHomePath";

export function RootRedirect() {
  const { isLoading, isProviderOwner, me } = useAuth();

  if (isLoading) {
    return <Loading text="Загрузка..." />;
  }

  if (!hasTokens()) {
    return <Navigate to="/login" replace />;
  }

  const tenantSlugs = me?.tenants.map((item) => item.tenant_slug) ?? [];
  return <Navigate to={resolveHomePath(isProviderOwner, tenantSlugs)} replace />;
}
