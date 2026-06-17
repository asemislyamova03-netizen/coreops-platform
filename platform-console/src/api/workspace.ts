import { apiFetch, type ApiFetchOptions } from "./client";

export function workspaceApiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  return apiFetch<T>(path, { ...options, workspaceTenant: true });
}
