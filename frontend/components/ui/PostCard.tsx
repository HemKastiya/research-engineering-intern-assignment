import { SearchResult } from "@/types";
import { formatDate, truncate, formatScore } from "@/lib/utils";

interface PostCardProps {
  result: SearchResult;
  compact?: boolean;
}

export default function PostCard({ result, compact = false }: PostCardProps) {
  const { post, relevance_score } = result;
  const postId = post.id ?? post.post_id ?? "";
  const title = post.title ?? post.title_clean ?? "(untitled)";
  const createdValue = post.created_datetime ?? post.created_date ?? post.created_utc;

  return (
    <article className="press-card press-card-story group">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="kicker">r/{post.subreddit}</span>
        {relevance_score != null && (
          <span className="data-label">{(relevance_score * 100).toFixed(0)}% match</span>
        )}
      </div>

      <h3 className="section-head mb-2 text-base leading-snug transition-colors group-hover:text-accent">
        {compact ? truncate(title, 100) : title}
      </h3>

      <p className="dateline mb-3">
        By u/{post.author} | {formatDate(createdValue)}
      </p>

      {post.selftext_clean && !compact && (
        <p className="article-copy mb-3 text-sm text-ink-soft">{truncate(post.selftext_clean, 280)}</p>
      )}

      <div className="flex items-center justify-between border-t border-rule pt-2">
        <span className="data-label">score: {formatScore(post.score)}</span>
        {postId && (
          <a
            href={`https://reddit.com/r/${post.subreddit}/comments/${postId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="data-label transition-colors hover:text-accent"
          >
            Read full post -&gt;
          </a>
        )}
      </div>
    </article>
  );
}
