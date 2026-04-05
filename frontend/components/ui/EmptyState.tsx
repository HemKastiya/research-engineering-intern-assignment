interface EmptyStateProps {
  title: string;
  description?: string;
  suggestions?: string[];
  onSuggestionClick?: (suggestion: string) => void;
}

export default function EmptyState({
  title,
  description,
  suggestions,
  onSuggestionClick,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center">
      <div className="mb-6 w-20 border-t-2 border-ink" />
      <p className="kicker mb-2">No Results</p>
      <h3 className="section-head mb-2">{title}</h3>
      {description && <p className="deck-text text-sm">{description}</p>}
      {suggestions && suggestions.length > 0 && (
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSuggestionClick?.(s)}
              className="pill-badge cursor-pointer transition-colors hover:border-muted hover:text-ink"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
