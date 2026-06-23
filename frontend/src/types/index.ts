/* ─── TypeScript type definitions for CodePulse ─── */

// ── API Response Types ──────────────────────────────────────

export interface Repository {
  id: number;
  github_id: number;
  name: string;
  full_name: string;
  org: string | null;
  default_branch: string;
  synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RepositoryListResponse {
  repositories: Repository[];
  count: number;
}

export interface SyncStatusResponse {
  sync_id: number;
  repo_id: number;
  status: "running" | "completed" | "failed";
  pr_count: number;
  started_at: string;
  finished_at: string | null;
  error: string | null;
}

// ── Metrics Types ───────────────────────────────────────────

export interface StatSummary {
  avg: number;
  median: number;
  p90: number;
  unit: string;
}

export interface WeeklyDataPoint {
  week: string;
  value: number;
  count?: number;
}

export interface ThroughputWeek {
  week: string;
  merged: number;
  opened: number;
}

export interface ContributorMetric {
  author: string;
  avg: number;
  count: number;
}

export interface CycleTimeResponse {
  summary: StatSummary;
  trend: WeeklyDataPoint[];
  period_days: number;
}

export interface ReviewLatencyResponse {
  summary: StatSummary;
  by_reviewer: ContributorMetric[];
  trend: WeeklyDataPoint[];
  period_days: number;
}

export interface ThroughputResponse {
  weekly: ThroughputWeek[];
  rolling_avg: number;
  period_weeks: number;
}

export interface OverviewMetrics {
  cycle_time: StatSummary;
  review_latency: StatSummary;
  wip: number;
  throughput_current_week: number;
  throughput_avg_4_week: number;
  period: string;
}

export interface OverviewResponse {
  metrics: OverviewMetrics;
  cycle_time_trend: WeeklyDataPoint[];
  throughput_trend: ThroughputWeek[];
}

// ── Insights ────────────────────────────────────────────────

export interface Insight {
  type: "warning" | "info" | "success";
  title: string;
  description: string;
  metric: string;
  severity: "low" | "medium" | "high";
}

export interface RuleEngineInsight {
  type: "bottleneck" | "anomaly";
  title: string;
  description: string;
  severity: "low" | "medium" | "high";
  metric?: string | null;
  meta?: Record<string, any> | null;
}

export interface StatisticalInsight {
  type: "trend_deviation" | "percentile_shift";
  title: string;
  description: string;
  metric: "cycle_time" | "review_latency" | "throughput" | "wip";
  change_pct?: number | null;
  severity: "low" | "medium" | "high";
}

export interface LLMInterpretation {
  why_did_this_happen: string;
  executive_summary: string;
}

export interface InsightsResponse {
  rule_engine: RuleEngineInsight[];
  statistical_layer: StatisticalInsight[];
  llm_layer: LLMInterpretation;
}


// ── Anomalies ───────────────────────────────────────────────

export interface Anomaly {
  type: "cycle_time_spike" | "pr_size_anomaly" | "reviewer_bottleneck" | "high_wip";
  title: string;
  description: string;
  severity: "low" | "medium" | "high";
  pr_number?: number | null;
  author?: string | null;
  value: number;
}
