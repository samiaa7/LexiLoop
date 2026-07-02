import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import ProgressPath from "../components/ProgressPath";
import CaptureTab from "../components/CaptureTab";
import ExercisesTab from "../components/ExercisesTab";
import ChatTab from "../components/ChatTab";

const TABS = [
  { key: "capture", label: "Handwriting" },
  { key: "exercises", label: "Reading" },
  { key: "chat", label: "Tutor chat" },
];

export default function ChildDetail() {
  const { id } = useParams();
  const [child, setChild] = useState(null);
  const [tab, setTab] = useState("capture");
  const [error, setError] = useState("");

  useEffect(() => {
    api.getChild(id).then(setChild).catch((err) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <div className="app-shell" style={{ paddingTop: 40 }}>
        <div className="error-text">{error}</div>
        <Link to="/">Back to dashboard</Link>
      </div>
    );
  }

  if (!child) return <div className="app-shell" style={{ paddingTop: 40 }}>Loading...</div>;

  return (
    <div className="app-shell" style={{ paddingTop: 40 }}>
      <Link to="/" style={{ color: "var(--ink-soft)", fontSize: "0.9rem" }}>&larr; All children</Link>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginTop: 12 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>{child.name}'s reading journey</h1>
          <span className="badge badge-teal">{child.reading_level}</span>
          <span className="badge badge-slate" style={{ marginLeft: 8 }}>Age {child.age}</span>
        </div>
      </div>

      <ProgressPath totalSessions={child.total_sessions} />

      {child.mood_trend?.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          <span style={{ color: "var(--ink-soft)", fontSize: "0.85rem" }}>Recent mood:</span>
          {child.mood_trend.slice(-5).map((m, i) => (
            <span key={i} className="badge badge-slate">{m}</span>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 28, borderBottom: "1px solid var(--stone)" }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: "10px 4px", marginRight: 20, fontWeight: 500,
              color: tab === t.key ? "var(--teal-deep)" : "var(--ink-soft)",
              borderBottom: tab === t.key ? "2px solid var(--teal)" : "2px solid transparent",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ marginTop: 24 }}>
        {tab === "capture" && <CaptureTab childId={id} />}
        {tab === "exercises" && <ExercisesTab childId={id} />}
        {tab === "chat" && <ChatTab childId={id} childName={child.name} />}
      </div>
    </div>
  );
}
