import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { ui } from "../../i18n/ruUi";

export function WorkspaceAccessDeniedPage() {
  const { me, logout, isProviderOwner } = useAuth();
  const location = useLocation();
  const tenantSlug = (location.state as { tenantSlug?: string } | null)?.tenantSlug;

  return (
    <div className="center-page">
      <div className="center-card">
        <h1>Нет доступа к рабочему месту</h1>
        <Alert variant="error">
          {tenantSlug
            ? `У вас нет доступа к рабочему месту организации «${tenantSlug}».`
            : "У вас нет доступа к этому рабочему месту организации."}
          {me?.user.email ? ` Вы вошли как ${me.user.email}.` : ""}
        </Alert>
        <div className="actions-row">
          {isProviderOwner && (
            <Link to="/tenants">
              <Button variant="secondary">{ui.platformConsole}</Button>
            </Link>
          )}
          <Button
            variant="secondary"
            onClick={() => {
              logout();
            }}
          >
            Выйти
          </Button>
          <Link to="/login" className="link-button">
            Страница входа
          </Link>
        </div>
      </div>
    </div>
  );
}
