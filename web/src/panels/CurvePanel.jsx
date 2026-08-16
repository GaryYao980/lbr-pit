import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { api } from "../api";

// no_trade_flag points are exchange-computed settlements, not real
// trades -- render hollow/dashed rather than as if they were a live market.
function NoTradeAwareDot(props) {
  const { cx, cy, payload } = props;
  const flagged = payload.no_trade_flag;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={4}
      fill={flagged ? "white" : "#2563eb"}
      stroke="#2563eb"
      strokeWidth={flagged ? 2 : 0}
      strokeDasharray={flagged ? "2 2" : undefined}
    />
  );
}

// Only 3 trade dates exist in the source CSV (flagged from the start as a
// known depth limitation) -- a dropdown of known-good dates is more honest
// here than a free date picker that mostly 404s.
const KNOWN_TRADE_DATES = ["2026-07-23", "2026-07-27", "2026-07-29"];

export default function CurvePanel() {
  const [tradeDate, setTradeDate] = useState(KNOWN_TRADE_DATES[KNOWN_TRADE_DATES.length - 1]);
  const [points, setPoints] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .curve(tradeDate)
      .then((rows) => {
        setPoints(rows);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, [tradeDate]);

  return (
    <div className="panel">
      <h2>Term structure</h2>
      <p className="note">
        Settlement price in <strong>$/MBF</strong> — dollars per thousand board feet,
        the exchange quote unit (M is the Roman thousand, not mega). One contract is
        27,500 bf = 27.5 MBF, so a $0.50 tick is $13.75.
      </p>
      <select value={tradeDate} onChange={(e) => setTradeDate(e.target.value)}>
        {KNOWN_TRADE_DATES.map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </select>
      {error && <p className="error">{error}</p>}
      <LineChart margin={{ top: 5, right: 20, bottom: 5, left: 18 }} width={420} height={260} data={points}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis domain={["auto", "auto"]} label={{ value: "$/MBF", angle: -90, position: "insideLeft" }} />
        <Tooltip />
        <Legend />
        {/* linear, not monotone: a spline invents curvature between contract months */}
        <Line type="linear" dataKey="settle" stroke="#2563eb" name="settle" dot={<NoTradeAwareDot />} />
      </LineChart>
      <p className="note">
        Hollow, dashed-ring points are <code>no_trade_flag=1</code> — exchange-computed
        settlements, not real trades. Months are ordered by{" "}
        <code>contract_start</code>, never by the label.
      </p>
      <p className="note limitation">
        <strong>3 trade dates loaded.</strong> LBR has only listed since 2022 and this
        demo ships with the settlement file on hand; full history needs a CME settlement
        feed. The loader is written and idempotent — the gap is the data, not the code.
      </p>
    </div>
  );
}
