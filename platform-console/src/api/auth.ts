import type { LoginRequest, MeResponse, TokenPair } from "../types/auth";
import { apiFetch } from "./client";

export function login(payload: LoginRequest): Promise<TokenPair> {
  return apiFetch<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
  });
}

export function getMe(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/auth/me");
}
