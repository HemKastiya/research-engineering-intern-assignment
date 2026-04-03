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
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 border-t-2 border-ink mb-6" />
      <p className="kicker mb-3">No Results</p>
      <h3 className="section-head mb-2">{title}</h3>
      {description && (
        <p className="byline max-w-md leading-relaxed">{description}</p>
      )}
      {suggestions && suggestions.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2 justify-center">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSuggestionClick?.(s)}
              className="pill-badge cursor-pointer hover:border-muted hover:text-ink transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
