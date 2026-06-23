"use client";

import { formatDuration, percentChange } from "@/lib/utils";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { ReactNode } from "react";

interface MetricCardProps {
  title: string;
  value: number;
  format?: "duration" | "number" | "count";
  previousValue?: number;
  icon: ReactNode;
  subtitle?: string;
  delay?: number;
}

/**
 * Animated metric card for the dashboard overview.
 * Shows a metric value with optional trend indicator.
 */
export default function MetricCard({
  title,
  value,
  format = "duration",
  previousValue,
  icon,
  subtitle,
  delay = 0,
}: MetricCardProps) {
  const formattedValue =
    format === "duration"
      ? formatDuration(value)
      : format === "count"
        ? value.toString()
        : value.toFixed(1);

  const change = previousValue ? percentChange(value, previousValue) : null;

  return (
    <div
      className={`glass-card p-6 animate-fade-in-up opacity-0`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: "var(--text-muted)" }}
        >
          {title}
        </span>
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{
            background: "linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(99, 102, 241, 0.05))",
          }}
        >
          {icon}
        </div>
      </div>

      {/* Value */}
      <div className="flex items-end gap-3">
        <span className="text-3xl font-bold tracking-tight gradient-text">
          {formattedValue}
        </span>

        {/* Trend indicator */}
        {change !== null && (
          <div
            className="flex items-center gap-1 text-xs font-medium mb-1 px-2 py-0.5 rounded-full"
            style={{
              color:
                change > 5
                  ? "var(--color-danger)"
                  : change < -5
                    ? "var(--color-success)"
                    : "var(--text-muted)",
              background:
                change > 5
                  ? "rgba(239, 68, 68, 0.1)"
                  : change < -5
                    ? "rgba(16, 185, 129, 0.1)"
                    : "rgba(96, 96, 128, 0.1)",
            }}
          >
            {change > 5 ? (
              <TrendingUp size={12} />
            ) : change < -5 ? (
              <TrendingDown size={12} />
            ) : (
              <Minus size={12} />
            )}
            {Math.abs(change).toFixed(0)}%
          </div>
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}
