import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { loggedIn, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header style={{ borderBottom: "1px solid var(--stone)", background: "var(--white)" }}>
      <div
        className="app-shell"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "18px 24px",
        }}
      >
        <Link to="/" style={{ textDecoration: "none", color: "var(--ink)" }}>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                width: 10, height: 10, borderRadius: "50%",
                background: "var(--coral)", display: "inline-block",
              }}
            />
            LexiLoop
          </h3>
        </Link>
        {loggedIn && (
          <button
            className="btn btn-ghost"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Log out
          </button>
        )}
      </div>
    </header>
  );
}
