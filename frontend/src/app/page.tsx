"use client";

import { useEffect, useState } from "react";
import { getIngestStatus, getTimeSeries } from "@/lib/api";
import { IngestStatus, TimeSeriesPoint } from "@/types";
import StatCard from "@/components/ui/StatCard";
import SectionHeading from "@/components/ui/SectionHeading";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import TimeSeriesChart from "@/components/charts/TimeSeriesChart";
import Link from "next/link";

export default function OverviewPage() {
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  const [series, setSeries] = useState<TimeSeriesPoint[]>([]);
  const [seriesLoading, setSeriesLoading] = useState(true);
  const [seriesError, setSeriesError] = useState<string | null>(null);

  useEffect(() => {
    getIngestStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setStatusLoading(false));
  }, []);

  useEffect(() => {
    getTimeSeries()
      .then(setSeries)
      .catch((e) => setSeriesError(e?.message ?? "Failed to load chart"))
      .finally(() => setSeriesLoading(false));
  }, []);

  return (
    <div className="news-section">
      <div className="lead-banner">
        <h2 className="lead-hed">Today’s Owl Dispatch</h2>
        <p className="deck-text">Daily signals, indexing progress, and exploratory modules from your corpus.</p>
      </div>

      <div className="mb-10 grid grid-cols-2 gap-3 md:grid-cols-4">
        {statusLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="press-card">
              <LoadingSkeleton lines={2} />
            </div>
          ))
        ) : (
          <>
            <StatCard label="Mongo Documents" value={status?.mongo_documents} sub="indexed posts" />
            <StatCard label="Chroma Vectors" value={status?.chroma_vectors} sub="semantic embeddings" />
            <StatCard label="Pipeline Status" value={status?.embedding_status ?? "-"} sub="embedding state" />
            <StatCard
              label="Vector Ratio"
              value={
                status && status.mongo_documents > 0
                  ? `${(status.chroma_vectors / status.mongo_documents).toFixed(2)}x`
                  : "-"
              }
              sub="vectors per post"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 lg:border-r lg:border-rule lg:pr-5">
          <SectionHeading kicker="Lead Story" title="Post Volume Over Time" />
          {seriesError ? (
            <div className="border border-accent px-4 py-3 text-sm text-muted" style={{ backgroundColor: "var(--color-accent-soft)" }}>
              {seriesError}
            </div>
          ) : (
            <TimeSeriesChart data={series} isLoading={seriesLoading} />
          )}
          <div className="mt-3 flex justify-end">
            <Link href="/timeseries" className="data-label transition-colors hover:text-accent">
              Full time series analysis -&gt;
            </Link>
          </div>
        </div>

        <div className="lg:pl-1">
          <SectionHeading kicker="Inside This Edition" title="Analysis Modules" />
          <div className="space-y-2">
            {[
              { href: "/timeseries", label: "Time Series", desc: "Post volume and trend behavior over time" },
              { href: "/search", label: "Semantic Search", desc: "Find posts by meaning, not keywords" },
              { href: "/network", label: "Author Network", desc: "Graph of co-poster interactions" },
              { href: "/clusters", label: "Topic Clusters", desc: "BERTopic-powered thematic groupings" },
              { href: "/embeddings", label: "UMAP Scatter", desc: "2D semantic embedding projection" },
              { href: "/chat", label: "AI Intelligence", desc: "RAG-powered Q&A across the dataset" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="press-card press-card-brief group flex items-center justify-between py-3 transition-colors hover:border-muted"
              >
                <div>
                  <p className="body-text font-semibold text-ink transition-colors group-hover:text-accent">{item.label}</p>
                  <p className="byline">{item.desc}</p>
                </div>
                <span className="text-rule transition-colors group-hover:text-accent">-&gt;</span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 border-t border-rule pt-6 text-center">
        <p className="byline">
          <span className="font-medium text-accent">Note:</span> Clusters, Embeddings, and Network run heavier ML workflows. First load may take 30 to 60 seconds.
        </p>
      </div>
    </div>
  );
}
