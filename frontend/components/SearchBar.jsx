import { useState } from "react";

export default function SearchBar({ onSearch, loading, placeholder }) {
  const [value, setValue] = useState("");

  function handleSubmit() {
    if (!value.trim() || loading) return;
    onSearch(value.trim());
  }

  return (
    <div className="flex gap-3">
      <input
        type="text"
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={e => e.key === "Enter" && handleSubmit()}
        placeholder={placeholder || "Ask a question…"}
        className="flex-1 px-4 py-2.5 rounded-lg bg-gray-900
                   border border-gray-700 text-sm text-gray-100
                   placeholder-gray-600 outline-none
                   focus:border-emerald-500/50
                   focus:ring-1 focus:ring-emerald-500/20"
      />
      <button
        onClick={handleSubmit}
        disabled={loading || !value.trim()}
        className="px-5 py-2.5 rounded-lg bg-emerald-500 text-gray-950
                   text-sm font-semibold hover:bg-emerald-400
                   disabled:opacity-40 disabled:cursor-not-allowed
                   transition-all"
      >
        {loading ? "Searching…" : "Search"}
      </button>
    </div>
  );
}