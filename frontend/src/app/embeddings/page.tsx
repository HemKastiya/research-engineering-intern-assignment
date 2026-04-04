"use client";

import { useState, useEffect, useCallback } from "react";
import { getEmbeddings, EmbeddingsResult } from "@/lib/api";
import dynamic from "next/dynamic";
import SectionHeading from "@/components/ui/SectionHeading";
import ErrorBanner from "@/components/ui/ErrorBanner";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

const ScatterPlot = dynamic(
  () => import("@/components/charts/ScatterPlot"),
  { ssr: false, loading: () => <LoadingSkeleton variant="chart" /> }
);

export default function EmbeddingsPage() {
  const [nClusters, setNClusters] = useState(10);
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
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <SectionHeading kicker="Embedding Space" title="UMAP 2D Projection" />

      <div className="flex items-center gap-4 mb-6 p-4 bg-wash border border-rule rounded flex-wrap">
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
        <button
          onClick={() => fetchData(nClusters)}
          className="press-btn press-btn-ghost"
          disabled={isLoading}
        >
          {isLoading ? "Loading…" : "Apply"}
        </button>
        <p className="byline ml-auto">Scroll to zoom · drag to pan</p>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchData(nClusters)} />
        </div>
      )}

      <div className="press-card p-0 overflow-hidden">
        {isLoading ? (
          <div className="h-[520px] flex items-center justify-center bg-wash">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-ink border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <p className="byline">Projecting embeddings…</p>
            </div>
          </div>
        ) : (
          <ScatterPlot data={data} isLoading={isLoading} />
        )}
      </div>

      {data && (
        <div className="mt-3 flex gap-6">
          <p className="data-label">{data.umap_2d?.length ?? 0} data points</p>
          <p className="data-label">
            {[...new Set(data.cluster_labels ?? [])].length} clusters rendered
          </p>
        </div>
      )}
    </div>
  );
}
