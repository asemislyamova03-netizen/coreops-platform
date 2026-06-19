import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Loading } from "../components/ui/Loading";
import { useAuth } from "./AuthContext";
import { hasTokens } from "./tokenStorage";

export function ProtectedRoute() {
  const { isLoading, isProviderOwner } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <Loading text="Загрузка..." />;
  }

  if (!hasTokens()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!isProviderOwner) {
    return <Navigate to="/access-denied" replace />;
  }

  return <Outlet />;
}
