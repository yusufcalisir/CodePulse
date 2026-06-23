"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { shortWeek, formatDuration } from "@/lib/utils";
import type { WeeklyDataPoint } from "@/types";

interface CycleTimeChartProps {
  data: WeeklyDataPoint[];
  title?: string;
}

/**
 * Area chart showing PR cycle time trend over weeks.
 * Uses gradient fill for a premium visual effect.
 */
export default function CycleTimeChart({
  data,
  title = "PR Cycle Time Trend",
}: CycleTimeChartProps) {
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
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="cycleTimeGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
              </linearGradient>
            </defs>
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
              tickFormatter={(v) => formatDuration(v)}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface-elevated)",
                border: "1px solid var(--surface-border)",
                borderRadius: "10px",
                fontSize: "12px",
                color: "var(--text-primary)",
              }}
              formatter={(value) => [formatDuration(Number(value)), "Avg Cycle Time"]}
              labelFormatter={(label) => `Week ${label}`}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--chart-1)"
              strokeWidth={2.5}
              fill="url(#cycleTimeGradient)"
              dot={{ r: 4, fill: "var(--chart-1)", stroke: "var(--surface-card)", strokeWidth: 2 }}
              activeDot={{ r: 6, fill: "var(--chart-1)", stroke: "var(--surface-card)", strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
