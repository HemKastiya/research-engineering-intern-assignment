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
  // Each data source has its own independent loading state
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  const [series, setSeries] = useState<TimeSeriesPoint[]>([]);
  const [seriesLoading, setSeriesLoading] = useState(true);
  const [seriesError, setSeriesError] = useState<string | null>(null);

  // Fetch ingest status independently
  useEffect(() => {
    getIngestStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setStatusLoading(false));
  }, []);

  // Fetch time series independently — this is fast (MongoDB aggregation)
  useEffect(() => {
    getTimeSeries()
      .then(setSeries)
      .catch((e) => setSeriesError(e?.message ?? "Failed to load chart"))
      .finally(() => setSeriesLoading(false));
  }, []);

  return (
    <div>
      {/* Page title */}
      <div className="mb-8 text-center">
        <p className="kicker mb-2">Intelligence Dashboard</p>
        <div className="w-24 border-t-2 border-ink mx-auto" />
      </div>

      {/* Stat strip — shows as soon as ingest status loads */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {statusLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="press-card">
              <LoadingSkeleton lines={2} />
            </div>
          ))
        ) : (
          <>
            <StatCard
              label="Mongo Documents"
              value={status?.mongo_documents}
              sub="indexed posts"
            />
            <StatCard
              label="Chroma Vectors"
              value={status?.chroma_vectors}
              sub="semantic embeddings"
            />
            <StatCard
              label="Pipeline Status"
              value={status?.embedding_status ?? "—"}
              sub="embedding state"
            />
            <StatCard
              label="Vector Ratio"
              value={
                status && status.mongo_documents > 0
                  ? `${(status.chroma_vectors / status.mongo_documents).toFixed(2)}x`
                  : "—"
              }
              sub="vectors per post"
            />
          </>
        )}
      </div>

      {/* Main grid — chart loads independently from slow endpoints */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Time series — loads fast via MongoDB aggregation */}
        <div className="lg:col-span-2">
          <SectionHeading kicker="Trend Analysis" title="Post Volume Over Time" />
          {seriesError ? (
            <div className="border-l-2 border-accent bg-[#fef2f2] px-4 py-3 text-sm text-muted">
              {seriesError}
            </div>
          ) : (
            <TimeSeriesChart data={series} isLoading={seriesLoading} />
          )}
          <div className="mt-3 flex justify-end">
            <Link href="/timeseries" className="data-label hover:text-accent transition-colors">
              Full time series analysis →
            </Link>
          </div>
        </div>

        {/* Right: Quick links — static, renders immediately */}
        <div>
          <SectionHeading kicker="Explore" title="Analysis Modules" />
          <div className="space-y-2">
            {[
              { href: "/timeseries", label: "Time Series", desc: "Post volume & trends over time" },
              { href: "/search", label: "Semantic Search", desc: "Find posts by meaning, not keywords" },
              { href: "/network", label: "Author Network", desc: "Graph of co-poster interactions" },
              { href: "/clusters", label: "Topic Clusters", desc: "BERTopic-powered groupings" },
              { href: "/embeddings", label: "UMAP Scatter", desc: "2D semantic embedding space" },
              { href: "/chat", label: "AI Intelligence", desc: "RAG-powered Q&A over the dataset" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="press-card flex items-center justify-between hover:border-muted group py-3"
              >
                <div>
                  <p className="body-text font-semibold group-hover:text-accent transition-colors">
                    {item.label}
                  </p>
                  <p className="byline">{item.desc}</p>
                </div>
                <span className="text-rule group-hover:text-accent transition-colors">→</span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Hint about heavy pages */}
      <div className="mt-8 border-t border-rule pt-6">
        <p className="byline text-center">
          <span className="text-accent font-medium">Note:</span> Clusters, Embeddings, and Network pages run ML operations — first load may take 30–60 seconds.
        </p>
      </div>
    </div>
  );
}

