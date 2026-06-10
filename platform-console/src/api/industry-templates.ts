import type { ApplyTemplateResponse, IndustryTemplate } from "../types/template";
import { apiFetch } from "./client";

export function listTemplates(): Promise<IndustryTemplate[]> {
  return apiFetch<IndustryTemplate[]>("/industry-templates");
}

export function applyTemplate(
  tenantId: string,
  templateId: string,
): Promise<ApplyTemplateResponse> {
  return apiFetch<ApplyTemplateResponse>(
    `/tenants/${tenantId}/apply-template/${templateId}`,
    { method: "POST" },
  );
}
