"use client";

import { useState, useEffect } from "react";
import { 
  Sparkles, 
  Layers, 
  TrendingUp, 
  AlertTriangle, 
  AlertCircle, 
  Activity, 
  CheckCircle2, 
  ArrowUpRight, 
  ArrowDownRight,
  BrainCircuit,
  Info
} from "lucide-react";
import { getInsights } from "@/lib/api";
import type { InsightsResponse } from "@/types";

// ── Mock Insights Response for fallback ──
const MOCK_INSIGHTS_RESPONSE: InsightsResponse = {
  rule_engine: [
    {
      type: "bottleneck",
      title: "Review Bottleneck: @bob",
      description: "@bob performed 12 reviews, which is 60% of all reviews in the last 30 days. High bus factor risk.",
      severity: "high",
      metric: "reviewer_bottleneck",
      meta: { author: "bob", value: 60 }
    },
    {
      type: "anomaly",
      title: "PR Size Anomaly: PR #102",
      description: "PR #102 by @alice has 620 lines changed. Large PRs delay code review and increase defect rate.",
      severity: "medium",
      metric: "pr_size_anomaly",
      meta: { author: "alice", pr_number: 102, value: 620 }
    },
    {
      type: "bottleneck",
      title: "High Work in Progress",
      description: "7 open PRs vs 15/week throughput. WIP exceeds recommended ratio. Consider implementing WIP limits to reduce context switching.",
      severity: "medium",
      metric: "high_wip",
      meta: { value: 7 }
    }
  ],
  statistical_layer: [
    {
      type: "trend_deviation",
      title: "Cycle Time Improving",
      description: "PR cycle time decreased 26% over the last 2 weeks (16.7h → 12.5h). The team is iterating faster — keep up the momentum!",
      metric: "cycle_time",
      change_pct: -26,
      severity: "low"
    },
    {
      type: "percentile_shift",
      title: "PR Cycle Time Percentile Shift",
      description: "The p90 cycle time (42.1h) is 3.4x higher than the median (12.3h). This suggests delivery unpredictability due to outlier PR delays.",
      metric: "cycle_time",
      change_pct: 340,
      severity: "medium"
    },
    {
      type: "trend_deviation",
      title: "Throughput Trending Up",
      description: "Weekly merged PR count increased 18% over the last 4 weeks (10.5 → 12.5/week). The team is shipping more consistently.",
      metric: "throughput",
      change_pct: 18,
      severity: "low"
    }
  ],
  llm_layer: {
    executive_summary: "Process telemetry identifies workflow friction points: a severe review distribution bottleneck on @bob and moderate context-switching overhead due to work-in-progress overload. However, overall cycle time has decreased by 26% over the last two weeks, indicating strong positive momentum in core task completion.",
    why_did_this_happen: "The bottleneck is primarily driven by @bob handling 60% of all reviews, creating review queue delays. The WIP shift is driven by 7 concurrent open PRs relative to weekly throughput. Restructure review assignments and enforce smaller PR splits to sustain the recent speed gains."
  }
};

/**
 * Insights and Decision Support page — displays metrics anomalies and recommendations.
 */
