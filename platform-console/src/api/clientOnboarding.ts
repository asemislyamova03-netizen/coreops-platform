import type { TokenPair } from "../types/auth";
import { apiFetch } from "./client";

export interface ClientSignupRequest {
  full_name: string;
  email: string;
  password: string;
  tenant_name: string;
  tenant_slug: string;
}

export interface ClientSignupResponse extends TokenPair {
  user: {
    id: string;
    email: string;
    full_name: string;
  };
  tenant: {
    id: string;
    name: string;
    slug: string;
    default_branch_id: string;
    role: "tenant_owner";
  };
  modules_enabled: string[];
  redirect_path: string;
}

export function clientSignup(
  payload: ClientSignupRequest,
  idempotencyKey: string,
): Promise<ClientSignupResponse> {
  return apiFetch<ClientSignupResponse>("/client-onboarding/signup", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
    headers: {
      "Idempotency-Key": idempotencyKey,
    },
  });
}
