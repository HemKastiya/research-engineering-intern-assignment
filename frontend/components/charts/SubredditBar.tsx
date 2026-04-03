"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";

interface SubredditBarProps {
  data: { subreddit: string; count: number }[];
  isLoading?: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="press-card text-xs py-2 px-3 shadow-md">
      <p className="font-semibold text-ink">r/{payload[0]?.payload?.subreddit}</p>
      <p className="text-muted">{payload[0]?.value} posts</p>
    </div>
  );
}

export default function SubredditBar({ data, isLoading }: SubredditBarProps) {
  if (isLoading) return <LoadingSkeleton variant="chart" />;
  if (!data || data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#D4CFC6" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
          axisLine={{ stroke: "#D4CFC6" }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="subreddit"
          tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
          axisLine={false}
          tickLine={false}
          width={90}
          tickFormatter={(v) => `r/${v}`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" fill="#EDE9E1" stroke="#D4CFC6" strokeWidth={1} radius={[0, 2, 2, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
