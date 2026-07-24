import type { ModuleDefinition, TenantModule } from "../types/module";
import { apiFetch } from "./client";

export function listModuleRegistry(): Promise<ModuleDefinition[]> {
  return apiFetch<ModuleDefinition[]>("/modules/registry");
}

export function listTenantModules(tenantId: string): Promise<TenantModule[]> {
  return apiFetch<TenantModule[]>(`/tenants/${tenantId}/modules`);
}

export function enableModule(tenantId: string, moduleCode: string): Promise<TenantModule> {
  return apiFetch<TenantModule>(
    `/tenants/${tenantId}/modules/${moduleCode}/enable`,
    { method: "POST" },
  );
}

export function disableModule(tenantId: string, moduleCode: string): Promise<TenantModule> {
  return apiFetch<TenantModule>(
    `/tenants/${tenantId}/modules/${moduleCode}/disable`,
    { method: "POST" },
  );
}
