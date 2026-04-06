"use client";

import { useState, useEffect, useCallback } from "react";
import { getEmbeddings, EmbeddingsResult } from "@/lib/api";
import dynamic from "next/dynamic";
import SectionHeading from "@/components/ui/SectionHeading";
import ErrorBanner from "@/components/ui/ErrorBanner";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

const ScatterPlot = dynamic(() => import("@/components/charts/ScatterPlot"), {
  ssr: false,
  loading: () => <LoadingSkeleton variant="chart" />,
});

export default function EmbeddingsPage() {
  const [nClusters, setNClusters] = useState(10);
  const [showOutliers, setShowOutliers] = useState(true);
  const [data, setData] = useState<EmbeddingsResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (clusterCount: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getEmbeddings(clusterCount);
      setData(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load embeddings");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(nClusters);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="news-section">
      <SectionHeading kicker="Where concepts cluster and new territories emerge." title="The Map of Knowledge" />

      <div className="press-card press-card-brief mb-6 flex flex-wrap items-center gap-4 p-4">
        <label className="kicker whitespace-nowrap">Cluster count</label>
        <input
          type="range"
          min={2}
          max={50}
          value={nClusters}
          onChange={(e) => setNClusters(Number(e.target.value))}
          className="w-32 accent-accent"
        />
        <span className="data-label w-6">{nClusters}</span>
        <button onClick={() => fetchData(nClusters)} className="press-btn press-btn-ghost" disabled={isLoading}>
          {isLoading ? "Loading..." : "Apply"}
        </button>
        <label className="data-label ml-1 inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={showOutliers}
            onChange={(e) => setShowOutliers(e.target.checked)}
            className="h-3.5 w-3.5 accent-accent"
          />
          Show outliers
        </label>
        <p className="byline ml-auto">Scroll to zoom | drag to pan</p>
      </div>

      {data?.projection_quality && (
        <div className="press-card press-card-brief mb-4 flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">
          <p className="data-label">
            Trustworthiness@{data.projection_quality.metric_k}:{" "}
            {typeof data.projection_quality.trustworthiness_at_k === "number"
              ? data.projection_quality.trustworthiness_at_k.toFixed(3)
              : "n/a"}
          </p>
          <p className="data-label">
            kNN overlap@{data.projection_quality.metric_k}:{" "}
            {typeof data.projection_quality.knn_overlap_at_k === "number"
              ? data.projection_quality.knn_overlap_at_k.toFixed(3)
              : "n/a"}
          </p>
          <p className="data-label">
            Outliers: {(data.projection_quality.outlier_ratio * 100).toFixed(1)}%
          </p>
          <p className="data-label">
            UMAP params: n_neighbors={data.projection_quality.umap_n_neighbors}, min_dist=
            {data.projection_quality.umap_min_dist}
          </p>
          <p className="byline">Auto-tuned on {data.projection_quality.sample_size} sampled points</p>
        </div>
      )}

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchData(nClusters)} />
        </div>
      )}

      <div className="press-card p-0 overflow-hidden">
        {isLoading ? (
          <div className="flex h-[520px] items-center justify-center bg-wash">
            <div className="text-center">
              <div className="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-2 border-ink border-t-transparent" />
              <p className="byline">Projecting embeddings...</p>
            </div>
          </div>
        ) : (
          <ScatterPlot data={data} isLoading={isLoading} showOutliers={showOutliers} />
        )}
      </div>

      {data && (
        <div className="mt-3 flex gap-6">
          <p className="data-label">{data.umap_2d?.length ?? 0} data points</p>
          <p className="data-label">{[...new Set(data.cluster_labels ?? [])].length} clusters rendered</p>
        </div>
      )}
    </div>
  );
}
