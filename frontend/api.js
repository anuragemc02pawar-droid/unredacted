const BASE = "/api";

async function post(endpoint, body) {
  const res = await fetch(`${BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

async function get(endpoint) {
  const res = await fetch(`${BASE}${endpoint}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export const api = {
  health: () => get("/health"),

  scrape: (query, sources) =>
    post("/scrape", { query, sources }),

  ingest: () =>
    post("/ingest", {}),

  query: (question, top_k = 5) =>
    post("/query", { question, top_k }),

  contradictions: (question) =>
    post("/contradictions", { question }),
};