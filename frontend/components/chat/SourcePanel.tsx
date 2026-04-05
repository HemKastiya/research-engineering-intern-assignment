import { SearchResult } from "@/types";
import { formatDate, truncate } from "@/lib/utils";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

interface SourcePanelProps {
  sources: SearchResult[];
  isLoading?: boolean;
}

export default function SourcePanel({ sources, isLoading }: SourcePanelProps) {
  return (
    <div className="flex h-full flex-col border-l border-rule">
      <div className="border-b border-rule p-4">
        <p className="kicker mb-0.5">Retrieved Sources</p>
        <p className="byline">Context used for the latest answer</p>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => <LoadingSkeleton key={i} variant="card" lines={2} />)
        ) : sources.length === 0 ? (
          <p className="byline mt-8 text-center">No sources retrieved yet</p>
        ) : (
          sources.map((result, i) => (
            <div key={i} className="press-card press-card-brief">
              <span className="kicker mb-1 block">r/{result.post.subreddit}</span>
              <p className="body-text mb-1 font-medium leading-snug text-ink">{truncate(result.post.title, 80)}</p>
              <p className="dateline">
                {result.post.author} | {formatDate(result.post.created_utc)}
              </p>
              {result.post.selftext_clean && (
                <p className="article-copy mt-2 text-xs text-ink-soft">{truncate(result.post.selftext_clean, 120)}</p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
