import { useState } from "react";
import { api } from "../api";

export default function CaptureTab({ childId }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleFileChange(e) {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setReport(null);
  }

  async function handleAnalyze() {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.detectHandwriting(childId, file);
      setReport(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <p style={{ color: "var(--ink-soft)" }}>
        Take a photo of a short handwriting sample — a few practiced words or
        letters work best — and LexiLoop will look for common reversal
        patterns.
      </p>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="field">
          <label htmlFor="handwriting-file">Handwriting photo</label>
          <input id="handwriting-file" type="file" accept="image/*" capture="environment" onChange={handleFileChange} />
        </div>

        {preview && (
          <img
            src={preview}
            alt="Selected handwriting sample"
            style={{ maxWidth: "100%", borderRadius: 12, border: "1px solid var(--stone)", marginBottom: 16 }}
          />
        )}

        {error && <div className="error-text">{error}</div>}

        <button className="btn btn-primary" onClick={handleAnalyze} disabled={!file || loading}>
          {loading ? "Analyzing..." : "Analyze handwriting"}
        </button>
      </div>

      {report && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ marginBottom: 0 }}>Session result</h3>
            <span
              className="badge"
              style={{
                background:
                  report.risk_label === "High" ? "var(--coral-pale)" :
                  report.risk_label === "Moderate" ? "var(--slate-pale)" : "var(--teal-pale)",
                color:
                  report.risk_label === "High" ? "#A6552A" :
                  report.risk_label === "Moderate" ? "var(--slate)" : "var(--teal-deep)",
              }}
            >
              {report.risk_label} practice priority
            </span>
          </div>

          <p style={{ marginTop: 12 }}>
            Looked at {report.total_chars} letters — found {report.reversal_count} practice
            spots ({report.reversal_percent}%). Nothing here is a mistake to fix, just
            somewhere to focus next.
          </p>

          {report.reversals_found.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
              {report.reversals_found.map((r, i) => (
                <span key={i} className="badge badge-coral">
                  {r.letter} ↔ {r.confused_with}
                </span>
              ))}
            </div>
          )}

          {report.annotated_image_b64 && (
            <img
              src={`data:image/png;base64,${report.annotated_image_b64}`}
              alt="Annotated handwriting sample showing detected letters"
              style={{ maxWidth: "100%", borderRadius: 12, marginTop: 16, border: "1px solid var(--stone)" }}
            />
          )}
        </div>
      )}
    </div>
  );
}
