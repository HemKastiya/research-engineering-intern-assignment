"use client";

import { useState, useEffect, useCallback } from "react";
import { getClusters } from "@/lib/api";
import { ClusterTopic } from "@/types";
import TopicSlider from "@/components/clusters/TopicSlider";
import ClusterPanel from "@/components/clusters/ClusterPanel";
import SectionHeading from "@/components/ui/SectionHeading";
import ErrorBanner from "@/components/ui/ErrorBanner";

export default function ClustersPage() {
  const [nTopics, setNTopics] = useState(10);
  const [debouncedN, setDebouncedN] = useState(10);
  const [topics, setTopics] = useState<ClusterTopic[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCluster, setActiveCluster] = useState<number | null>(null);

  useEffect(() => {
    const id = setTimeout(() => setDebouncedN(nTopics), 600);
    return () => clearTimeout(id);
  }, [nTopics]);

  const fetchClusters = useCallback(async (n: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getClusters(n);
      setTopics(result.topics ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load clusters");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClusters(debouncedN);
  }, [debouncedN, fetchClusters]);

  const activeTopicData = topics.find((t) => t.topic_id === activeCluster);

  return (
    <div className="news-section">
      <SectionHeading kicker="Every document finds the house it truly belongs." title="The Sorting Hat" />

      <div className="press-card press-card-brief mb-6">
        <TopicSlider value={nTopics} onChange={setNTopics} isLoading={isLoading} />
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchClusters(debouncedN)} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <p className="kicker mb-3">{topics.length} topics</p>
          <ClusterPanel
            topics={topics}
            isLoading={isLoading}
            activeCluster={activeCluster}
            onClusterClick={(id) => setActiveCluster(activeCluster === id ? null : id)}
          />
        </div>

        <div className="lg:col-span-2">
          {activeTopicData ? (
            <div className="press-card press-card-brief h-full">
              <p className="kicker mb-2">Topic {activeTopicData.topic_id + 1} - Detail</p>
              <h2 className="section-head mb-4">{activeTopicData.name || `Topic ${activeTopicData.topic_id}`}</h2>

              <div className="mb-4">
                <p className="data-label mb-2">Top Terms</p>
                <div className="flex flex-wrap gap-2">
                  {(activeTopicData.representation ?? []).map((term) => (
                    <span key={term} className="pill-badge pill-badge-accent">
                      {term}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mb-4 border-t border-rule pt-4">
                <p className="data-label mb-2">Top Representative Posts</p>
                {(activeTopicData.top_posts ?? []).length > 0 ? (
                  <div className="space-y-2">
                    {(activeTopicData.top_posts ?? []).slice(0, 10).map((post) => {
                      const href = post.permalink
                        ? post.permalink.startsWith("http")
                          ? post.permalink
                          : `https://reddit.com${post.permalink}`
                        : "";

                      return (
                        <div key={post.post_id} className="border border-rule bg-wash p-3">
                          {href ? (
                            <a href={href} target="_blank" rel="noopener noreferrer" className="font-semibold text-accent hover:underline">
                              {post.title}
                            </a>
                          ) : (
                            <p className="font-semibold text-ink">{post.title}</p>
                          )}
                          <p className="byline mt-1">
                            u/{post.author} in r/{post.subreddit} | Score {post.score} | Comments {post.num_comments}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="byline">No representative posts available for this topic.</p>
                )}
              </div>

              <div className="flex gap-6 border-t border-rule pt-4">
                <div>
                  <p className="data-label">Post Count</p>
                  <p className="font-playfair text-2xl font-black">{activeTopicData.count.toLocaleString()}</p>
                </div>
                <div>
                  <p className="data-label">Share of Dataset</p>
                  <p className="font-playfair text-2xl font-black">
                    {topics.length > 0
                      ? ((activeTopicData.count / topics.reduce((s, t) => s + t.count, 0)) * 100).toFixed(1)
                      : 0}
                    %
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="press-card press-card-brief flex h-full items-center justify-center">
              <div className="text-center">
                <div className="mx-auto mb-4 w-12 border-t border-rule" />
                <p className="kicker mb-2">Select a Topic</p>
                <p className="byline">Click any topic on the left to see details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
