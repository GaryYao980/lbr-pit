import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { api } from "../api";

// flipping these two toggles redraws the chart -- that's
// the demonstration. roll is a RULE passed to the API, not a
// hard-coded date.
export default function ContinuousPanel() {
  const [adjust, setAdjust] = useState("none");
  const [roll, setRoll] = useState("volume");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .continuous("SEP26", "NOV26", roll, adjust)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, [adjust, roll]);

  return (
    <div className="panel">
      <h2>Continuous price</h2>
      <div className="toggles">
        <label>
          Back-adjustment:
          <select value={adjust} onChange={(e) => setAdjust(e.target.value)}>
            <option value="none">none</option>
            <option value="ratio">ratio</option>
          </select>
        </label>
        <label>
          Roll rule:
          <select value={roll} onChange={(e) => setRoll(e.target.value)}>
            <option value="volume">volume crossover</option>
            <option value="ltd">n-days-before-LTD</option>
          </select>
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <LineChart margin={{ top: 5, right: 20, bottom: 5, left: 18 }} width={420} height={260} data={data.points}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="trade_date" />
            <YAxis domain={["auto", "auto"]} label={{ value: "$/MBF", angle: -90, position: "insideLeft" }} />
            <Tooltip />
            <Legend />
            <Line type="linear" dataKey="settle" stroke="#059669" name={`continuous (${adjust})`} />
          </LineChart>
          <p className="note">
            roll_date: <code>{data.roll_date ?? "n/a"}</code>
            {data.roll_note && (
              <>
                {" — "}
                <strong>{data.roll_note}</strong>
              </>
            )}
          </p>
          <p className="note limitation">
            <strong>3 trade dates.</strong> Back-adjustment and roll rules are the point of
            this panel and both are implemented, but neither is legible across three points.
            There is no free, licensed source of deep CME settlement history — that is a paid
            feed, and it is the reason this panel is the thinnest one here.
          </p>
          <p className="note">
            Read the three panels together and they are a map of the data floor: COT and
            ALFRED are free and deep, these settlements are free and shallow, and physical
            prices are licensed and absent.
          </p>
        </>
      )}
    </div>
  );
}
