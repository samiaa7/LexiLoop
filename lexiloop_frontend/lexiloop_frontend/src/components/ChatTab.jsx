import { useState, useRef, useEffect } from "react";
import { api } from "../api";

export default function ChatTab({ childId, childName }) {
  const [messages, setMessages] = useState([
    { role: "assistant", text: `Hi! I'm here to read and practice with ${childName || "you"}. What would you like to do today?` },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.chat(childId, text);
      setMessages((prev) => [...prev, { role: "assistant", text: res.reply }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", text: `Something went wrong: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", height: 480 }}>
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", paddingRight: 4 }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
              marginBottom: 12,
            }}
          >
            <div
              style={{
                maxWidth: "80%",
                padding: "10px 16px",
                borderRadius: 16,
                background: m.role === "user" ? "var(--teal)" : "var(--sand-deep)",
                color: m.role === "user" ? "var(--white)" : "var(--ink)",
              }}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ color: "var(--ink-soft)", fontSize: "0.9rem" }}>Thinking...</div>
        )}
      </div>

      <form onSubmit={handleSend} style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          style={{
            flex: 1, border: "1px solid var(--stone)", borderRadius: 999,
            padding: "12px 18px", background: "var(--white)",
          }}
        />
        <button className="btn btn-primary" type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
