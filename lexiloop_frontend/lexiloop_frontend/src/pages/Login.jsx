import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.login({ email, password });
      login(res.access_token);
      navigate("/");
    } catch (err) {
      setError(err.message || "Could not log in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell" style={{ maxWidth: 420, paddingTop: 80 }}>
      <h1>Welcome back</h1>
      <p style={{ color: "var(--ink-soft)" }}>Log in to continue your child's reading journey.</p>

      <div className="card" style={{ marginTop: 24 }}>
        {error && <div className="error-text">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Logging in..." : "Log in"}
          </button>
        </form>
      </div>

      <p style={{ marginTop: 20, textAlign: "center", color: "var(--ink-soft)" }}>
        New here? <Link to="/signup">Create an account</Link>
      </p>
    </div>
  );
}
