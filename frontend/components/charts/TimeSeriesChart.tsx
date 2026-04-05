"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Brush,
} from "recharts";
import { TimeSeriesPoint } from "@/types";
import { formatDate } from "@/lib/utils";
import EmptyState from "@/components/ui/EmptyState";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

interface TimeSeriesChartProps {
  data: TimeSeriesPoint[];
  isLoading?: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="press-card press-card-brief px-3 py-2 text-xs shadow-sm">
      <p className="byline mb-1">{formatDate(label)}</p>
      <p className="font-semibold text-ink">{payload[0]?.value} posts</p>
      {payload[1] && (
        <p className="text-muted">Avg score: {payload[1]?.value?.toFixed(1)}</p>
      )}
    </div>
  );
}

export default function TimeSeriesChart({ data, isLoading }: TimeSeriesChartProps) {
  if (isLoading) return <LoadingSkeleton variant="chart" />;
  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No data for this query"
        description="Try different search terms, date ranges, or subreddits."
      />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={340}>
      <AreaChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#C41E1E" stopOpacity={0.18} />
            <stop offset="95%" stopColor="#C41E1E" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6B6860" stopOpacity={0.12} />
            <stop offset="95%" stopColor="#6B6860" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#D4CFC6" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={(v) => {
            const d = new Date(v);
            return d.toLocaleDateString("en-GB", { month: "short", day: "numeric" });
          }}
          tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
          axisLine={{ stroke: "#D4CFC6" }}
          tickLine={false}
        />
        <YAxis
          yAxisId="count"
          tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
          axisLine={false}
          tickLine={false}
          width={38}
        />
        <YAxis
          yAxisId="score"
          orientation="right"
          tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
          axisLine={false}
          tickLine={false}
          width={38}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          yAxisId="count"
          type="monotone"
          dataKey="count"
          stroke="#C41E1E"
          strokeWidth={2}
          fill="url(#colorCount)"
        />
        <Area
          yAxisId="score"
          type="monotone"
          dataKey="avg_score"
          stroke="#6B6860"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          fill="url(#colorScore)"
        />
        <Brush
          dataKey="date"
          height={24}
          stroke="#D4CFC6"
          fill="#EFE8DC"
          travellerWidth={6}
          tickFormatter={(v) =>
            new Date(v).toLocaleDateString("en-GB", { month: "short", day: "numeric" })
          }
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
