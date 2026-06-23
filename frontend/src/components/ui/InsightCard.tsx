"use client";

import type { Insight } from "@/types";
import { AlertTriangle, Info, CheckCircle } from "lucide-react";

interface InsightCardProps {
  insight: Insight;
}

const iconMap = {
  warning: <AlertTriangle size={18} style={{ color: "var(--color-warning)" }} />,
  info: <Info size={18} style={{ color: "var(--chart-5)" }} />,
  success: <CheckCircle size={18} style={{ color: "var(--color-success)" }} />,
};

const borderColorMap = {
  warning: "rgba(245, 158, 11, 0.3)",
  info: "rgba(96, 165, 250, 0.3)",
  success: "rgba(16, 185, 129, 0.3)",
};

/**
 * Displays an AI-generated insight as a styled card.
 */
export default function InsightCard({ insight }: InsightCardProps) {
  return (
    <div
      className="glass-card p-5 flex gap-4"
      style={{ borderLeftWidth: "3px", borderLeftColor: borderColorMap[insight.type] }}
    >
      <div className="mt-0.5 shrink-0">{iconMap[insight.type]}</div>
      <div>
        <h4 className="text-sm font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
          {insight.title}
        </h4>
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {insight.description}
        </p>
        <span
          className="inline-block mt-2 text-[10px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full"
          style={{
            color: "var(--text-muted)",
            background: "var(--surface-hover)",
          }}
        >
          {insight.metric.replace("_", " ")}
        </span>
      </div>
    </div>
  );
}
