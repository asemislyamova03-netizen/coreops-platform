import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Button } from "../ui/Button";

export function Header() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="header">
      <div className="header-user">
        <span className="header-name">{me?.user.full_name}</span>
        <span className="header-email">{me?.user.email}</span>
      </div>
      <Button variant="secondary" onClick={handleLogout}>
        Выйти
      </Button>
    </header>
  );
}
