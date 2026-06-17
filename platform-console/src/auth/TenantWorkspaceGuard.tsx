import { useEffect, useState } from "react";
import { Navigate, Outlet, useParams } from "react-router-dom";
import { listTenants } from "../api/tenants";
import { Loading } from "../components/ui/Loading";
import { useAuth } from "./AuthContext";
import {
  TenantWorkspaceProvider,
  type WorkspaceTenantInfo,
} from "./TenantWorkspaceContext";
import { hasTokens } from "./tokenStorage";

export function TenantWorkspaceGuard() {
  const { tenantSlug = "" } = useParams();
  const { me, isLoading, isProviderOwner } = useAuth();
  const [tenant, setTenant] = useState<WorkspaceTenantInfo | null>(null);
  const [resolveState, setResolveState] = useState<"loading" | "ready" | "denied">(
    "loading",
  );

  useEffect(() => {
    if (isLoading || !me) {
      return;
    }

    const membership = me.tenants.find((item) => item.tenant_slug === tenantSlug);
    if (membership) {
      setTenant({
        tenantId: membership.tenant_id,
        tenantName: membership.tenant_name,
        tenantSlug: membership.tenant_slug,
        role: membership.role,
      });
      setResolveState("ready");
      return;
    }

    if (!isProviderOwner) {
      setResolveState("denied");
      return;
    }

    let cancelled = false;

    async function resolveProviderTenant() {
      try {
        const tenants = await listTenants();
        const match = tenants.find((item) => item.slug === tenantSlug);
        if (cancelled) return;

        if (!match) {
          setResolveState("denied");
          return;
        }

        setTenant({
          tenantId: match.id,
          tenantName: match.name,
          tenantSlug: match.slug,
          role: null,
        });
        setResolveState("ready");
      } catch {
        if (!cancelled) setResolveState("denied");
      }
    }

    void resolveProviderTenant();

    return () => {
      cancelled = true;
    };
  }, [isLoading, me, tenantSlug, isProviderOwner]);

  if (isLoading || (me && resolveState === "loading")) {
    return <Loading text="Загрузка workspace..." />;
  }

  if (!hasTokens()) {
    return <Navigate to="/login" replace />;
  }

  if (!me || resolveState === "denied" || !tenant) {
    return <Navigate to="/workspace-access-denied" replace state={{ tenantSlug }} />;
  }

  return (
    <TenantWorkspaceProvider tenant={tenant}>
      <Outlet />
    </TenantWorkspaceProvider>
  );
}
