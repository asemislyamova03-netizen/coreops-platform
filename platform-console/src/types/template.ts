export interface IndustryTemplate {
  id: string;
  code: string;
  name: string;
  description: string | null;
  default_modules: string[];
  is_active: boolean;
}

export interface ApplyTemplateResponse {
  tenant_id: string;
  template_id: string;
  template_code: string;
  modules_enabled: string[];
  pipelines_created: string[];
  custom_fields_created: number;
  labels_applied: boolean;
}
