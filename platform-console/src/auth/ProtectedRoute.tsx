import { Navigate, Outlet } from "react-router-dom";
import { Loading } from "../components/ui/Loading";
import { useAuth } from "./AuthContext";
import { hasTokens } from "./tokenStorage";

export function ProtectedRoute() {
  const { isLoading, isProviderOwner } = useAuth();

  if (isLoading) {
    return <Loading text="Загрузка..." />;
  }

  if (!hasTokens()) {
    return <Navigate to="/login" replace />;
  }

  if (!isProviderOwner) {
    return <Navigate to="/access-denied" replace />;
  }

  return <Outlet />;
}
