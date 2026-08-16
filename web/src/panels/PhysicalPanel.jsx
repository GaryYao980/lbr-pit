import { useEffect, useState } from "react";
import { api } from "../api";

// the deliberate hole. Schema is real, zero rows, source named.
// Not "I need budget" -- a working machine with one part missing.
export default function PhysicalPanel() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api.physicalStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  return (
    <div className="panel panel--greyed">
      <h2>PHYSICAL / CASH</h2>
      {status ? (
        <>
          <p>
            schema ready · {status.row_count} rows
          </p>
          <p>source: {status.source}</p>
        </>
      ) : (
        <p>loading…</p>
      )}
    </div>
  );
}
