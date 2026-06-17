import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { hasTokens } from "../auth/tokenStorage";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Loading } from "../components/ui/Loading";
import { resolveHomePath } from "../routes/resolveHomePath";

export function LoginPage() {
  const { login, isLoading, isProviderOwner, me } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isLoading) {
    return <Loading text="Проверка сессии..." />;
  }

  if (hasTokens() && me) {
    const tenantSlugs = me.tenants.map((item) => item.tenant_slug);
    return <Navigate to={resolveHomePath(isProviderOwner, tenantSlugs)} replace />;
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const session = await login({ email, password });
      const tenantSlugs = session.tenants.map((item) => item.tenant_slug);
      const isProvider = session.provider?.role === "provider_owner";
      navigate(resolveHomePath(isProvider, tenantSlugs));
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Не удалось войти. Проверьте backend и сеть.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Flexity Platform Console</h1>
        <p className="muted">Вход для provider_owner и tenant users</p>
        {error && <Alert variant="error">{error}</Alert>}
        <Input
          label="Email"
          name="email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          label="Пароль"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" disabled={submitting} className="full-width">
          {submitting ? "Вход..." : "Войти"}
        </Button>
      </form>
    </div>
  );
}
