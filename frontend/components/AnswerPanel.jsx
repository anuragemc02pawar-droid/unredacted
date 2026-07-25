import SourceCard from "./SourceCard";

export default function AnswerPanel({ result }) {
  return (
    <div className="space-y-5">

      {/* Mocked warning */}
      {result.mocked && (
        <div className="px-4 py-3 rounded-lg bg-yellow-500/10 border
                        border-yellow-500/30 text-yellow-400 text-xs">
          Mock response — add <code className="font-mono">ANTHROPIC_API_KEY</code> to{" "}
          <code className="font-mono">backend/.env</code> for real answers.
        </div>
      )}

      {/* Answer */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold text-emerald-400
                           uppercase tracking-wider">
            Answer
          </span>
          <span className="text-xs text-gray-600">
            from {result.chunk_count} document excerpts
          </span>
        </div>
        <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
          {result.answer}
        </p>
      </div>

      {/* Sources */}
      {result.sources.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase
                        tracking-wider mb-3">
            Sources
          </p>
          <div className="space-y-2">
            {result.sources.map((source, i) => (
              <SourceCard key={i} source={source} />
            ))}
          </div>
        </div>
      )}

      {/* Retrieved chunks */}
      {result.chunks.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase
                        tracking-wider mb-3">
            Relevant excerpts
          </p>
          <div className="space-y-2">
            {result.chunks.map((chunk, i) => (
              <div
                key={i}
                className="p-4 rounded-lg bg-gray-900 border border-gray-800"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-400 truncate max-w-xs">
                    {chunk.title} — p.{chunk.page}
                  </span>
                  <span className="text-xs font-mono text-emerald-500/70
                                   bg-emerald-500/10 px-2 py-0.5 rounded ml-2
                                   shrink-0">
                    {chunk.score.toFixed(3)}
                  </span>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed">
                  {chunk.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}