"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import AnalyticsChart, {
  AnalyticsChartType,
  AnalyticsDatum,
} from "@/components/charts/AnalyticsChart";
import ErrorBanner from "@/components/ui/ErrorBanner";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import SectionHeading from "@/components/ui/SectionHeading";
import { getTimeSeriesAnalytics, getTimeSeriesSummary, TimeSeriesParams } from "@/lib/api";
import { TimeSeriesAnalytics } from "@/types";

type DatasetKey =
  | "volume"
  | "avg_score"
  | "avg_engagement"
  | "trend_line"
  | "projection_next_week"
  | "subreddit_share"
  | "weekday_activity"
  | "score_buckets"
  | "anomalies"
  | "cluster_distribution"
  | "cluster_timeline";

const DATASET_META: Record<
  DatasetKey,
  {
    label: string;
    valueLabel: string;
    description: string;
    isDateAxis?: boolean;
    allowedChartTypes: AnalyticsChartType[];
  }
> = {
  volume: {
    label: "Daily Post Volume",
    valueLabel: "Posts",
    description: "Raw number of matching posts per day.",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
  avg_score: {
    label: "Daily Average Score",
    valueLabel: "Avg Score",
    description: "Average Reddit score across matching posts each day.",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
  avg_engagement: {
    label: "Daily Average Engagement",
    valueLabel: "Avg Engagement",
    description: "Average engagement (score + comments) per post each day.",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
  trend_line: {
    label: "Trend Line (Regression)",
    valueLabel: "Predicted Posts",
    description: "Best-fit line from linear regression over daily post counts.",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
  projection_next_week: {
    label: "7-Day Projection",
    valueLabel: "Projected Posts",
    description: "Model-projected post counts for the next 7 days.",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
  subreddit_share: {
    label: "Subreddit Share",
    valueLabel: "Posts",
    description: "Top subreddits by number of matching posts.",
    allowedChartTypes: ["pie", "bar"],
  },
  weekday_activity: {
    label: "Weekday Activity",
    valueLabel: "Posts",
    description: "How matching activity is distributed across weekdays.",
    allowedChartTypes: ["bar", "pie"],
  },
  score_buckets: {
    label: "Score Bucket Distribution",
    valueLabel: "Posts",
    description: "Counts of posts grouped by score ranges.",
    allowedChartTypes: ["bar", "pie"],
  },
  anomalies: {
    label: "Anomalous Days (Isolation Forest)",
    valueLabel: "Posts",
    description: "Outlier days detected from count, score, and engagement features.",
    isDateAxis: true,
    allowedChartTypes: ["bar", "line"],
  },
  cluster_distribution: {
    label: "Daily Regime Clusters (KMeans)",
    valueLabel: "Days",
    description: "How many days fall into each behavior cluster.",
    allowedChartTypes: ["bar", "pie"],
  },
  cluster_timeline: {
    label: "Cluster Timeline",
    valueLabel: "Cluster ID",
    description: "Per-day cluster assignment from KMeans regime modeling.",
    isDateAxis: true,
    allowedChartTypes: ["line", "bar"],
  },
};

const FIELD_HELP: Array<{ field: string; meaning: string }> = [
  { field: "count", meaning: "Number of posts on a given day." },
  { field: "avg_score", meaning: "Average Reddit score per post on that day." },
  { field: "avg_engagement", meaning: "Average value of score + comments per post." },
  { field: "slope", meaning: "Trend strength from linear regression over daily counts." },
  { field: "r2", meaning: "How well the trend line explains day-to-day variation (0 to 1)." },
  { field: "direction", meaning: "Trend direction: upward, downward, or flat." },
  { field: "predicted_count", meaning: "Model-estimated post count (trend line or forecast)." },
  { field: "anomaly", meaning: "A day flagged as statistically unusual by Isolation Forest." },
  { field: "cluster_id", meaning: "Behavior regime label assigned by KMeans." },
  { field: "days", meaning: "Number of days assigned to a given cluster." },
];

function normalizeSubreddit(value: string): string {
  return value.trim().replace(/^r\//i, "");
}

function normalizeFilters(filters: TimeSeriesParams): TimeSeriesParams {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => Boolean(value)));
}

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
    case "trend_line":
      return analytics.ml_models.trend_regression.trend_line.map((point) => ({
        label: point.date,
        value: point.predicted_count,
      }));
    case "projection_next_week":
      return analytics.ml_models.trend_regression.projected_next.map((point) => ({
        label: point.date,
        value: point.predicted_count,
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
    case "cluster_timeline":
      return analytics.ml_models.daily_clusters.assignments.map((row) => ({
        label: row.date,
        value: row.cluster_id,
      }));
    default:
      return [];
  }
}

export default function TimeSeriesPage() {
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");

  const [subredditInput, setSubredditInput] = useState("");
  const [subreddit, setSubreddit] = useState("");

  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const [analytics, setAnalytics] = useState<TimeSeriesAnalytics | null>(null);
  const [summary, setSummary] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedDataset, setSelectedDataset] = useState<DatasetKey>("volume");
  const [selectedChartType, setSelectedChartType] = useState<AnalyticsChartType>("line");

  const filters = useMemo(
    () =>
      normalizeFilters({
        query: query || undefined,
        subreddit: subreddit || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
      }),
    [query, subreddit, fromDate, toDate]
  );

  const dateRangeError = useMemo(() => {
    if (!fromDate || !toDate) return null;
    return fromDate <= toDate ? null : "Invalid date range: 'From' date must be before 'To' date.";
  }, [fromDate, toDate]);

  const fetchData = useCallback(async (activeFilters: TimeSeriesParams) => {
    setIsLoading(true);
    setIsSummaryLoading(true);
    setError(dateRangeError);

    try {
      const analyticsResponse = await getTimeSeriesAnalytics(activeFilters);
      setAnalytics(analyticsResponse);
      setIsLoading(false);

      const summaryResponse = await getTimeSeriesSummary(activeFilters).catch(() => null);
      setSummary(summaryResponse?.summary ?? null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load analytics");
      setAnalytics(null);
      setSummary(null);
    } finally {
      setIsSummaryLoading(false);
      setIsLoading(false);
    }
  }, [dateRangeError]);

  useEffect(() => {
    const debounceId = setTimeout(() => {
      setQuery(queryInput.trim());
      setSubreddit(normalizeSubreddit(subredditInput));
    }, 400);
    return () => clearTimeout(debounceId);
  }, [queryInput, subredditInput]);

  useEffect(() => {
    if (dateRangeError) {
      setError(dateRangeError);
      setIsLoading(false);
      setIsSummaryLoading(false);
      return;
    }
    fetchData(filters);
  }, [dateRangeError, fetchData, filters]);

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
  const clusterSummaries = analytics?.ml_models.daily_clusters.clusters ?? [];

  const projectedNextWeek = trend?.projected_next ?? [];
  const projectionHeadline =
    projectedNextWeek.length > 0
      ? `${projectedNextWeek[0].date} to ${projectedNextWeek[projectedNextWeek.length - 1].date}`
      : "Insufficient history";

  const hasActiveFilters = Boolean(query || subreddit || fromDate || toDate);

  const clearFilters = () => {
    setQueryInput("");
    setSubredditInput("");
    setFromDate("");
    setToDate("");
    setError(null);
  };

  return (
    <div className="news-section">
      <SectionHeading kicker="Revisit the past. Reveal the trends." title="The Time Turner" />

      <div className="press-card press-card-brief mb-6">
        <p className="kicker mb-3">Filters</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label htmlFor="timeseries-query" className="data-label block mb-1">Keyword query</label>
            <input
              id="timeseries-query"
              className="press-input w-full"
              placeholder="e.g. climate change"
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="timeseries-subreddit" className="data-label block mb-1">Subreddit</label>
            <input
              id="timeseries-subreddit"
              className="press-input w-full"
              placeholder="e.g. worldnews or r/worldnews"
              value={subredditInput}
              onChange={(event) => setSubredditInput(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="timeseries-from-date" className="data-label block mb-1">From date</label>
            <input
              id="timeseries-from-date"
              type="date"
              className="press-input w-full"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="timeseries-to-date" className="data-label block mb-1">To date</label>
            <input
              id="timeseries-to-date"
              type="date"
              className="press-input w-full"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <p className="byline">Text filters apply after 400ms. Date filters apply instantly.</p>
          {hasActiveFilters && (
            <button onClick={clearFilters} className="press-btn press-btn-ghost border-rule">
              Clear filters
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onRetry={() => fetchData(filters)} />
        </div>
      )}

      <div className="press-card press-card-brief mb-6">
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
        <p className="byline mb-3">{DATASET_META[selectedDataset].description}</p>

        <AnalyticsChart
          data={chartData}
          chartType={selectedChartType}
          valueLabel={DATASET_META[selectedDataset].valueLabel}
          isDateAxis={DATASET_META[selectedDataset].isDateAxis}
          isLoading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <div className="press-card press-card-brief">
          <p className="kicker mb-2">Trend Model</p>
          {isLoading ? (
            <LoadingSkeleton lines={2} />
          ) : (
            <>
              <p className="body-text">Direction: <span className="font-semibold text-ink">{trend?.direction ?? "flat"}</span></p>
              <p className="byline">Slope: {trend ? trend.slope.toFixed(3) : "0.000"}</p>
              <p className="byline">R2: {trend ? trend.r2.toFixed(3) : "0.000"}</p>
            </>
          )}
        </div>

        <div className="press-card press-card-brief">
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

        <div className="press-card press-card-brief">
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

        <div className="press-card press-card-brief">
          <p className="kicker mb-2">7-Day Projection</p>
          {isLoading ? (
            <LoadingSkeleton lines={2} />
          ) : (
            <>
              <p className="body-text"><span className="font-semibold text-ink">{projectedNextWeek.length}</span> projected day(s)</p>
              <p className="byline">{projectionHeadline}</p>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-6">
        <div className="press-card press-card-brief">
          <p className="kicker mb-2">Projection Snapshot</p>
          {isLoading ? (
            <LoadingSkeleton lines={5} />
          ) : projectedNextWeek.length === 0 ? (
            <p className="byline">Not enough data to project future values.</p>
          ) : (
            <div className="space-y-2">
              {projectedNextWeek.map((row) => (
                <div key={row.date} className="flex items-center justify-between border-b border-rule pb-1">
                  <span className="data-label">{row.date}</span>
                  <span className="body-text font-semibold text-ink">{row.predicted_count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="press-card press-card-brief">
          <p className="kicker mb-2">Cluster Profiles</p>
          {isLoading ? (
            <LoadingSkeleton lines={5} />
          ) : clusterSummaries.length === 0 ? (
            <p className="byline">Not enough days to compute stable clusters.</p>
          ) : (
            <div className="space-y-2">
              {clusterSummaries.map((cluster) => (
                <div key={cluster.cluster_id} className="border-b border-rule pb-1">
                  <p className="data-label">Cluster {cluster.cluster_id} | {cluster.days} day(s)</p>
                  <p className="byline">
                    Avg count {cluster.avg_count.toFixed(1)} | Avg score {cluster.avg_score.toFixed(2)} | Avg engagement {cluster.avg_engagement.toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mb-6">
        <SectionHeading kicker="AI-Generated Summary" title="Narrative Interpretation" />
        {isSummaryLoading ? (
          <LoadingSkeleton lines={4} />
        ) : summary ? (
          <div className="press-card press-card-brief border-l-4 border-accent">
            <p className="kicker mb-2">Editorial Summary</p>
            <p className="body-text leading-relaxed">{summary}</p>
          </div>
        ) : (
          <p className="byline">No summary available for the current query.</p>
        )}
      </div>

      <div className="press-card press-card-brief">
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
          <div>
            <span className="data-label">Avg posts/day</span>
            <p className="font-playfair text-xl font-black">
              {analytics && analytics.time_series.length > 0
                ? (totalPosts / analytics.time_series.length).toFixed(2)
                : "0.00"}
            </p>
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

      <div className="press-card press-card-brief mt-6">
        <p className="kicker mb-2">Field Guide</p>
        <p className="byline mb-3">Quick definitions for the metrics shown on this page.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {FIELD_HELP.map((item) => (
            <div key={item.field} className="border border-rule px-3 py-2">
              <p className="data-label">{item.field}</p>
              <p className="byline">{item.meaning}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
