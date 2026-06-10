import type { Tenant, TenantCreate, TenantUpdate } from "../types/tenant";
import { apiFetch } from "./client";

export function listTenants(): Promise<Tenant[]> {
  return apiFetch<Tenant[]>("/tenants");
}

export function getTenant(tenantId: string): Promise<Tenant> {
  return apiFetch<Tenant>(`/tenants/${tenantId}`);
}

export function createTenant(payload: TenantCreate): Promise<Tenant> {
  return apiFetch<Tenant>("/tenants", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchTenant(tenantId: string, payload: TenantUpdate): Promise<Tenant> {
  return apiFetch<Tenant>(`/tenants/${tenantId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
