export type TenantStatus = "active" | "trial" | "suspended" | "archived";

export interface Tenant {
  id: string;
  provider_company_id: string;
  name: string;
  slug: string;
  industry_template_id: string | null;
  status: TenantStatus;
  created_at: string;
  updated_at: string;
}

export interface TenantCreate {
  name: string;
  slug: string;
  status?: TenantStatus;
  plan_code?: string;
  industry_template_code?: string;
}

export interface TenantUpdate {
  name?: string;
  status?: TenantStatus;
}
