"use client";

import { useState, useEffect } from "react";
import { 
  Clock, 
  Eye, 
  GitPullRequest, 
  BarChart3, 
  Terminal, 
  AlertTriangle, 
  AlertCircle, 
  TrendingUp, 
  CheckCircle2, 
  ShieldAlert, 
  Activity, 
  ChevronDown, 
  ChevronUp, 
  GitMerge,
  Send,
  Sliders
} from "lucide-react";
import MetricCard from "@/components/ui/MetricCard";
import CycleTimeChart from "@/components/charts/CycleTimeChart";
import ThroughputChart from "@/components/charts/ThroughputChart";
import { getRepositories, getOverview, getAnomalies, getInsights } from "@/lib/api";
import type { Repository, OverviewResponse, Anomaly, InsightsResponse } from "@/types";

// Fallbacks for offline/no-repo mode
const FALLBACK_REPOS: Repository[] = [
  {
    id: 1,
    github_id: 123456,
    name: "frontend",
    full_name: "codepulse/frontend",
    org: "codepulse",
    default_branch: "main",
    synced_at: "2026-06-23T14:30:00Z",
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-23T14:30:00Z",
  },
  {
    id: 2,
    github_id: 234567,
    name: "api",
    full_name: "codepulse/api",
    org: "codepulse",
    default_branch: "main",
    synced_at: "2026-06-23T12:00:00Z",
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-23T12:00:00Z",
  }
];

const FALLBACK_OVERVIEW: Record<number, OverviewResponse> = {
  1: {
    metrics: {
      cycle_time: { avg: 18.5, median: 12.3, p90: 42.1, unit: "hours" },
      review_latency: { avg: 4.2, median: 2.1, p90: 12.0, unit: "hours" },
      wip: 7,
      throughput_current_week: 12,
      throughput_avg_4_week: 15.5,
      period: "last_30_days",
    },
    cycle_time_trend: [
      { week: "2026-W17", value: 22.4, count: 8 },
      { week: "2026-W18", value: 19.1, count: 11 },
      { week: "2026-W19", value: 16.2, count: 9 },
      { week: "2026-W20", value: 14.8, count: 13 },
      { week: "2026-W21", value: 18.5, count: 10 },
      { week: "2026-W22", value: 12.3, count: 14 },
      { week: "2026-W23", value: 11.2, count: 12 },
      { week: "2026-W24", value: 13.7, count: 15 },
    ],
    throughput_trend: [
      { week: "2026-W17", merged: 8, opened: 11 },
      { week: "2026-W18", merged: 11, opened: 14 },
      { week: "2026-W19", merged: 9, opened: 10 },
      { week: "2026-W20", merged: 13, opened: 15 },
      { week: "2026-W21", merged: 10, opened: 12 },
      { week: "2026-W22", merged: 14, opened: 16 },
      { week: "2026-W23", merged: 12, opened: 13 },
      { week: "2026-W24", merged: 15, opened: 17 },
    ],
  },
  2: {
    metrics: {
      cycle_time: { avg: 14.2, median: 10.8, p90: 36.5, unit: "hours" },
      review_latency: { avg: 3.6, median: 1.8, p90: 10.2, unit: "hours" },
      wip: 4,
      throughput_current_week: 8,
      throughput_avg_4_week: 10.5,
      period: "last_30_days",
    },
    cycle_time_trend: [
      { week: "2026-W17", value: 18.2, count: 5 },
      { week: "2026-W18", value: 15.4, count: 7 },
      { week: "2026-W19", value: 12.8, count: 6 },
      { week: "2026-W20", value: 11.2, count: 9 },
      { week: "2026-W21", value: 14.6, count: 7 },
      { week: "2026-W22", value: 10.1, count: 10 },
      { week: "2026-W23", value: 9.8, count: 8 },
      { week: "2026-W24", value: 10.8, count: 11 },
    ],
    throughput_trend: [
      { week: "2026-W17", merged: 5, opened: 7 },
      { week: "2026-W18", merged: 7, opened: 9 },
      { week: "2026-W19", merged: 6, opened: 7 },
      { week: "2026-W20", merged: 9, opened: 11 },
      { week: "2026-W21", merged: 7, opened: 8 },
      { week: "2026-W22", merged: 10, opened: 12 },
      { week: "2026-W23", merged: 8, opened: 9 },
      { week: "2026-W24", merged: 11, opened: 13 },
    ],
  }
};

