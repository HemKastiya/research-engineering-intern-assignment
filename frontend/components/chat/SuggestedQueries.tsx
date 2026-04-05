interface SuggestedQueriesProps {
  suggestions: string[];
  onSelect: (q: string) => void;
}

export default function SuggestedQueries({ suggestions, onSelect }: SuggestedQueriesProps) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="border-t border-rule px-4 pb-3 pt-2">
      <p className="kicker mb-2">Suggested Follow-ups</p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="pill-badge cursor-pointer transition-colors hover:border-muted hover:text-ink"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
