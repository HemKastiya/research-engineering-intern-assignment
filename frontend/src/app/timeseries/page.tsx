"use client";

import { useState, useEffect, useCallback } from "react";
import { getTimeSeries, getTimeSeriesSummary } from "@/lib/api";
import { TimeSeriesPoint } from "@/types";
import TimeSeriesChart from "@/components/charts/TimeSeriesChart";
import SectionHeading from "@/components/ui/SectionHeading";
import ErrorBanner from "@/components/ui/ErrorBanner";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

export default function TimeSeriesPage() {
  const [query, setQuery] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [data, setData] = useState<TimeSeriesPoint[]>([]);
  const [summary, setSummary] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (q: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const [ts, sumRes] = await Promise.all([
        getTimeSeries({ query: q || undefined }),
        getTimeSeriesSummary(q || undefined).catch(() => null),
      ]);
      setData(ts);
      setSummary(sumRes?.summary ?? null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load time series");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounce input
  useEffect(() => {
    const id = setTimeout(() => setQuery(inputValue), 400);
    return () => clearTimeout(id);
  }, [inputValue]);

  useEffect(() => {
    fetchData(query);
  }, [query, fetchData]);

  return (
    <div>
      <SectionHeading kicker="Trend Analysis" title="Post Volume Over Time" />

      {/* Search bar */}
      <div className="mb-6">
        <input
          id="timeseries-query"
          className="press-input max-w-xl"
          placeholder="Filter by keyword (e.g. 'climate change')…"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        <p className="byline mt-1">Debounces 400ms · leave blank for all posts</p>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchData(query)} />
        </div>
      )}

      {/* Chart */}
      <div className="press-card mb-6">
        <TimeSeriesChart data={data} isLoading={isLoading} />
      </div>

      {/* AI Summary */}
      <div className="mb-6">
        <SectionHeading kicker="AI-Generated Summary" title="Trend Interpretation" />
        {isSummaryLoading ? (
          <LoadingSkeleton lines={4} />
        ) : summary ? (
          <div className="press-card border-l-4 border-accent">
            <p className="kicker mb-2">Gemini Analysis</p>
            <p className="body-text leading-relaxed">{summary}</p>
          </div>
        ) : (
          <p className="byline">No summary available for the current query.</p>
        )}
      </div>

      {/* Stats */}
      <div className="press-card">
        <p className="kicker mb-2">Dataset Statistics</p>
        <div className="flex flex-wrap gap-6">
          <div>
            <span className="data-label">Total data points</span>
            <p className="font-playfair text-xl font-black">{data.length}</p>
          </div>
          <div>
            <span className="data-label">Total posts</span>
            <p className="font-playfair text-xl font-black">
              {data.reduce((s, d) => s + d.count, 0).toLocaleString()}
            </p>
          </div>
          {data.length > 0 && (
            <div>
              <span className="data-label">Date range</span>
              <p className="font-playfair text-xl font-black">
                {data[0].date} → {data[data.length - 1].date}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