const FALLBACK_ANOMALIES: Record<number, Anomaly[]> = {
  1: [
    {
      type: "reviewer_bottleneck",
      title: "Review Bottleneck on @bob",
      description: "@bob handled 60% of all code reviews. This creates high bus factor risk and delays pull requests.",
      severity: "high",
      author: "bob",
      value: 60
    },
    {
      type: "high_wip",
      title: "Work in Progress Overload",
      description: "7 open PRs vs 15.5/week throughput. Team is starting new branches faster than finishing current work.",
      severity: "medium",
      value: 7
    },
    {
      type: "pr_size_anomaly",
      title: "PR Size Exception: PR #102",
      description: "PR #102 contains 620 lines changed. Large changes decrease code review quality and increase defect rate.",
      severity: "medium",
      pr_number: 102,
      author: "alice",
      value: 620
    }
  ],
  2: [
    {
      type: "reviewer_bottleneck",
      title: "Review Bottleneck on @alice",
      description: "@alice handled 55% of all code reviews. Adjust assignments to balance the code quality verification workload.",
      severity: "high",
      author: "alice",
      value: 55
    },
    {
      type: "high_wip",
      title: "WIP Limit warning",
      description: "4 open PRs vs 10.5/week average throughput. Keep checking pull request queues to sustain optimal flow.",
      severity: "low",
      value: 4
    }
  ]
};

const FALLBACK_INSIGHTS: Record<number, InsightsResponse> = {
  1: {
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
        type: "bottleneck",
        title: "High Work in Progress",
        description: "7 open PRs vs 15.5/week throughput. WIP exceeds recommended ratio.",
        severity: "medium",
        metric: "high_wip",
        meta: { value: 7 }
      }
    ],
    statistical_layer: [
      {
        type: "trend_deviation",
        title: "Review Latency Increased 42%",
        description: "Time to first review increased 42% over the last week (2.1h → 3.0h). Delivery pipeline is starting to clog.",
        metric: "review_latency",
        change_pct: 42,
        severity: "medium"
      },
      {
        type: "trend_deviation",
        title: "Cycle Time Improving",
        description: "PR cycle time decreased 26% over the last 2 weeks (16.7h → 12.5h). Core completions are accelerating.",
        metric: "cycle_time",
        change_pct: -26,
        severity: "low"
      }
    ],
    llm_layer: {
      executive_summary: "Command Center logs indicate review gridlock on @bob and a 42% spike in review latency. However, overall cycle time has decreased 26%, showing active completions.",
      why_did_this_happen: "The increase in review latency is caused by review queue pileups. Suggested action: establish review SLAs, re-allocate PR reviews to other engineers, and set WIP limit."
    }
  },
  2: {
    rule_engine: [
      {
        type: "bottleneck",
        title: "Review Bottleneck: @alice",
        description: "@alice performed 15 reviews, which is 55% of all reviews.",
        severity: "high",
        metric: "reviewer_bottleneck",
        meta: { author: "alice", value: 55 }
      }
    ],
    statistical_layer: [
      {
        type: "trend_deviation",
        title: "Cycle Time Stable",
        description: "Cycle time remains within optimal boundary lines at 10.8h median.",
        metric: "cycle_time",
        change_pct: 0,
        severity: "low"
      }
    ],
    llm_layer: {
      executive_summary: "The project shows stable cycle times, but review distribution is highly concentrated on @alice.",
      why_did_this_happen: "@alice is reviews coordinator. Suggested action: distribute reviews to @bob and @charlie."
    }
  }
};

