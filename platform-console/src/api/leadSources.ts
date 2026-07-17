import type { LeadSource } from "../types/leadSources";
import { apiFetch } from "./client";

export function getTenantLeadSources(tenantId: string): Promise<LeadSource[]> {
  return apiFetch<LeadSource[]>(`/tenants/${tenantId}/lead-sources`);
}
