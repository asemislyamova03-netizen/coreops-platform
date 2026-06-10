export type ModuleStatus = "enabled" | "disabled" | "trial" | "suspended";
export type ModuleMode = "internal" | "external" | "hybrid" | "disabled";

export interface TenantModule {
  id: string;
  tenant_id: string;
  module_code: string;
  status: ModuleStatus;
  mode: ModuleMode;
  external_provider_code: string | null;
  settings_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
