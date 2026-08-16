const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status}`);
  }
  return res.json();
}

export const api = {
  curve: (tradeDate) => get(`/api/curve?trade_date=${tradeDate}`),
  continuous: (front, back, roll, adjust) =>
    get(`/api/continuous?front=${front}&back=${back}&roll=${roll}&adjust=${adjust}`),
  cot: (asOf, series) => get(`/api/cot?as_of=${asOf}&series=${series}`),
  cotRevisions: (series) => get(`/api/cot/revisions?series=${series}`),
  fundamentalsFirst: (series) => get(`/api/fundamentals/first?series=${series}`),
  physicalStatus: () => get(`/api/physical/status`),
};
