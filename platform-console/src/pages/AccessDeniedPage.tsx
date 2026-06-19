import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { formatMembershipRole, ui } from "../i18n/ruUi";

export function AccessDeniedPage() {
  const { me, logout } = useAuth();

  return (
    <div className="center-page">
      <div className="center-card">
        <h1>Доступ запрещён</h1>
        <Alert variant="error">
          {ui.platformConsole} доступна только пользователям с ролью{" "}
          <strong>{formatMembershipRole("provider_owner")}</strong>.
          {me?.user.email ? ` Вы вошли как ${me.user.email}.` : ""}
        </Alert>
        <div className="actions-row">
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
