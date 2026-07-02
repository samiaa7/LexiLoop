/**
 * ProgressPath — the app's signature visual. Progress is shown as a
 * winding dotted path of stepping stones rather than a bar or chart,
 * reframing "sessions completed" as a journey instead of a score.
 * Each stone lights up (filled) once that session has happened.
 */
export default function ProgressPath({ totalSessions = 0, maxStones = 10 }) {
  const stones = Array.from({ length: maxStones }, (_, i) => i < totalSessions);

  // Simple alternating zig-zag y-offsets so the path visually "winds"
  const yFor = (i) => (i % 2 === 0 ? 0 : 22);

  const width = maxStones * 48 + 24;

  return (
    <div style={{ overflowX: "auto", padding: "8px 0" }}>
      <svg width={width} height="70" viewBox={`0 0 ${width} 70`} role="img" aria-label={`${totalSessions} of ${maxStones} sessions completed`}>
        <path
          d={stones
            .map((_, i) => `${i === 0 ? "M" : "L"} ${24 + i * 48} ${35 + yFor(i)}`)
            .join(" ")}
          fill="none"
          stroke="var(--stone)"
          strokeWidth="2"
          strokeDasharray="1 8"
          strokeLinecap="round"
        />
        {stones.map((filled, i) => (
          <g key={i}>
            <circle
              cx={24 + i * 48}
              cy={35 + yFor(i)}
              r={filled ? 11 : 9}
              fill={filled ? "var(--teal)" : "var(--white)"}
              stroke={filled ? "var(--teal-deep)" : "var(--stone)"}
              strokeWidth="2"
            />
            {filled && (
              <circle cx={24 + i * 48} cy={35 + yFor(i)} r="3.5" fill="var(--coral-pale)" />
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}
