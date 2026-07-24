import { useState, useEffect } from "react";
import { api } from "./api";
import SearchBar from "./components/SearchBar";
import AnswerPanel from "./components/AnswerPanel";
import ContradictionPanel from "./components/ContradictionPanel";

export default function App() {
  const [health, setHealth]             = useState(null);
  const [activeTab, setActiveTab]       = useState("query");
  const [scrapeQuery, setScrapeQuery]   = useState("");
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const [scrapeLoading, setScrapeLoading] = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [queryResult, setQueryResult]   = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [contradictions, setContradictions] = useState(null);
  const [contraLoading, setContraLoading]   = useState(false);
  const [error, setError]               = useState(null);

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch(() => setHealth({ status: "unreachable" }));
  }, []);

  async function handleScrape() {
    if (!scrapeQuery.trim()) return;
    setScrapeLoading(true);
    setError(null);
    try {
      const result = await api.scrape(scrapeQuery);
      setScrapeStatus(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setScrapeLoading(false);
    }
  }

  async function handleIngest() {
    setIngestLoading(true);
    setError(null);
    try {
      const result = await api.ingest();
      setIngestStatus(result);
      // Refresh health so chunk count updates
      api.health().then(setHealth).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setIngestLoading(false);
    }
  }

  async function handleQuery(question) {
    setQueryLoading(true);
    setError(null);
    setQueryResult(null);
    setContradictions(null);
    try {
      const result = await api.query(question);
      setQueryResult(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setQueryLoading(false);
    }
  }

  async function handleContradictions(question) {
    setContraLoading(true);
    setError(null);
    setContradictions(null);
    try {
      const result = await api.contradictions(question);
      setContradictions(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setContraLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans">

      {/* ── Header ── */}
      <header className="border-b border-gray-800 bg-gray-900 px-6 py-4
                         flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border
                          border-emerald-500/40 flex items-center
                          justify-center text-emerald-400 font-bold text-sm">
            U
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight">
              Unredacted
            </h1>
            <p className="text-xs text-gray-500">
              Government document intelligence
            </p>
          </div>
        </div>

        {/* Health pill */}
        <div className="flex items-center gap-4">
          {health && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span className={`w-2 h-2 rounded-full ${
                health.status === "ok"
                  ? "bg-emerald-400 shadow-[0_0_6px_#34d399]"
                  : "bg-red-400"
              }`} />
              {health.status === "ok"
                ? `${health.chunks} chunks indexed`
                : "Backend unreachable"}
              {health.has_api_key && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-emerald-500/10
                                 border border-emerald-500/20 text-emerald-400">
                  Claude API
                </span>
              )}
            </div>
          )}
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8">

        {/* ── Error banner ── */}
        {error && (
          <div className="mb-6 px-4 py-3 rounded-lg bg-red-500/10 border
                          border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* ── Tabs ── */}
        <div className="flex gap-1 mb-8 bg-gray-900 rounded-xl p-1
                        border border-gray-800 w-fit">
          {[
            { id: "scrape", label: "Scrape" },
            { id: "query",  label: "Query" },
            { id: "contradictions", label: "Contradictions" },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Scrape tab ── */}
        {activeTab === "scrape" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-gray-300 mb-1">
                Scrape government documents
              </h2>
              <p className="text-xs text-gray-500 mb-4">
                Enter a topic to search across CAG, PRS India, and data.gov.in.
                Documents are downloaded and saved locally.
              </p>

              <div className="flex gap-3">
                <input
                  type="text"
                  value={scrapeQuery}
                  onChange={e => setScrapeQuery(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleScrape()}
                  placeholder="e.g. coal block allocation audit"
                  className="flex-1 px-4 py-2.5 rounded-lg bg-gray-900
                             border border-gray-700 text-sm text-gray-100
                             placeholder-gray-600 outline-none
                             focus:border-emerald-500/50
                             focus:ring-1 focus:ring-emerald-500/20"
                />
                <button
                  onClick={handleScrape}
                  disabled={scrapeLoading}
                  className="px-5 py-2.5 rounded-lg bg-emerald-500 text-gray-950
                             text-sm font-semibold hover:bg-emerald-400
                             disabled:opacity-40 disabled:cursor-not-allowed
                             transition-all"
                >
                  {scrapeLoading ? "Scraping…" : "Scrape"}
                </button>
              </div>
            </div>

            {/* Scrape result */}
            {scrapeStatus && (
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
                <p className="text-sm text-gray-300 mb-3">
                  Found{" "}
                  <span className="text-emerald-400 font-semibold">
                    {scrapeStatus.documents_found}
                  </span>{" "}
                  documents for "{scrapeStatus.query}"
                </p>

                {scrapeStatus.documents.length > 0 && (
                  <div className="space-y-2 mb-4">
                    {scrapeStatus.documents.map((doc, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-3 p-3 rounded-lg
                                   bg-gray-800/50 border border-gray-700/50"
                      >
                        <span className="text-xs font-mono text-emerald-500/70
                                         bg-emerald-500/10 px-2 py-0.5 rounded
                                         mt-0.5 shrink-0">
                          {doc.source_site}
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm text-gray-200 truncate">
                            {doc.title || "Untitled"}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {doc.file_size_kb} KB
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <button
                  onClick={handleIngest}
                  disabled={ingestLoading}
                  className="w-full py-2.5 rounded-lg border border-emerald-500/30
                             text-emerald-400 text-sm font-medium
                             hover:bg-emerald-500/10 disabled:opacity-40
                             disabled:cursor-not-allowed transition-all"
                >
                  {ingestLoading
                    ? "Indexing…"
                    : "Index documents into vector store"}
                </button>

                {ingestStatus && (
                  <p className="text-xs text-gray-400 mt-3 text-center">
                    {ingestStatus.chunks_added} new chunks added —{" "}
                    {ingestStatus.total_chunks} total indexed
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Query tab ── */}
        {activeTab === "query" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-gray-300 mb-1">
                Ask a question
              </h2>
              <p className="text-xs text-gray-500 mb-4">
                Query across all indexed government documents.
                Answers are grounded in source text with citations.
              </p>
              <SearchBar
                onSearch={handleQuery}
                loading={queryLoading}
                placeholder="e.g. What irregularities were found in coal block allocation?"
              />
            </div>

            {queryLoading && (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div
                    key={i}
                    className="h-24 rounded-xl bg-gray-900 border
                               border-gray-800 animate-pulse"
                  />
                ))}
              </div>
            )}

            {queryResult && !queryLoading && (
              <AnswerPanel result={queryResult} />
            )}
          </div>
        )}

        {/* ── Contradictions tab ── */}
        {activeTab === "contradictions" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-gray-300 mb-1">
                Detect contradictions
              </h2>
              <p className="text-xs text-gray-500 mb-4">
                Find conflicting claims across different government documents
                on the same topic.
              </p>
              <SearchBar
                onSearch={handleContradictions}
                loading={contraLoading}
                placeholder="e.g. coal allocation figures 2019"
              />
            </div>

            {contraLoading && (
              <div className="space-y-3">
                {[1, 2].map(i => (
                  <div
                    key={i}
                    className="h-32 rounded-xl bg-gray-900 border
                               border-gray-800 animate-pulse"
                  />
                ))}
              </div>
            )}

            {contradictions && !contraLoading && (
              <ContradictionPanel data={contradictions} />
            )}
          </div>
        )}

      </div>
    </div>
  );
}