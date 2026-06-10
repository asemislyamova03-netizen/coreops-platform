import type { Plan, Subscription } from "../types/subscription";
import { apiFetch } from "./client";

export function listPlans(): Promise<Plan[]> {
  return apiFetch<Plan[]>("/plans");
}

export function getSubscription(tenantId: string): Promise<Subscription | null> {
  return apiFetch<Subscription | null>(`/tenants/${tenantId}/subscription`);
}

export function assignPlan(tenantId: string, planCode: string): Promise<Subscription> {
  return apiFetch<Subscription>(`/tenants/${tenantId}/subscription`, {
    method: "POST",
    body: JSON.stringify({ plan_code: planCode }),
  });
}
