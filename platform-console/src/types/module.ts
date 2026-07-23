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

export interface ModuleDefinition {
  id: string;
  code: string;
  name: string;
  description: string | null;
  default_mode: ModuleMode;
  dependencies_json: {
    required?: string[];
    recommended?: string[];
  };
  is_active: boolean;
}

export interface TenantModuleRow extends TenantModule {
  name: string;
  description: string | null;
  required_dependencies: string[];
  active_dependents: string[];
}