function getSuggestedAction(anomaly: Anomaly | any, metric = ""): string {
  const type = anomaly.type || anomaly.metric || "";
  if (type === "reviewer_bottleneck" || type === "bottleneck") {
    const name = anomaly.author || anomaly.meta?.author || "primary reviewer";
    return `Re-route pending pull requests to other team members, establish review rotations, or increase team review bandwidth to relieve @${name}.`;
  }
  if (type === "high_wip" || anomaly.title?.toLowerCase().includes("work in progress")) {
    return "Establish a strict WIP limit (maximum 3 open PRs per developer). Pause starting new branch tasks and prioritize merging active PRs.";
  }
  if (anomaly.title?.toLowerCase().includes("review latency") || metric === "review_latency") {
    return "Enforce review SLAs (e.g. <2 hours for first review). Configure Slack notification alerts for open PR queues.";
  }
  if (type === "pr_size_anomaly" || type === "anomaly" || anomaly.title?.toLowerCase().includes("pr size")) {
    const prNum = anomaly.pr_number || anomaly.meta?.pr_number || "102";
    return `Establish automated PR size warnings in CI. Break PR #${prNum} into smaller, logically-independent modules (<200 lines) for safer review.`;
  }
  return "Review active bottleneck metrics, sync with the assignee to clear blockers, and coordinate pair-programming reviews.";
}

/**
 * Command Center page — Overview HUD, problem actions console, and collapsible telemetry.
 */
