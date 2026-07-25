export default function SourceCard({ source }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-900 border border-gray-800">
      <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded shrink-0">
        {source.site}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-gray-200 truncate">
          {source.title || "Untitled document"}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">
          Page {source.page}
        </p>
        {source.url && (
          
            <a href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-emerald-500/70 hover:text-emerald-400 transition-colors"
          >
            View source
          </a>
        )}
      </div>
    </div>
  );
}