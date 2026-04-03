import { SearchResult } from "@/types";
import { formatDate, truncate } from "@/lib/utils";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

interface SourcePanelProps {
  sources: SearchResult[];
  isLoading?: boolean;
}

export default function SourcePanel({ sources, isLoading }: SourcePanelProps) {
  return (
    <div className="h-full flex flex-col border-l border-rule">
      <div className="p-4 border-b border-rule">
        <p className="kicker mb-0.5">Retrieved Sources</p>
        <p className="byline">RAG context for last response</p>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <LoadingSkeleton key={i} variant="card" lines={2} />
          ))
        ) : sources.length === 0 ? (
          <p className="byline text-center mt-8">No sources retrieved yet</p>
        ) : (
          sources.map((result, i) => (
            <div key={i} className="press-card">
              <span className="kicker block mb-1">r/{result.post.subreddit}</span>
              <p className="body-text font-medium text-ink mb-1 leading-snug">
                {truncate(result.post.title, 80)}
              </p>
              <p className="byline">{result.post.author} · {formatDate(result.post.created_utc)}</p>
              {result.post.selftext_clean && (
                <p className="body-text text-muted mt-2 text-xs">
                  {truncate(result.post.selftext_clean, 120)}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
