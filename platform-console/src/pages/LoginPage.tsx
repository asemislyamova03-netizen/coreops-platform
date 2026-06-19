import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { hasTokens } from "../auth/tokenStorage";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Loading } from "../components/ui/Loading";
import { LOGIN_NEWS_CARDS, LOGIN_RESOURCE_LINKS } from "../content/loginNews";
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
      <div className="login-page-shell">
        <section className="login-page-primary">
          <header className="login-page-brand">
            <p className="login-page-eyebrow">Platform Console</p>
            <h1 className="login-page-title">Flexity</h1>
            <p className="login-page-tagline">
              Единая AI-ready CRM/ERP-платформа для владельцев и менеджеров сервисного и
              операционного бизнеса.
            </p>
            <p className="login-page-directions muted">
              Клиника, консалтинг, детский сад и Trailers — направления внедрения Flexity, а не
              отдельные продукты.
            </p>
          </header>

          <form className="login-card" onSubmit={handleSubmit}>
            <h2 className="login-form-heading">Вход в систему</h2>
            <p className="muted login-form-sub">Для provider_owner и пользователей tenant</p>
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
        </section>

        <aside className="login-page-aside" aria-label="Материалы Flexity">
          <h2 className="login-aside-heading">Материалы и обновления</h2>
          <ul className="login-news-list">
            {LOGIN_NEWS_CARDS.map((card) => (
              <li key={card.id} className="login-news-card">
                <h3>{card.title}</h3>
                <p>{card.body}</p>
                {card.href && card.hrefLabel ? (
                  <a href={card.href} target="_blank" rel="noopener noreferrer">
                    {card.hrefLabel}
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
          <nav className="login-resource-links" aria-label="Полезные ссылки">
            {LOGIN_RESOURCE_LINKS.map((link) => (
              <a key={link.href} href={link.href} target="_blank" rel="noopener noreferrer">
                {link.label}
              </a>
            ))}
          </nav>
        </aside>
      </div>
    </div>
  );
}
