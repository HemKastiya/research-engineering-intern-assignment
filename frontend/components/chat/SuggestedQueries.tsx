interface SuggestedQueriesProps {
  suggestions: string[];
  onSelect: (q: string) => void;
}

export default function SuggestedQueries({ suggestions, onSelect }: SuggestedQueriesProps) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="px-4 pb-3">
      <p className="kicker mb-2">Suggested follow-ups</p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="pill-badge cursor-pointer hover:border-muted hover:text-ink transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