export default function InsightsPage() {
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"all" | "llm" | "rules" | "stats">("all");

  useEffect(() => {
    async function loadData() {
      try {
        const insightsData = await getInsights(1);
        if (
          insightsData &&
          (insightsData.rule_engine?.length > 0 ||
            insightsData.statistical_layer?.length > 0 ||
            insightsData.llm_layer?.executive_summary)
        ) {
          setInsights(insightsData);
        } else {
          setInsights(MOCK_INSIGHTS_RESPONSE);
        }
      } catch (err) {
        console.warn("Failed to load real decision support data, falling back to mock:", err);
        setInsights(MOCK_INSIGHTS_RESPONSE);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading || !insights) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="loading-shimmer h-12 w-64 mb-4" />
        <div className="loading-shimmer h-[200px] w-full mb-6" />
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="loading-shimmer h-[150px]" />
          <div className="loading-shimmer h-[150px]" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(99, 102, 241, 0.05))",
            }}
          >
            <BrainCircuit size={20} style={{ color: "var(--color-brand-400)" }} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Decision Support</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
              AI-driven multi-layer reasoning engine and strategic recommendations
            </p>
          </div>
        </div>
      </div>

      {/* Tabs / Filtering */}
      <div className="flex gap-2 mb-8 overflow-x-auto pb-1">
        {[
          { id: "all", label: "All Layers", count: insights.rule_engine.length + insights.statistical_layer.length },
          { id: "llm", label: "Cognitive Summary", count: 1 },
          { id: "rules", label: "Process Rules", count: insights.rule_engine.length },
          { id: "stats", label: "Statistical Analysis", count: insights.statistical_layer.length },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className="px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 whitespace-nowrap"
            style={{
              background:
                activeTab === tab.id
                  ? "linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(99, 102, 241, 0.1))"
                  : "var(--surface-card)",
              color:
                activeTab === tab.id
                  ? "var(--color-brand-400)"
                  : "var(--text-secondary)",
              border: `1px solid ${
                activeTab === tab.id
                  ? "rgba(99, 102, 241, 0.3)"
                  : "var(--surface-border)"
              }`,
            }}
          >
            {tab.label}
            <span className="ml-1.5 opacity-60">({tab.count})</span>
          </button>
        ))}
      </div>

      {/* Layer 3: LLM / Interpretive Layer (Cognitive Core) */}
      {(activeTab === "all" || activeTab === "llm") && (
        <div className="mb-10 animate-fade-in-up opacity-0" style={{ animationDelay: "100ms" }}>
          <div 
            className="glass-card p-6 border relative overflow-hidden"
            style={{
              borderColor: "rgba(99, 102, 241, 0.25)",
              background: "linear-gradient(135deg, rgba(18, 18, 30, 0.95), rgba(26, 26, 46, 0.8))"
            }}
          >
            {/* Subtle neon glowing gradient background */}
            <div className="absolute -top-24 -right-24 w-64 h-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />
            
            <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wider text-indigo-400">
              <Sparkles size={16} className="text-indigo-400 animate-pulse" />
              Layer 3: Interpretive Engine (AI Synthesis)
            </div>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-bold text-white mb-2 leading-snug">Executive Summary</h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {insights.llm_layer.executive_summary}
                </p>
              </div>
              
              <div className="pt-4 border-t" style={{ borderColor: "rgba(255, 255, 255, 0.08)" }}>
                <h4 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
                  Context & Causality ("Why did this happen?")
                </h4>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {insights.llm_layer.why_did_this_happen}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Layer 1: Rule Engine (Deterministic Bottlenecks & Anomalies) */}
      {(activeTab === "all" || activeTab === "rules") && (
        <div className="mb-10 animate-fade-in-up opacity-0" style={{ animationDelay: "200ms" }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2" style={{ color: "var(--text-secondary)" }}>
              <Layers size={15} style={{ color: "var(--color-brand-400)" }} />
              Layer 1: Rule Engine (Bottlenecks & Anomalies)
            </h2>
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              {insights.rule_engine.length} active triggers
            </span>
          </div>
          
          {insights.rule_engine.length === 0 ? (
            <div className="glass-card p-6 text-center text-xs" style={{ color: "var(--text-muted)" }}>
              <CheckCircle2 size={24} className="mx-auto mb-2" style={{ color: "var(--color-success)" }} />
              No process bottlenecks or anomalies detected in the rule engine.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {insights.rule_engine.map((rule, idx) => (
                <div 
                  key={idx}
                  className="glass-card p-5 border-l-4"
                  style={{
                    borderLeftColor: 
                      rule.severity === "high" 
                        ? "var(--color-danger)" 
                        : rule.severity === "medium" 
                          ? "var(--color-warning)" 
                          : "var(--color-brand-400)",
                    background: "var(--surface-card)"
                  }}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2">
                      {rule.type === "bottleneck" ? (
                        <AlertTriangle size={15} style={{ color: "var(--color-warning)" }} />
                      ) : (
                        <AlertCircle size={15} style={{ color: "var(--color-danger)" }} />
                      )}
                      <h3 className="font-semibold text-sm text-white">{rule.title}</h3>
                    </div>
                    <span 
                      className="text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wide"
                      style={{
                        background: 
                          rule.severity === "high" 
                            ? "rgba(239, 68, 68, 0.1)" 
                            : rule.severity === "medium" 
                              ? "rgba(245, 158, 11, 0.1)" 
                              : "rgba(99, 102, 241, 0.1)",
                        color: 
                          rule.severity === "high" 
                            ? "var(--color-danger)" 
                            : rule.severity === "medium" 
                              ? "var(--color-warning)" 
                              : "var(--color-brand-400)"
                      }}
                    >
                      {rule.severity}
                    </span>
                  </div>
                  <p className="text-xs mb-4 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                    {rule.description}
                  </p>
                  <div className="flex items-center justify-between text-[10px]" style={{ color: "var(--text-muted)" }}>
                    <span>Category: <b className="capitalize">{rule.type}</b></span>
                    {rule.meta?.author && (
                      <span>User: <b>@{rule.meta.author}</b></span>
                    )}
                    {rule.meta?.value !== undefined && (
                      <span>Value: <b>{rule.meta.value}{rule.metric === "reviewer_bottleneck" ? "%" : rule.metric === "pr_size_anomaly" ? " lines" : rule.metric === "cycle_time_spike" ? "h" : ""}</b></span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Layer 2: Statistical Layer (Trend Deviations & Percentile Shifts) */}
      {(activeTab === "all" || activeTab === "stats") && (
        <div className="mb-10 animate-fade-in-up opacity-0" style={{ animationDelay: "300ms" }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2" style={{ color: "var(--text-secondary)" }}>
              <TrendingUp size={15} style={{ color: "var(--color-brand-400)" }} />
              Layer 2: Statistical Layer (Time-series Deviations)
            </h2>
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              {insights.statistical_layer.length} observations
            </span>
          </div>
          
          {insights.statistical_layer.length === 0 ? (
            <div className="glass-card p-6 text-center text-xs" style={{ color: "var(--text-muted)" }}>
              <CheckCircle2 size={24} className="mx-auto mb-2" style={{ color: "var(--color-success)" }} />
              No significant statistical trend deviations or percentile shifts detected.
            </div>
          ) : (
            <div className="space-y-4">
              {insights.statistical_layer.map((stat, idx) => {
                const isPositiveChange = stat.severity === "low";
                const hasChangePct = stat.change_pct !== undefined && stat.change_pct !== null;
                
                return (
                  <div 
                    key={idx}
                    className="glass-card p-5 flex items-start gap-4"
                    style={{
                      borderLeftWidth: "3px",
                      borderLeftColor: 
                        stat.severity === "high" 
                          ? "var(--color-danger)" 
                          : stat.severity === "medium" 
                            ? "var(--color-warning)" 
                            : "var(--color-success)"
                    }}
                  >
                    <div className="mt-1 shrink-0">
                      <Activity size={18} style={{ color: isPositiveChange ? "var(--color-success)" : "var(--color-warning)" }} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-3 mb-1">
                        <h3 className="font-semibold text-sm text-white">{stat.title}</h3>
                        
                        {hasChangePct && (
                          <div 
                            className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-lg font-bold"
                            style={{
                              background: isPositiveChange ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                              color: isPositiveChange ? "var(--color-success)" : "var(--color-danger)"
                            }}
                          >
                            {stat.change_pct! > 0 ? (
                              <ArrowUpRight size={14} />
                            ) : (
                              <ArrowDownRight size={14} />
                            )}
                            <span>{Math.abs(stat.change_pct!)}%</span>
                          </div>
                        )}
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                        {stat.description}
                      </p>
                      <div className="flex items-center gap-4 mt-3 text-[10px]" style={{ color: "var(--text-muted)" }}>
                        <span>Metric: <b className="uppercase">{stat.metric.replace("_", " ")}</b></span>
                        <span>Type: <b className="capitalize">{stat.type.replace("_", " ")}</b></span>
                        <span>Severity: <b className="capitalize">{stat.severity}</b></span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
