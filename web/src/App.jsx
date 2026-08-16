import { useState } from "react";
import CurvePanel from "./panels/CurvePanel.jsx";
import ContinuousPanel from "./panels/ContinuousPanel.jsx";
import CotPanel from "./panels/CotPanel.jsx";
import FundamentalsPanel from "./panels/FundamentalsPanel.jsx";
import PhysicalPanel from "./panels/PhysicalPanel.jsx";
import "./index.css";

// The as-of slider is the whole point : it sets the knowledge
// cutoff for the page. cot_lumber_clean.csv spans 2021-01-05 .. 2026-07-21;
// the slider walks that range week by week.
const RANGE_START = new Date("2021-01-05");
const RANGE_END = new Date("2026-07-28"); // one week past the last report, so the final week is reachable
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
const TOTAL_WEEKS = Math.round((RANGE_END - RANGE_START) / WEEK_MS);

function weekIndexToDate(i) {
  return new Date(RANGE_START.getTime() + i * WEEK_MS).toISOString().slice(0, 10);
}

export default function App() {
  const [weekIndex, setWeekIndex] = useState(TOTAL_WEEKS);
  const asOf = weekIndexToDate(weekIndex);

  return (
    <div className="app">
      <aside className="rail">
        <h1>lbr-pit</h1>
        <p className="subtitle">point-in-time lumber dashboard</p>
        <label className="as-of-label">
          as of: <strong>{asOf}</strong>
        </label>
        <input
          type="range"
          min={0}
          max={TOTAL_WEEKS}
          value={weekIndex}
          onChange={(e) => setWeekIndex(Number(e.target.value))}
          className="as-of-slider"
        />
        <p className="note">
          Dragging this backwards makes data disappear that had not been
          published yet — that's the whole demo.
        </p>
      </aside>

      <main className="grid">
        <CurvePanel />
        <ContinuousPanel />
        <CotPanel asOf={asOf} />
        <FundamentalsPanel />
        <PhysicalPanel />
      </main>
    </div>
  );
}
