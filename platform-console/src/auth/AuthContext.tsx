import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getMe, login as apiLogin } from "../api/auth";
import type { LoginRequest, MeResponse } from "../types/auth";
import { clearTokens, hasTokens, setTokens } from "./tokenStorage";

interface AuthContextValue {
  me: MeResponse | null;
  isLoading: boolean;
  isProviderOwner: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    const data = await getMe();
    setMe(data);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!hasTokens()) {
        setIsLoading(false);
        return;
      }
      try {
        const data = await getMe();
        if (!cancelled) setMe(data);
      } catch {
        clearTokens();
        if (!cancelled) setMe(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (payload: LoginRequest) => {
    const tokens = await apiLogin(payload);
    setTokens(tokens.access_token, tokens.refresh_token);
    const data = await getMe();
    setMe(data);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setMe(null);
  }, []);

  const isProviderOwner = me?.provider?.role === "provider_owner";

  const value = useMemo(
    () => ({
      me,
      isLoading,
      isProviderOwner,
      login,
      logout,
      refreshMe,
    }),
    [me, isLoading, isProviderOwner, login, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
