"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import EmptyState from "@/components/ui/EmptyState";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import { formatDate } from "@/lib/utils";

const COLORS = ["#C41E1E", "#2563EB", "#16A34A", "#D97706", "#0891B2", "#7C3AED", "#DB2777", "#65A30D"];

export type AnalyticsChartType = "line" | "bar" | "pie";

export interface AnalyticsDatum {
  label: string;
  value: number;
}

interface AnalyticsChartProps {
  data: AnalyticsDatum[];
  chartType: AnalyticsChartType;
  valueLabel?: string;
  isLoading?: boolean;
  isDateAxis?: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="press-card text-xs py-2 px-3 shadow-md">
      <p className="byline mb-1">{label}</p>
      <p className="font-semibold text-ink">{payload[0]?.value}</p>
    </div>
  );
}

export default function AnalyticsChart({
  data,
  chartType,
  valueLabel = "Value",
  isLoading,
  isDateAxis,
}: AnalyticsChartProps) {
  if (isLoading) return <LoadingSkeleton variant="chart" />;
  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No analytics data"
        description="Try changing the query or date range to populate this view."
      />
    );
  }

  if (chartType === "pie") {
    return (
      <ResponsiveContainer width="100%" height={360}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            cx="42%"
            cy="50%"
            outerRadius={120}
            innerRadius={60}
            paddingAngle={2}
          >
            {data.map((entry, index) => (
              <Cell key={entry.label} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "line") {
    return (
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#D4CFC6" vertical={false} />
          <XAxis
            dataKey="label"
            tickFormatter={(value) =>
              isDateAxis ? formatDate(String(value)) : String(value)
            }
            tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
            axisLine={{ stroke: "#D4CFC6" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip content={<ChartTooltip />} />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            name={valueLabel}
            stroke="#C41E1E"
            strokeWidth={2}
            dot={{ r: 2.5 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#D4CFC6" vertical={false} />
        <XAxis
          dataKey="label"
          tickFormatter={(value) =>
            isDateAxis ? formatDate(String(value)) : String(value)
          }
          tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
          axisLine={{ stroke: "#D4CFC6" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#6B6860", fontFamily: "JetBrains Mono, monospace" }}
          axisLine={false}
          tickLine={false}
          width={44}
        />
        <Tooltip content={<ChartTooltip />} />
        <Legend />
        <Bar dataKey="value" name={valueLabel} fill="#C41E1E" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

