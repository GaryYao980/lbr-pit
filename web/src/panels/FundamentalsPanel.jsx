import { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from "recharts";
import { api } from "../api";

// "if only one panel gets built well, build this one."
// Two lines from ONE query pair (as_of_query DESC vs first_published_query
// ASC, see app/queries.py) -- where they separate is the whole ALFRED
// revision argument, drawn instead of argued.
//
// Over 700 monthly observations the two levels overlap almost everywhere, so
// the levels chart alone reads as "these are the same series" -- the opposite
// of the point. The revision chart below carries the argument; the levels
// chart is context for it.
const WINDOWS = [
  { label: "last 5 years", months: 60 },
  { label: "last 15 years", months: 180 },
  { label: "full history", months: null },
];

const yearOf = (d) => String(d).slice(0, 4);

export default function FundamentalsPanel() {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const [months, setMonths] = useState(WINDOWS[0].months);

  useEffect(() => {
    api
      .fundamentalsFirst("HOUST")
      .then((d) => {
        setPayload(d);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, []);

  const { rows, revisedCount, biggest } = useMemo(() => {
    if (!payload) return { rows: [], revisedCount: 0, biggest: null };
    const all = payload.points.map((p) => ({
      ...p,
      revision:
        p.current == null || p.first_published == null
          ? null
          : Number((p.current - p.first_published).toFixed(1)),
    }));
    const windowed = months == null ? all : all.slice(-months);
    const changed = all.filter((p) => p.revision != null && Math.abs(p.revision) > 0.05);
    const worst = changed.reduce(
      (acc, p) => (acc == null || Math.abs(p.revision) > Math.abs(acc.revision) ? p : acc),
      null,
    );
    return { rows: windowed, revisedCount: changed.length, biggest: worst };
  }, [payload, months]);

  return (
    <div className="panel panel--wide">
      <h2>Housing starts (HOUST) — as first published vs current</h2>
      {error && <p className="error">{error}</p>}
      {payload && payload.note && (
        <p className="note">{payload.note}</p>
      )}
      {payload && !payload.note && (
        <>
          <div className="controls">
            {WINDOWS.map((w) => (
              <button
                key={w.label}
                onClick={() => setMonths(w.months)}
                className={months === w.months ? "active" : undefined}
              >
                {w.label}
              </button>
            ))}
          </div>

          <LineChart margin={{ top: 5, right: 20, bottom: 5, left: 18 }} width={520} height={200} data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="obs_date" tickFormatter={yearOf} minTickGap={40} />
            <YAxis domain={["auto", "auto"]} label={{ value: "000s, SAAR", angle: -90, position: "insideLeft" }} />
            <Tooltip />
            <Legend />
            <Line type="linear" dataKey="first_published" stroke="#f97316" dot={false} name="as first published" />
            <Line type="linear" dataKey="current" stroke="#9333ea" dot={false} name="current (latest vintage)" />
          </LineChart>

          <h3>Revision — current minus as first published</h3>
          <LineChart margin={{ top: 5, right: 20, bottom: 5, left: 18 }} width={520} height={160} data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="obs_date" tickFormatter={yearOf} minTickGap={40} />
            <YAxis domain={["auto", "auto"]} label={{ value: "revision, 000s", angle: -90, position: "insideLeft" }} />
            <Tooltip />
            <ReferenceLine y={0} stroke="#94a3b8" />
            <Line type="linear" dataKey="revision" stroke="#0f766e" dot={false} name="revision" />
          </LineChart>

          <p className="note">
            The levels overlap because revisions are small next to the series itself. That is
            exactly why the second chart exists: every excursion from zero is a month whose
            published value was later changed. A backtest reading the current series believes
            it knew those numbers at the time.
          </p>
          <p className="note">
            {revisedCount} of {payload.points.length} observations have been revised at least
            once
            {biggest
              ? `; the largest is ${biggest.obs_date} at ${biggest.revision > 0 ? "+" : ""}${biggest.revision} thousand units`
              : ""}
            .
          </p>
          <p className="note">
            source: FRED/ALFRED (<code>etl/load_fundamentals.py</code>)
          </p>
        </>
      )}
    </div>
  );
}
