import {
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "./AuthContext";
import type { TenantMembershipInfo } from "../types/auth";
import { formatMembershipRole } from "../i18n/ruUi";

export interface WorkspaceTenantInfo {
  tenantId: string;
  tenantName: string;
  tenantSlug: string;
  role: string | null;
}

interface TenantWorkspaceContextValue {
  tenantSlug: string;
  membership: TenantMembershipInfo | null;
  tenant: WorkspaceTenantInfo | null;
  isResolved: boolean;
}

const TenantWorkspaceContext = createContext<TenantWorkspaceContextValue | null>(null);

export function membershipRoleLabel(role: string | null): string {
  return formatMembershipRole(role);
}

export function TenantWorkspaceProvider({
  tenant,
  children,
}: {
  tenant: WorkspaceTenantInfo | null;
  children: ReactNode;
}) {
  const { tenantSlug = "" } = useParams();
  const { me } = useAuth();

  const membership = useMemo(
    () => me?.tenants.find((item) => item.tenant_slug === tenantSlug) ?? null,
    [me?.tenants, tenantSlug],
  );

  const value = useMemo(
    () => ({
      tenantSlug,
      membership,
      tenant,
      isResolved: tenant !== null || membership !== null,
    }),
    [tenantSlug, membership, tenant],
  );

  return (
    <TenantWorkspaceContext.Provider value={value}>
      {children}
    </TenantWorkspaceContext.Provider>
  );
}

export function useTenantWorkspace(): TenantWorkspaceContextValue {
  const ctx = useContext(TenantWorkspaceContext);
  if (!ctx) {
    throw new Error("useTenantWorkspace must be used within TenantWorkspaceProvider");
  }
  return ctx;
}
