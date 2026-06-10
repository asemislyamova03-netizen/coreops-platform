import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "../auth/tokenStorage";
import type { TokenPair } from "../types/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "object" && item && "msg" in item) {
          return String((item as { msg: string }).msg);
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: string }).message);
  }
  return "Request failed";
}

async function parseError(response: Response): Promise<never> {
  let message = response.statusText;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (body.detail !== undefined) {
      message = formatDetail(body.detail);
    }
  } catch {
    // ignore JSON parse errors
  }
  throw new ApiError(message, response.status);
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    return null;
  }

  const tokens = (await response.json()) as TokenPair;
  setTokens(tokens.access_token, tokens.refresh_token);
  return tokens.access_token;
}

export interface ApiFetchOptions extends RequestInit {
  skipAuth?: boolean;
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { skipAuth = false, headers, ...rest } = options;
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  const buildHeaders = (token: string | null): HeadersInit => ({
    "Content-Type": "application/json",
    ...(token && !skipAuth ? { Authorization: `Bearer ${token}` } : {}),
    ...headers,
  });

  let token = skipAuth ? null : getAccessToken();
  let response = await fetch(url, {
    ...rest,
    headers: buildHeaders(token),
  });

  if (response.status === 401 && !skipAuth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      token = newToken;
      response = await fetch(url, {
        ...rest,
        headers: buildHeaders(token),
      });
    }
  }

  if (!response.ok) {
    await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
