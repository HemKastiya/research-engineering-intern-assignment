"use client";

import { useState } from "react";
import { searchPosts } from "@/lib/api";
import { SearchResult } from "@/types";
import PostCard from "@/components/ui/PostCard";
import SectionHeading from "@/components/ui/SectionHeading";
import ErrorBanner from "@/components/ui/ErrorBanner";
import EmptyState from "@/components/ui/EmptyState";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

const EXAMPLE_QUERIES = [
  "climate change impact on ecosystems",
  "machine learning in healthcare",
  "remote work productivity tips",
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (q: string) => {
    if (!q.trim()) return;
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      const data = await searchPosts({ query: q, top_k: 15 });
      setResults(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch(query);
  };

  return (
    <div className="news-section">
      <SectionHeading kicker="Where meaning surfaces from memories." title="Pensieve Search" />

      <form onSubmit={handleSubmit} className="press-card press-card-brief mb-8">
        <div className="mb-2 flex max-w-3xl gap-2">
          <input
            id="search-input"
            className="press-input flex-1"
            placeholder="Search across all posts semantically..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={!query.trim() || isLoading} className="press-btn">
            {isLoading ? "Searching..." : "Search"}
          </button>
        </div>
        <p className="byline">Powered by MiniLM sentence embeddings and Chroma vector search</p>
      </form>

      {!hasSearched && (
        <div className="mb-6 border-y border-rule py-4">
          <p className="kicker mb-2">Suggested Openers</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                onClick={() => {
                  setQuery(q);
                  handleSearch(q);
                }}
                className="pill-badge cursor-pointer transition-colors hover:border-muted hover:text-ink"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => handleSearch(query)} />
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <LoadingSkeleton key={i} variant="card" />
          ))}
        </div>
      ) : hasSearched && results.length === 0 ? (
        <EmptyState
          title="No results found"
          description="Try a broader topic or rephrase your question with less specific wording."
          suggestions={EXAMPLE_QUERIES}
          onSuggestionClick={(s) => {
            setQuery(s);
            handleSearch(s);
          }}
        />
      ) : (
        <div className="space-y-4">
          {results.length > 0 && (
            <p className="data-label mb-3">{`${results.length} results for "${query}"`}</p>
          )}
          {results.map((r, i) => (
            <PostCard key={r.post.id ?? r.post.post_id ?? i} result={r} />
          ))}
        </div>
      )}
    </div>
  );
}
