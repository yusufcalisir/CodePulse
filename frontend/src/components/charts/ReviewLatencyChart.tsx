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
import { formatDuration } from "@/lib/utils";
import type { ContributorMetric } from "@/types";

interface ReviewLatencyChartProps {
  data: ContributorMetric[];
  title?: string;
}

/**
 * Horizontal bar chart showing review latency per contributor.
 */
export default function ReviewLatencyChart({
  data,
  title = "Review Latency by Reviewer",
}: ReviewLatencyChartProps) {
  // Sort by avg ascending (fastest first) and take top 10
  const chartData = [...data]
    .sort((a, b) => a.avg - b.avg)
    .slice(0, 10)
    .map((d) => ({
      author: d.author,
      avg: d.avg,
      count: d.count,
    }));

  return (
    <div className="glass-card p-6">
      <h3
        className="text-sm font-semibold mb-6 uppercase tracking-wider"
        style={{ color: "var(--text-muted)" }}
      >
        {title}
      </h3>

      <div style={{ height: Math.max(200, chartData.length * 40) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: "var(--text-muted)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => formatDuration(v)}
            />
            <YAxis
              type="category"
              dataKey="author"
              tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
              axisLine={false}
              tickLine={false}
              width={100}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface-elevated)",
                border: "1px solid var(--surface-border)",
                borderRadius: "10px",
                fontSize: "12px",
                color: "var(--text-primary)",
              }}
              formatter={(value, _name, props) => [
                `${formatDuration(Number(value))} avg (${(props as any).payload.count} reviews)`,
                "Latency",
              ]}
            />
            <Bar
              dataKey="avg"
              fill="var(--chart-3)"
              radius={[0, 6, 6, 0]}
              barSize={18}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
