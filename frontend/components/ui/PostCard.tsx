import { SearchResult } from "@/types";
import { formatDate, truncate, formatScore } from "@/lib/utils";
import Link from "next/link";

interface PostCardProps {
  result: SearchResult;
  compact?: boolean;
}

export default function PostCard({ result, compact = false }: PostCardProps) {
  const { post, relevance_score } = result;

  return (
    <article className="press-card group">
      {/* Kicker + score */}
      <div className="flex items-center justify-between mb-2">
        <span className="kicker">r/{post.subreddit}</span>
        {relevance_score != null && (
          <span className="data-label">
            {(relevance_score * 100).toFixed(0)}% match
          </span>
        )}
      </div>

      {/* Title */}
      <h3 className="section-head text-base leading-snug mb-2 group-hover:text-accent transition-colors">
        {compact ? truncate(post.title, 100) : post.title}
      </h3>

      {/* Byline */}
      <p className="byline mb-3">
        u/{post.author} · {formatDate(post.created_utc)}
      </p>

      {/* Body snippet */}
      {post.selftext_clean && !compact && (
        <p className="body-text text-muted mb-3">
          {truncate(post.selftext_clean, 280)}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-rule">
        <span className="data-label">↑ {formatScore(post.score)}</span>
        {post.id && (
          <a
            href={`https://reddit.com/r/${post.subreddit}/comments/${post.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="data-label hover:text-accent transition-colors"
          >
            View post →
          </a>
        )}
      </div>
    </article>
  );
}
