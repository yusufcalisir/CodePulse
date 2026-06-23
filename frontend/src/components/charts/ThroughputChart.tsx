"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { shortWeek } from "@/lib/utils";
import type { ThroughputWeek } from "@/types";

interface ThroughputChartProps {
  data: ThroughputWeek[];
  title?: string;
}

/**
 * Stacked bar chart showing weekly opened vs merged PRs.
 */
export default function ThroughputChart({
  data,
  title = "Weekly Throughput",
}: ThroughputChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    week: shortWeek(d.week),
  }));

  return (
    <div className="glass-card p-6">
      <h3
        className="text-sm font-semibold mb-6 uppercase tracking-wider"
        style={{ color: "var(--text-muted)" }}
      >
        {title}
      </h3>

      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="week"
              tick={{ fontSize: 11, fill: "var(--text-muted)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--text-muted)" }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface-elevated)",
                border: "1px solid var(--surface-border)",
                borderRadius: "10px",
                fontSize: "12px",
                color: "var(--text-primary)",
              }}
              labelFormatter={(label) => `Week ${label}`}
            />
            <Legend
              wrapperStyle={{ fontSize: "11px", color: "var(--text-secondary)" }}
              iconType="circle"
              iconSize={8}
            />
            <Bar
              dataKey="merged"
              name="Merged"
              fill="var(--chart-2)"
              radius={[4, 4, 0, 0]}
              barSize={20}
            />
            <Bar
              dataKey="opened"
              name="Opened"
              fill="var(--chart-1)"
              radius={[4, 4, 0, 0]}
              barSize={20}
              opacity={0.6}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
