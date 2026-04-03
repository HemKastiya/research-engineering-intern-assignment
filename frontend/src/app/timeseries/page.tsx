"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import AnalyticsChart, {
  AnalyticsChartType,
  AnalyticsDatum,
} from "@/components/charts/AnalyticsChart";
import ErrorBanner from "@/components/ui/ErrorBanner";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import SectionHeading from "@/components/ui/SectionHeading";
import { getTimeSeriesAnalytics, getTimeSeriesSummary } from "@/lib/api";
import { TimeSeriesAnalytics } from "@/types";

type DatasetKey =
  | "volume"
  | "avg_score"
  | "avg_engagement"
  | "subreddit_share"
  | "weekday_activity"
  | "score_buckets"
  | "anomalies"
  | "cluster_distribution";

const DATASET_META: Record<
  DatasetKey,
  {
    label: string;
    valueLabel: string;
    isDateAxis?: boolean;
    allowedChartTypes: AnalyticsChartType[];
  }
> = {
  volume: {
    label: "Daily Post Volume",
    valueLabel: "Posts",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
  avg_score: {
    label: "Daily Average Score",
    valueLabel: "Avg Score",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
  avg_engagement: {
    label: "Daily Average Engagement",
    valueLabel: "Avg Engagement",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
  subreddit_share: {
    label: "Subreddit Share",
    valueLabel: "Posts",
    allowedChartTypes: ["pie", "bar"],
  },
  weekday_activity: {
    label: "Weekday Activity",
    valueLabel: "Posts",
    allowedChartTypes: ["bar", "pie"],
  },
  score_buckets: {
    label: "Score Bucket Distribution",
    valueLabel: "Posts",
    allowedChartTypes: ["bar", "pie"],
  },
  anomalies: {
    label: "Anomalous Days (Isolation Forest)",
    valueLabel: "Posts",
    isDateAxis: true,
    allowedChartTypes: ["bar", "line"],
  },
  cluster_distribution: {
    label: "Daily Regime Clusters (KMeans)",
    valueLabel: "Days",
    allowedChartTypes: ["bar", "pie"],
  },
};

function buildChartData(analytics: TimeSeriesAnalytics | null, key: DatasetKey): AnalyticsDatum[] {
  if (!analytics) return [];

  switch (key) {
    case "volume":
      return analytics.time_series.map((point) => ({ label: point.date, value: point.count }));
    case "avg_score":
      return analytics.time_series.map((point) => ({
        label: point.date,
        value: Number(point.avg_score.toFixed(3)),
      }));
    case "avg_engagement":
      return analytics.time_series.map((point) => ({
        label: point.date,
        value: Number(point.avg_engagement.toFixed(3)),
      }));
    case "subreddit_share":
      return analytics.subreddit_distribution.map((row) => ({ label: row.label, value: row.value }));
    case "weekday_activity":
      return analytics.weekday_distribution.map((row) => ({ label: row.label, value: row.value }));
    case "score_buckets":
      return analytics.score_buckets.map((row) => ({ label: row.label, value: row.value }));
    case "anomalies":
      return analytics.ml_models.anomalies.map((row) => ({ label: row.date, value: row.count }));
    case "cluster_distribution":
      return analytics.ml_models.daily_clusters.clusters.map((row) => ({
        label: `Cluster ${row.cluster_id}`,
        value: row.days,
      }));
    default:
      return [];
  }
}

export default function TimeSeriesPage() {
  const [query, setQuery] = useState("");
  const [inputValue, setInputValue] = useState("");

  const [analytics, setAnalytics] = useState<TimeSeriesAnalytics | null>(null);
  const [summary, setSummary] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedDataset, setSelectedDataset] = useState<DatasetKey>("volume");
  const [selectedChartType, setSelectedChartType] = useState<AnalyticsChartType>("line");

  const fetchData = useCallback(async (q: string) => {
    setIsLoading(true);
    setIsSummaryLoading(true);
    setError(null);

    try {
      const analyticsResponse = await getTimeSeriesAnalytics({ query: q || undefined });
      setAnalytics(analyticsResponse);
      setIsLoading(false);

      const summaryResponse = await getTimeSeriesSummary(q || undefined).catch(() => null);
      setSummary(summaryResponse?.summary ?? null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load analytics");
      setAnalytics(null);
      setSummary(null);
    } finally {
      setIsSummaryLoading(false);
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const debounceId = setTimeout(() => setQuery(inputValue), 400);
    return () => clearTimeout(debounceId);
  }, [inputValue]);

  useEffect(() => {
    fetchData(query);
  }, [query, fetchData]);

  useEffect(() => {
    const meta = DATASET_META[selectedDataset];
    if (!meta.allowedChartTypes.includes(selectedChartType)) {
      setSelectedChartType(meta.allowedChartTypes[0]);
    }
  }, [selectedDataset, selectedChartType]);

  const chartData = useMemo(
    () => buildChartData(analytics, selectedDataset),
    [analytics, selectedDataset]
  );

  const totalPosts = useMemo(
    () => (analytics ? analytics.time_series.reduce((sum, point) => sum + point.count, 0) : 0),
    [analytics]
  );

  const trend = analytics?.ml_models.trend_regression;
  const anomaliesCount = analytics?.ml_models.anomalies.length ?? 0;
  const clusterCount = analytics?.ml_models.daily_clusters.n_clusters ?? 0;

  return (
    <div>
      <SectionHeading kicker="Trend Intelligence" title="Interactive Time-Series Analytics" />

      <div className="mb-6">
        <input
          id="timeseries-query"
          className="press-input max-w-xl"
          placeholder="Filter by keyword (e.g. climate change)..."
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
        />
        <p className="byline mt-1">Debounced query (400ms). Leave blank to analyze the full dataset.</p>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchData(query)} />
        </div>
      )}

      <div className="press-card mb-6">
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="data-label block mb-1">Dataset</label>
            <select
              className="press-input"
              value={selectedDataset}
              onChange={(event) => setSelectedDataset(event.target.value as DatasetKey)}
            >
              {Object.entries(DATASET_META).map(([key, meta]) => (
                <option key={key} value={key}>
                  {meta.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="data-label block mb-1">Chart Type</label>
            <select
              className="press-input"
              value={selectedChartType}
              onChange={(event) => setSelectedChartType(event.target.value as AnalyticsChartType)}
            >
              {DATASET_META[selectedDataset].allowedChartTypes.map((chartType) => (
                <option key={chartType} value={chartType}>
                  {chartType.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
          <div className="ml-auto self-end">
            <p className="byline">
              View: <span className="font-semibold text-ink">{DATASET_META[selectedDataset].label}</span>
            </p>
          </div>
        </div>

        <AnalyticsChart
          data={chartData}
          chartType={selectedChartType}
          valueLabel={DATASET_META[selectedDataset].valueLabel}
          isDateAxis={DATASET_META[selectedDataset].isDateAxis}
          isLoading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="press-card">
          <p className="kicker mb-2">Trend Model</p>
          {isLoading ? (
            <LoadingSkeleton lines={2} />
          ) : (
            <>
              <p className="body-text">Direction: <span className="font-semibold text-ink">{trend?.direction ?? "flat"}</span></p>
              <p className="byline">Slope: {trend ? trend.slope.toFixed(3) : "0.000"}</p>
              <p className="byline">R�: {trend ? trend.r2.toFixed(3) : "0.000"}</p>
            </>
          )}
        </div>

        <div className="press-card">
          <p className="kicker mb-2">Anomaly Detection</p>
          {isLoading ? (
            <LoadingSkeleton lines={2} />
          ) : (
            <>
              <p className="body-text"><span className="font-semibold text-ink">{anomaliesCount}</span> anomalous day(s)</p>
              <p className="byline">Isolation Forest over count/score/engagement.</p>
            </>
          )}
        </div>

        <div className="press-card">
          <p className="kicker mb-2">Regime Clustering</p>
          {isLoading ? (
            <LoadingSkeleton lines={2} />
          ) : (
            <>
              <p className="body-text"><span className="font-semibold text-ink">{clusterCount}</span> behavior cluster(s)</p>
              <p className="byline">KMeans on daily feature vectors.</p>
            </>
          )}
        </div>
      </div>

      <div className="mb-6">
        <SectionHeading kicker="AI-Generated Summary" title="Narrative Interpretation" />
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

      <div className="press-card">
        <p className="kicker mb-2">Dataset Statistics</p>
        <div className="flex flex-wrap gap-6">
          <div>
            <span className="data-label">Total days</span>
            <p className="font-playfair text-xl font-black">{analytics?.time_series.length ?? 0}</p>
          </div>
          <div>
            <span className="data-label">Total posts</span>
            <p className="font-playfair text-xl font-black">{totalPosts.toLocaleString()}</p>
          </div>
          {analytics && analytics.time_series.length > 0 && (
            <div>
              <span className="data-label">Date range</span>
              <p className="font-playfair text-xl font-black">
                {analytics.time_series[0].date} to {analytics.time_series[analytics.time_series.length - 1].date}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
