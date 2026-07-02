import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Signup() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("parent");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.signup({ name, email, password, role });
      login(res.access_token);
      navigate("/");
    } catch (err) {
      setError(err.message || "Could not create account.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell" style={{ maxWidth: 420, paddingTop: 80 }}>
      <h1>Create your account</h1>
      <p style={{ color: "var(--ink-soft)" }}>Set up LexiLoop for your child.</p>

      <div className="card" style={{ marginTop: 24 }}>
        {error && <div className="error-text">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="name">Your name</label>
            <input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="role">You are a</label>
            <select id="role" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="parent">Parent</option>
              <option value="teacher">Teacher</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>
      </div>

      <p style={{ marginTop: 20, textAlign: "center", color: "var(--ink-soft)" }}>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
