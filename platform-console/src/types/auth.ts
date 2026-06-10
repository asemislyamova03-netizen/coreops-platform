export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface ProviderStaffInfo {
  provider_company_id: string;
  provider_company_name: string;
  role: string;
}

export interface TenantMembershipInfo {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: string;
}

export interface MeResponse {
  user: UserResponse;
  provider: ProviderStaffInfo | null;
  tenants: TenantMembershipInfo[];
}

export interface LoginRequest {
  email: string;
  password: string;
}
