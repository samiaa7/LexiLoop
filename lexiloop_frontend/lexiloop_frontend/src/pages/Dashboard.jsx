import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import ProgressPath from "../components/ProgressPath";

export default function Dashboard() {
  const [children, setChildren] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    loadChildren();
  }, []);

  async function loadChildren() {
    setLoading(true);
    try {
      const data = await api.listChildren();
      setChildren(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell" style={{ paddingTop: 40 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>Reading journeys</h1>
          <p style={{ color: "var(--ink-soft)" }}>Every child's path, one stepping stone at a time.</p>
        </div>
        <button className="btn btn-coral" onClick={() => setShowAdd(true)}>+ Add child</button>
      </div>

      {error && <div className="error-text">{error}</div>}

      {showAdd && (
        <AddChildForm
          onClose={() => setShowAdd(false)}
          onCreated={() => {
            setShowAdd(false);
            loadChildren();
          }}
        />
      )}

      {loading ? (
        <p>Loading...</p>
      ) : children.length === 0 ? (
        <div className="card" style={{ marginTop: 24, textAlign: "center" }}>
          <p style={{ marginBottom: 0 }}>No profiles yet. Add a child to start their reading journey.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: 16, marginTop: 24 }}>
          {children.map((child) => (
            <Link key={child.id} to={`/children/${child.id}`} style={{ textDecoration: "none", color: "inherit" }}>
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h3 style={{ marginBottom: 4 }}>{child.name}</h3>
                    <span className="badge badge-teal">{child.reading_level}</span>
                    <span className="badge badge-slate" style={{ marginLeft: 8 }}>Age {child.age}</span>
                  </div>
                  <span style={{ color: "var(--ink-soft)", fontSize: "0.9rem" }}>
                    {child.total_sessions} session{child.total_sessions === 1 ? "" : "s"}
                  </span>
                </div>
                <ProgressPath totalSessions={child.total_sessions} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function AddChildForm({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [age, setAge] = useState(7);
  const [readingLevel, setReadingLevel] = useState("beginner");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.createChild({ name, age: Number(age), reading_level: readingLevel });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ marginTop: 20 }}>
      <h3>New reading profile</h3>
      {error && <div className="error-text">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="child-name">Child's name</label>
          <input id="child-name" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="child-age">Age</label>
          <input id="child-age" type="number" min={4} max={16} required value={age} onChange={(e) => setAge(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="child-level">Starting reading level</label>
          <select id="child-level" value={readingLevel} onChange={(e) => setReadingLevel(e.target.value)}>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Creating..." : "Create profile"}
          </button>
          <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
