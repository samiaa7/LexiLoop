import { useState } from "react";
import { api } from "../api";

export default function ExercisesTab({ childId }) {
  const [exercise, setExercise] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    setLoading(true);
    setError("");
    try {
      const res = await api.generateExercise(childId);
      setExercise(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <p style={{ color: "var(--ink-soft)" }}>
        Generate a short story matched to this child's reading level, with a
        few questions to check understanding afterward.
      </p>

      <button className="btn btn-primary" onClick={handleGenerate} disabled={loading}>
        {loading ? "Finding a story..." : exercise ? "Get another story" : "Generate exercise"}
      </button>

      {error && <div className="error-text" style={{ marginTop: 16 }}>{error}</div>}

      {exercise && (
        <div className="card" style={{ marginTop: 16 }}>
          <span className="badge badge-teal">{exercise.target_level}</span>
          <h3 style={{ marginTop: 12 }}>{exercise.passage_title}</h3>
          <p style={{ whiteSpace: "pre-line" }}>{exercise.passage_text}</p>

          <h3 style={{ marginTop: 24 }}>Let's talk about it</h3>
          <ol style={{ paddingLeft: 20 }}>
            {exercise.comprehension_questions.map((q, i) => (
              <li key={i} style={{ marginBottom: 8 }}>{q}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
