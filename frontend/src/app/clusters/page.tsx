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

  // Debounce slider
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
    <div>
      <SectionHeading kicker="Topic Modelling" title="BERTopic Clusters" />

      <div className="mb-6">
        <TopicSlider value={nTopics} onChange={setNTopics} isLoading={isLoading} />
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchClusters(debouncedN)} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cluster list */}
        <div className="lg:col-span-1">
          <p className="kicker mb-3">{topics.length} clusters</p>
          <ClusterPanel
            topics={topics}
            isLoading={isLoading}
            activeCluster={activeCluster}
            onClusterClick={(id) => setActiveCluster(activeCluster === id ? null : id)}
          />
        </div>

        {/* Active cluster detail */}
        <div className="lg:col-span-2">
          {activeTopicData ? (
            <div className="press-card h-full">
              <p className="kicker mb-2">Cluster {activeTopicData.topic_id} — Detail</p>
              <h2 className="section-head mb-4">{activeTopicData.name || `Topic ${activeTopicData.topic_id}`}</h2>

              <div className="mb-4">
                <p className="data-label mb-2">Top Terms</p>
                <div className="flex flex-wrap gap-2">
                  {(activeTopicData.representation ?? []).map((term) => (
                    <span key={term} className="pill-badge pill-badge-accent">{term}</span>
                  ))}
                </div>
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
                      : 0}%
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="press-card h-full flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 border-t border-rule mx-auto mb-4" />
                <p className="kicker mb-2">Select a Cluster</p>
                <p className="byline">Click any cluster on the left to see details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