export default function DashboardPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null);
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTelemetry, setShowTelemetry] = useState(false);
  const [dismissedAlerts, setDismissedAlerts] = useState<string[]>([]);
  const [actionStatus, setActionStatus] = useState<Record<string, string>>({});

  useEffect(() => {
    async function loadInitialData() {
      try {
        const fetchedRepos = await getRepositories();
        setRepos(fetchedRepos);
        if (fetchedRepos.length > 0) {
          setSelectedRepoId(fetchedRepos[0].id);
        } else {
          setRepos(FALLBACK_REPOS);
          setSelectedRepoId(FALLBACK_REPOS[0].id);
        }
      } catch (err) {
        console.warn("Failed to load real repositories, falling back to mock:", err);
        setRepos(FALLBACK_REPOS);
        setSelectedRepoId(FALLBACK_REPOS[0].id);
      }
    }
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedRepoId === null) return;
    const repoId = selectedRepoId;
    
    async function loadRepoData() {
      setLoading(true);
      try {
        const [overviewData, anomaliesData, insightsData] = await Promise.all([
          getOverview(repoId),
          getAnomalies(repoId),
          getInsights(repoId)
        ]);

        setOverview(overviewData);
        setAnomalies(anomaliesData || []);
        setInsights(insightsData);
      } catch (err) {
        console.warn(`Failed to load data for repo ${repoId}, falling back to mock:`, err);
        const fallbackId = FALLBACK_OVERVIEW[repoId] ? repoId : 1;
        setOverview(FALLBACK_OVERVIEW[fallbackId]);
        setAnomalies(FALLBACK_ANOMALIES[fallbackId] || []);
        setInsights(FALLBACK_INSIGHTS[fallbackId]);
      } finally {
        setLoading(false);
      }
    }
    loadRepoData();
  }, [selectedRepoId]);

  if (loading || !overview) {
    return <DashboardSkeleton />;
  }

  const selectedRepo = repos.find(r => r.id === selectedRepoId) || repos[0];
  
  // Aggregate anomalies from rules as well to construct a comprehensive action feed
  const combinedAlerts: Anomaly[] = [...anomalies];
  if (insights && insights.rule_engine) {
    insights.rule_engine.forEach(rule => {
      // Avoid duplicates
      if (!combinedAlerts.some(a => a.title === rule.title)) {
        combinedAlerts.push({
          type: rule.type === "bottleneck" ? "reviewer_bottleneck" : "pr_size_anomaly",
          title: rule.title,
          description: rule.description,
          severity: rule.severity,
          value: rule.meta?.value || 0,
          author: rule.meta?.author || null,
          pr_number: rule.meta?.pr_number || null
        });
      }
    });
  }

  // Add latency trends as alert triggers if they are high
  if (insights && insights.statistical_layer) {
    insights.statistical_layer.forEach(stat => {
      if (stat.severity === "high" || stat.severity === "medium") {
        if (!combinedAlerts.some(a => a.title === stat.title)) {
          combinedAlerts.push({
            type: "cycle_time_spike",
            title: stat.title,
            description: stat.description,
            severity: stat.severity,
            value: stat.change_pct || 0
          });
        }
      }
    });
  }

  const activeAlerts = combinedAlerts.filter(a => !dismissedAlerts.includes(a.title));
  const { metrics } = overview;

  const triggerAction = (alertTitle: string, actionType: string) => {
    setActionStatus(prev => ({
      ...prev,
      [alertTitle]: actionType === "slack" ? "Slack Alert Sent!" : "Limit Applied!"
    }));
    setTimeout(() => {
      setActionStatus(prev => {
        const copy = { ...prev };
        delete copy[alertTitle];
        return copy;
      });
    }, 3000);
  };

  const dismissAlert = (alertTitle: string) => {
    setDismissedAlerts(prev => [...prev, alertTitle]);
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center animate-pulse-glow"
            style={{
              background: "linear-gradient(135deg, var(--color-brand-600), var(--color-brand-500))",
            }}
          >
            <Terminal size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Command Center</h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
              Active problems, process alerts, and workflow action recommendations
            </p>
          </div>
        </div>

        {/* Repo Selector Dropdown */}
        <div className="relative shrink-0 select-container">
          <select
            value={selectedRepoId || ""}
            onChange={(e) => setSelectedRepoId(Number(e.target.value))}
            className="appearance-none pr-10 pl-4 py-2.5 rounded-xl text-sm font-semibold outline-none border transition-all duration-200 cursor-pointer bg-clip-padding"
            style={{
              background: "var(--surface-card)",
              borderColor: "var(--surface-border)",
              color: "var(--text-primary)",
              boxShadow: "0 2px 10px rgba(0,0,0,0.2)"
            }}
            id="repo-select"
          >
            {repos.map((repo) => (
              <option key={repo.id} value={repo.id}>
                {repo.full_name}
              </option>
            ))}
          </select>
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: "var(--text-muted)" }}>
            <ChevronDown size={16} />
          </div>
        </div>
      </div>

      {/* HUD System Status Console */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="glass-card p-4 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-semibold tracking-wider block" style={{ color: "var(--text-muted)" }}>
              Workflow Alerts
            </span>
            <span className={`text-lg font-bold block mt-1 ${activeAlerts.length > 0 ? "text-red-400" : "text-emerald-400"}`}>
              {activeAlerts.length} Active
            </span>
          </div>
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-red-500/10">
            <ShieldAlert size={16} className={activeAlerts.length > 0 ? "text-red-400" : "text-emerald-400"} />
          </div>
        </div>
        <div className="glass-card p-4 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-semibold tracking-wider block" style={{ color: "var(--text-muted)" }}>
              Review Latency
            </span>
            <span className="text-lg font-bold block mt-1">
              {metrics.review_latency.median.toFixed(1)}h
            </span>
          </div>
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-indigo-500/10">
            <Clock size={16} style={{ color: "var(--color-brand-400)" }} />
          </div>
        </div>
        <div className="glass-card p-4 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-semibold tracking-wider block" style={{ color: "var(--text-muted)" }}>
              Queue Pressure
            </span>
            <span className={`text-lg font-bold block mt-1 ${metrics.wip > metrics.throughput_avg_4_week * 0.7 ? "text-amber-400" : "text-emerald-400"}`}>
              WIP {metrics.wip} / T {metrics.throughput_avg_4_week.toFixed(0)}
            </span>
          </div>
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-amber-500/10">
            <GitPullRequest size={16} className="text-amber-400" />
          </div>
        </div>
        <div className="glass-card p-4 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-semibold tracking-wider block" style={{ color: "var(--text-muted)" }}>
              Throughput
            </span>
            <span className="text-lg font-bold block mt-1">
              {metrics.throughput_current_week} Merges
            </span>
          </div>
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-emerald-500/10">
            <GitMerge size={16} className="text-emerald-400" />
          </div>
        </div>
      </div>

      {/* Main Console Board */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={18} style={{ color: "var(--color-brand-400)" }} />
          <h2 className="text-base font-semibold">Active Engineering Alerts & Action Items</h2>
          <span className="text-xs px-2 py-0.5 rounded-full font-bold uppercase" style={{ background: "rgba(239, 68, 68, 0.1)", color: "var(--color-danger)" }}>
            PR Flow Warnings
          </span>
        </div>

        {activeAlerts.length === 0 ? (
          <div className="glass-card p-10 text-center flex flex-col items-center justify-center max-w-3xl mx-auto">
            <CheckCircle2 size={40} className="text-emerald-400 mb-3" />
            <h3 className="text-md font-bold mb-1 text-white">All Channels Clear</h3>
            <p className="text-xs max-w-sm" style={{ color: "var(--text-secondary)" }}>
              No process bottlenecks, queue pressure, or code review bottlenecks detected on {selectedRepo.full_name}.
            </p>
          </div>
        ) : (
          <div className="grid gap-5">
            {activeAlerts.map((alert, idx) => {
              const borderLeftColor =
                alert.severity === "high"
                  ? "var(--color-danger)"
                  : alert.severity === "medium"
                    ? "var(--color-warning)"
                    : "var(--color-brand-400)";
              const pillBg =
                alert.severity === "high"
                  ? "rgba(239, 68, 68, 0.1)"
                  : alert.severity === "medium"
                    ? "rgba(245, 158, 11, 0.1)"
                    : "rgba(99, 102, 241, 0.1)";
              const pillColor =
                alert.severity === "high"
                  ? "var(--color-danger)"
                  : alert.severity === "medium"
                    ? "var(--color-warning)"
                    : "var(--color-brand-400)";

              return (
                <div
                  key={alert.title}
                  className="glass-card p-6 border-l-4 relative overflow-hidden animate-fade-in-up"
                  style={{
                    borderLeftColor: borderLeftColor,
                    animationDelay: `${idx * 80}ms`
                  }}
                  id={`alert-card-${idx}`}
                >
                  <div className="absolute -top-12 -right-12 w-32 h-32 rounded-full bg-indigo-500/5 blur-2xl pointer-events-none" />

                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex items-center gap-2.5">
                      {alert.severity === "high" ? (
                        <AlertCircle size={18} className="text-red-400 shrink-0" />
                      ) : (
                        <AlertTriangle size={18} className="text-amber-400 shrink-0" />
                      )}
                      <h3 className="font-bold text-base text-white">{alert.title}</h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider"
                        style={{ background: pillBg, color: pillColor }}
                      >
                        {alert.severity}
                      </span>
                      <button
                        onClick={() => dismissAlert(alert.title)}
                        className="text-xs transition-colors hover:text-white cursor-pointer"
                        style={{ color: "var(--text-muted)" }}
                      >
                        Mute
                      </button>
                    </div>
                  </div>

                  <p className="text-sm mb-4 leading-relaxed max-w-4xl font-normal" style={{ color: "var(--text-secondary)" }}>
                    {alert.description}
                  </p>

                  {/* Suggested Action Box */}
                  <div
                    className="p-4 rounded-xl mb-4 border"
                    style={{
                      background: "rgba(18, 18, 30, 0.5)",
                      borderColor: "rgba(99, 102, 241, 0.15)"
                    }}
                  >
                    <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-400 block mb-1">
                      Suggested Action
                    </span>
                    <p className="text-xs leading-relaxed text-white font-medium">
                      {getSuggestedAction(alert)}
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      onClick={() => triggerAction(alert.title, "apply")}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
                      id={`action-primary-${idx}`}
                    >
                      <Sliders size={13} />
                      {alert.type === "reviewer_bottleneck" ? "Balance Reviews" : alert.type === "high_wip" ? "Apply WIP Limit" : "Resolve Issues"}
                    </button>
                    <button
                      onClick={() => triggerAction(alert.title, "slack")}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 hover:scale-105 cursor-pointer"
                      style={{ background: "var(--surface-hover)", color: "var(--text-secondary)", border: "1px solid var(--surface-border)" }}
                      id={`action-secondary-${idx}`}
                    >
                      <Send size={13} />
                      Notify Slack
                    </button>
                    {actionStatus[alert.title] && (
                      <span className="text-xs font-medium text-emerald-400 animate-pulse ml-2">
                        {actionStatus[alert.title]}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Supporting Telemetry & Historical Trends (Collapsible) */}
      <div className="mt-8">
        <button
          onClick={() => setShowTelemetry(!showTelemetry)}
          className="w-full flex items-center justify-between p-5 rounded-2xl glass-card transition-all duration-200 cursor-pointer text-left"
          style={{ background: "var(--surface-card)" }}
          id="telemetry-accordion-btn"
        >
          <div className="flex items-center gap-2">
            <BarChart3 size={18} style={{ color: "var(--color-brand-400)" }} />
            <span className="text-sm font-semibold text-white">
              Supporting Telemetry & Historical Trends
            </span>
            <span className="text-xs opacity-60">
              (Metric Cards & Charts)
            </span>
          </div>
          <div>
            {showTelemetry ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </div>
        </button>

        {showTelemetry && (
          <div className="mt-6 space-y-8 animate-fade-in-up" id="telemetry-content">
            {/* Metric Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <MetricCard
                title="Cycle Time"
                value={metrics.cycle_time.median}
                format="duration"
                icon={<Clock size={18} style={{ color: "var(--color-brand-400)" }} />}
                subtitle={`avg ${metrics.cycle_time.avg.toFixed(1)}h · p90 ${metrics.cycle_time.p90.toFixed(1)}h`}
                delay={0}
              />
              <MetricCard
                title="Review Latency"
                value={metrics.review_latency.median}
                format="duration"
                icon={<Eye size={18} style={{ color: "var(--color-brand-400)" }} />}
                subtitle={`avg ${metrics.review_latency.avg.toFixed(1)}h · p90 ${metrics.review_latency.p90.toFixed(1)}h`}
                delay={100}
              />
              <MetricCard
                title="Work in Progress"
                value={metrics.wip}
                format="count"
                icon={<GitPullRequest size={18} style={{ color: "var(--color-brand-400)" }} />}
                subtitle="Open pull requests"
                delay={200}
              />
              <MetricCard
                title="Throughput"
                value={metrics.throughput_current_week}
                format="count"
                icon={<BarChart3 size={18} style={{ color: "var(--color-brand-400)" }} />}
                subtitle={`${metrics.throughput_avg_4_week}/week rolling avg`}
                delay={300}
              />
            </div>

            {/* Sparkline Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <CycleTimeChart data={overview.cycle_time_trend} />
              <ThroughputChart data={overview.throughput_trend} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-8">
        <div>
          <div className="loading-shimmer h-8 w-48 mb-2" />
          <div className="loading-shimmer h-4 w-72" />
        </div>
        <div className="loading-shimmer h-10 w-40" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="loading-shimmer h-20" />
        ))}
      </div>
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="loading-shimmer h-48 w-full" />
        ))}
      </div>
    </div>
  );
}

