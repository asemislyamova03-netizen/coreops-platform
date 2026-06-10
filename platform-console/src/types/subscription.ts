export interface Plan {
  id: string;
  code: string;
  name: string;
  description: string | null;
  default_modules_json: string[];
  is_active: boolean;
  features?: string[];
  limits?: Array<{
    limit_code: string;
    limit_value: number;
    period: string;
  }>;
}

export interface Subscription {
  id: string;
  tenant_id: string;
  plan_id: string;
  plan_code: string;
  plan_name: string;
  status: string;
  created_at: string;
}
