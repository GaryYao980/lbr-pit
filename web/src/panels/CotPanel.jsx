import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend, ReferenceLine } from "recharts";
import { api } from "../api";

const FAR_FUTURE = "2099-01-01";

// The series is `nonc_net` = NL - NS from the LEGACY COT report, i.e. the
// Non-Commercial category. That is NOT the same thing as Managed Money, which
// is a category in the DISAGGREGATED report and excludes the other reportable
// speculative positions that Legacy sweeps into Non-Commercial. Labelling this
// "managed money" would be wrong, and wrong in a way anyone who trades the COT
// would catch on sight.

// COT panel, driven by the as-of slider in App.jsx. "final" here is the same
// series queried far in the future, i.e. every report_date this dataset has.
// "as known" is the same series truncated at asOf -- once asOf falls before
// a report's release_ts, that report_date simply isn't in the response yet.
// This dataset has no COT revisions (see /api/cot/revisions's `note` field),
// so the two lines never differ in *value* -- only in how far the "as known"
// line currently reaches. Dragging the slider back makes its tail vanish;
// that disappearance *is* the point-in-time argument for this panel.
export default function CotPanel({ asOf }) {
  const [asKnown, setAsKnown] = useState([]);
  const [final, setFinal] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.cot(asOf, "nonc_net"), api.cot(FAR_FUTURE, "nonc_net")])
      .then(([known, fin]) => {
        setAsKnown(known);
        setFinal(fin);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, [asOf]);

  const merged = final.map((f) => {
    const k = asKnown.find((r) => r.report_date === f.report_date);
    return { report_date: f.report_date, final: f.value, as_known: k ? k.value : null };
  });

  return (
    <div className="panel">
      <h2>COT — non-commercial net position</h2>
      <p className="note">
        Legacy report, <strong>contracts</strong> (long minus short). Non-Commercial,
        not Managed Money — the latter is a Disaggregated-report category and is a
        subset of this one. Above zero is a net-long speculative community.
      </p>
      {error && <p className="error">{error}</p>}
      <LineChart margin={{ top: 5, right: 20, bottom: 5, left: 18 }} width={420} height={260} data={merged}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="report_date" hide />
        <YAxis domain={["auto", "auto"]} label={{ value: "contracts", angle: -90, position: "insideLeft" }} />
        <Tooltip formatter={(v) => (v == null ? "—" : `${v.toLocaleString()} contracts`)} />
        <Legend />
        <ReferenceLine y={0} stroke="#94a3b8" />
        {/* One series, two knowledge states -- not two series. Where both are
            defined the values are identical, so the orange line sits directly on
            the purple one; it is drawn second and thicker so the point at which
            it stops is what the eye lands on. Neither carries dots: markers on
            170 points would bury the only thing worth seeing. */}
        <Line type="linear" dataKey="final" stroke="#9333ea" name="final (all reports)" dot={false} strokeWidth={1.5} />
        <Line type="linear" dataKey="as_known" stroke="#f97316" name={`as known @ ${asOf}`} dot={false} strokeWidth={2.5} connectNulls={false} />
      </LineChart>
      <p className="note">
        As you drag the as-of slider left, the orange line's right edge retreats —
        report_dates whose release_ts is after the as-of cutoff simply aren't
        knowable yet.
      </p>
    </div>
  );
}
