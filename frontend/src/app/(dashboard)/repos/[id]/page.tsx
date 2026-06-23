"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Clock, Eye, GitPullRequest } from "lucide-react";
import Link from "next/link";
import MetricCard from "@/components/ui/MetricCard";
import CycleTimeChart from "@/components/charts/CycleTimeChart";
import ThroughputChart from "@/components/charts/ThroughputChart";
import ReviewLatencyChart from "@/components/charts/ReviewLatencyChart";
import type { OverviewResponse, ContributorMetric } from "@/types";

// ── Mock data ──
const MOCK_OVERVIEW: OverviewResponse = {
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
};

const MOCK_REVIEWERS: ContributorMetric[] = [
  { author: "alice", avg: 1.2, count: 28 },
  { author: "bob", avg: 2.8, count: 22 },
  { author: "charlie", avg: 4.5, count: 15 },
  { author: "diana", avg: 6.1, count: 12 },
  { author: "eve", avg: 8.3, count: 8 },
];

/**
 * Repository detail page — detailed metrics for a single repo.
 */
export default function RepoDetailPage() {
  const params = useParams();
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [reviewers, setReviewers] = useState<ContributorMetric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Replace with real API calls
    const timer = setTimeout(() => {
      setOverview(MOCK_OVERVIEW);
      setReviewers(MOCK_REVIEWERS);
      setLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, [params.id]);

  if (loading || !overview) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="loading-shimmer h-8 w-64 mb-8" />
        <div className="grid grid-cols-3 gap-5 mb-8">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="loading-shimmer h-[140px]" />
          ))}
        </div>
        <div className="loading-shimmer h-[340px]" />
      </div>
    );
  }

  const { metrics } = overview;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link
          href="/repos"
          className="p-2 rounded-lg transition-colors"
          style={{ color: "var(--text-muted)" }}
        >
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            codepulse/frontend
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
            Repository detail — last 30 days
          </p>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
        <MetricCard
          title="Cycle Time"
          value={metrics.cycle_time.median}
          format="duration"
          icon={<Clock size={18} style={{ color: "var(--color-brand-400)" }} />}
          subtitle={`p90: ${metrics.cycle_time.p90.toFixed(1)}h`}
          delay={0}
        />
        <MetricCard
          title="Review Latency"
          value={metrics.review_latency.median}
          format="duration"
          icon={<Eye size={18} style={{ color: "var(--color-brand-400)" }} />}
          subtitle={`p90: ${metrics.review_latency.p90.toFixed(1)}h`}
          delay={100}
        />
        <MetricCard
          title="WIP / Throughput"
          value={metrics.wip}
          format="count"
          icon={
            <GitPullRequest size={18} style={{ color: "var(--color-brand-400)" }} />
          }
          subtitle={`${metrics.throughput_avg_4_week}/week avg throughput`}
          delay={200}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
        <CycleTimeChart data={overview.cycle_time_trend} />
        <ThroughputChart data={overview.throughput_trend} />
      </div>

      {/* Reviewer Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ReviewLatencyChart data={reviewers} />

        {/* Contributor Table */}
        <div className="glass-card p-6">
          <h3
            className="text-sm font-semibold mb-6 uppercase tracking-wider"
            style={{ color: "var(--text-muted)" }}
          >
            Contributor Breakdown
          </h3>
          <table className="w-full">
            <thead>
              <tr
                className="text-xs uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                <th className="text-left pb-3 font-medium">Reviewer</th>
                <th className="text-right pb-3 font-medium">Avg Latency</th>
                <th className="text-right pb-3 font-medium">Reviews</th>
                <th className="text-right pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {reviewers.map((r) => (
                <tr
                  key={r.author}
                  className="border-t"
                  style={{ borderColor: "var(--surface-border)" }}
                >
                  <td className="py-3 text-sm font-medium">{r.author}</td>
                  <td
                    className="py-3 text-sm text-right"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {r.avg.toFixed(1)}h
                  </td>
                  <td
                    className="py-3 text-sm text-right"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {r.count}
                  </td>
                  <td className="py-3 text-right">
                    <span
                      className="text-xs font-medium px-2 py-1 rounded-full"
                      style={{
                        color:
                          r.avg < 3
                            ? "var(--color-success)"
                            : r.avg < 6
                              ? "var(--color-warning)"
                              : "var(--color-danger)",
                        background:
                          r.avg < 3
                            ? "rgba(16, 185, 129, 0.1)"
                            : r.avg < 6
                              ? "rgba(245, 158, 11, 0.1)"
                              : "rgba(239, 68, 68, 0.1)",
                      }}
                    >
                      {r.avg < 3 ? "Fast" : r.avg < 6 ? "Moderate" : "Slow"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
