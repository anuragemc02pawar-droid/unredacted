export default function ContradictionPanel({ data }) {
  if (data.contradictions_found === 0) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-8
                      text-center">
        <p className="text-2xl mb-2">✓</p>
        <p className="text-sm text-gray-300 font-medium">
          No contradictions found
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {data.chunks_analyzed} excerpts analyzed across documents
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-400">
        <span className="text-red-400 font-semibold">
          {data.contradictions_found} potential contradiction
          {data.contradictions_found !== 1 ? "s" : ""}
        </span>{" "}
        found across {data.chunks_analyzed} excerpts
      </p>

      {data.contradictions.map((pair, i) => (
        <div
          key={i}
          className="rounded-xl border border-red-500/20 bg-gray-900 p-5"
        >
          {/* Similarity badge */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs font-mono text-red-400/80
                             bg-red-500/10 px-2 py-0.5 rounded">
              similarity {pair.similarity.toFixed(3)}
            </span>
            <span className="text-xs text-gray-500">
              — same topic, different claims
            </span>
          </div>

          {/* Conflict hint */}
          <p className="text-xs text-gray-400 mb-4 leading-relaxed">
            {pair.conflict_hint}
          </p>

          {/* Side by side */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { doc: pair.document_a, values: pair.values_a, label: "A" },
              { doc: pair.document_b, values: pair.values_b, label: "B" },
            ].map(({ doc, values, label }) => (
              <div
                key={label}
                className="p-3 rounded-lg bg-gray-800/60 border border-gray-700/50"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono text-gray-500
                                   bg-gray-700 px-1.5 py-0.5 rounded">
                    {label}
                  </span>
                  <span className="text-xs font-mono text-emerald-500/60">
                    {doc.site}
                  </span>
                </div>
                <p className="text-xs text-gray-300 font-medium truncate mb-1">
                  {doc.title} — p.{doc.page}
                </p>
                <p className="text-xs text-gray-500 leading-relaxed mb-3">
                  {doc.excerpt}
                </p>
                {values.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {values.slice(0, 4).map((v, j) => (
                      <span
                        key={j}
                        className="text-xs font-mono text-yellow-400/80
                                   bg-yellow-500/10 px-2 py-0.5 rounded"
                      >
                        {v}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}