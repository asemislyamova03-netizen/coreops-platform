import { apiFetch } from "./client";

export function getTenantLabels(tenantId: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/tenants/${tenantId}/labels`);
}
