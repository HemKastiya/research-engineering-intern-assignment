import { NetworkNode } from "@/types";

interface NodeSidebarProps {
  node: NetworkNode | null;
  onClose: () => void;
}

export default function NodeSidebar({ node, onClose }: NodeSidebarProps) {
  if (!node) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <div className="mb-4 w-8 border-t border-rule" />
        <p className="kicker mb-2">Author Detail</p>
        <p className="byline">Click a node in the graph to view author details.</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-4 flex items-center justify-between">
        <p className="kicker">Author Profile</p>
        <button onClick={onClose} className="text-lg leading-none text-muted hover:text-ink">
          x
        </button>
      </div>
      <div className="mb-4 border-t border-rule" />

      <h3 className="section-head mb-1">{node.label}</h3>
      <p className="byline mb-6">u/{node.id}</p>

      <div className="space-y-4">
        <div className="press-card">
          <p className="kicker mb-1">PageRank Score</p>
          <p className="font-playfair text-2xl font-black text-ink">
            {node.pagerank_score.toFixed(6)}
          </p>
        </div>

        <div className="press-card">
          <p className="kicker mb-1">Community</p>
          <p className="font-playfair text-2xl font-black text-ink">#{node.community_id}</p>
        </div>

        <div className="press-card">
          <p className="kicker mb-1">Post Count</p>
          <p className="font-playfair text-2xl font-black text-ink">
            {node.post_count.toLocaleString()}
          </p>
        </div>

        <div className="press-card">
          <p className="kicker mb-2">Top Subreddits</p>
          {node.top_subreddits.length === 0 ? (
            <p className="byline">No subreddit metadata available.</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              {node.top_subreddits.map((subreddit) => (
                <span key={subreddit} className="pill-badge">
                  r/{subreddit}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="press-card">
          <p className="kicker mb-2">Top Domains</p>
          {node.top_domains.length === 0 ? (
            <p className="byline">No external-domain metadata available.</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              {node.top_domains.map((domain) => (
                <span key={domain} className="pill-badge">
                  {domain}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="press-card">
          <p className="kicker mb-2">Recent Post Titles</p>
          {node.recent_post_titles.length === 0 ? (
            <p className="byline">No title sample available.</p>
          ) : (
            <div className="space-y-2">
              {node.recent_post_titles.map((title, index) => (
                <p key={`${node.id}-${index}`} className="body-text text-xs">
                  {title}
                </p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
