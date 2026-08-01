import { FormEvent, useMemo, useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { clientSignup } from "../api/clientOnboarding";
import { useAuth } from "../auth/AuthContext";
import { hasTokens, setTokens } from "../auth/tokenStorage";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Loading } from "../components/ui/Loading";
import { ui } from "../i18n/ruUi";
import {
  buildMarketingGuidePath,
  isValidTenantSlug,
  mapSignupError,
  slugifyTenantName,
} from "./clientSignupHelpers";

export function ClientSignupPage() {
  const { isLoading, me, refreshMe } = useAuth();
  const navigate = useNavigate();
  const idempotencyKeyRef = useRef<string>(
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `signup-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  );

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const slugOk = useMemo(
    () => !tenantSlug || isValidTenantSlug(tenantSlug),
    [tenantSlug],
  );

  if (isLoading) {
    return <Loading text="Проверка сессии..." />;
  }

  if (hasTokens() && me) {
    const slug = me.tenants[0]?.tenant_slug;
    if (slug) {
      return <Navigate to={buildMarketingGuidePath(slug)} replace />;
    }
    return <Navigate to="/tenants" replace />;
  }

  const handleTenantNameChange = (value: string) => {
    setTenantName(value);
    if (!slugTouched) {
      setTenantSlug(slugifyTenantName(value));
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setFieldError(null);

    if (!isValidTenantSlug(tenantSlug)) {
      setFieldError("Slug: только строчные латинские буквы, цифры и дефисы.");
      return;
    }
    if (password.length < 8) {
      setFieldError("Пароль должен быть не короче 8 символов.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await clientSignup(
        {
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          tenant_name: tenantName.trim(),
          tenant_slug: tenantSlug.trim(),
        },
        idempotencyKeyRef.current,
      );
      setTokens(result.access_token, result.refresh_token);
      await refreshMe();
      navigate(result.redirect_path || buildMarketingGuidePath(result.tenant.slug), {
        replace: true,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(mapSignupError(err.status, err.message));
      } else {
        setError("Не удалось зарегистрироваться. Проверьте сеть и попробуйте снова.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-page-shell">
        <section className="login-page-primary">
          <header className="login-page-brand">
            <p className="login-page-eyebrow">{ui.platformConsole}</p>
            <h1 className="login-page-title">Создать кабинет</h1>
            <p className="login-page-tagline">
              Регистрация владельца организации: аккаунт, workspace и Marketing Cabinet.
            </p>
          </header>

          <form className="login-card" onSubmit={handleSubmit}>
            <h2 className="login-form-heading">Регистрация клиента</h2>
            <p className="muted login-form-sub">
              Один шаг: пользователь + организация. Модули parties и marketing подключаются
              автоматически.
            </p>
            {error && <Alert variant="error">{error}</Alert>}
            {fieldError && <Alert variant="error">{fieldError}</Alert>}

            <Input
              label="Ваше имя"
              name="full_name"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoComplete="name"
            />
            <Input
              label="Email"
              name="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
            />
            <Input
              label="Пароль"
              name="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
            <Input
              label="Название организации"
              name="tenant_name"
              required
              value={tenantName}
              onChange={(e) => handleTenantNameChange(e.target.value)}
            />
            <Input
              label="Адрес организации (slug)"
              name="tenant_slug"
              required
              value={tenantSlug}
              onChange={(e) => {
                setSlugTouched(true);
                setTenantSlug(e.target.value);
              }}
              pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
              title="Только строчные латинские буквы, цифры и дефисы"
            />
            {!slugOk && (
              <p className="muted form-hint">
                Slug: только `a-z`, `0-9` и дефисы (например `my-company`).
              </p>
            )}

            <Button type="submit" disabled={submitting || !slugOk} className="full-width">
              {submitting ? "Создание кабинета..." : "Создать кабинет"}
            </Button>

            <p className="muted login-form-sub" style={{ marginTop: "1rem" }}>
              Уже есть аккаунт? <Link to="/login">Войти</Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}
