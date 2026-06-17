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

export interface TenantMembership {
  membership_id: string;
  user_id: string;
  email: string;
  full_name: string;
  user_is_active: boolean;
  role: string;
  membership_is_active: boolean;
  created_at: string;
}

export type TenantMembershipRole = "tenant_owner" | "tenant_admin" | "member";

export interface TenantMembershipCreatePayload {
  user_id?: string;
  user_email?: string;
  role: TenantMembershipRole;
}
