import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import DashboardPage from "../app/(dashboard)/dashboard/page";
import React from "react";

// Mock Recharts elements since they rely on ResizeObserver and canvas/SVG measuring in jsdom
vi.mock("recharts", () => {
  const DummyChart = ({ children }: any) => <div data-testid="mock-chart">{children}</div>;
  return {
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
    AreaChart: DummyChart,
    Area: () => <div />,
    BarChart: DummyChart,
    Bar: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Legend: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />,
  };
});

// Mock the API client
vi.mock("@/lib/api", () => {
  return {
    getRepositories: vi.fn().mockResolvedValue([
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
      }
    ]),
    getOverview: vi.fn().mockResolvedValue({
      metrics: {
        cycle_time: { avg: 18.5, median: 12.3, p90: 42.1, unit: "hours" },
        review_latency: { avg: 4.2, median: 2.1, p90: 12.0, unit: "hours" },
        wip: 7,
        throughput_current_week: 12,
        throughput_avg_4_week: 15.5,
        period: "last_30_days",
      },
      cycle_time_trend: [],
      throughput_trend: [],
    }),
    getAnomalies: vi.fn().mockResolvedValue([
      {
        type: "reviewer_bottleneck",
        title: "Review Bottleneck on @bob",
        description: "@bob handled 60% of all code reviews.",
        severity: "high",
        author: "bob",
        value: 60
      }
    ]),
    getInsights: vi.fn().mockResolvedValue({
      rule_engine: [
        {
          type: "bottleneck",
          title: "High Work in Progress",
          description: "7 open PRs vs 15/week throughput.",
          severity: "medium",
          metric: "high_wip",
          meta: { value: 7 }
        }
      ],
      statistical_layer: [
        {
          type: "trend_deviation",
          title: "Review Latency Increased 42%",
          description: "Time to first review increased 42% over the last week.",
          metric: "review_latency",
          change_pct: 42,
          severity: "medium"
        }
      ],
      llm_layer: {
        executive_summary: "Test summary",
        why_did_this_happen: "Test explanation"
      }
    }),
  };
});

describe("Dashboard Page Entegrasyonu", () => {
  it("shows loading skeleton first and then renders Command Center with alerts and telemetry", async () => {
    // Render the page
    const { container } = render(<DashboardPage />);

    // Initially loading skeleton should be shown
    const skeletons = container.querySelectorAll(".loading-shimmer");
    expect(skeletons.length).toBeGreaterThan(0);

    // Wait for the async state updates to resolve the loading skeleton
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    // Check loading skeleton is gone
    const skeletonsAfter = container.querySelectorAll(".loading-shimmer");
    expect(skeletonsAfter.length).toBe(0);

    // Verify Command Center header
    expect(screen.getByText("Command Center")).toBeInTheDocument();

    // Verify HUD status console is visible (always shown, not inside accordion)
    // "Review Latency" appears in the HUD as a label
    const reviewLatencyLabels = screen.getAllByText("Review Latency");
    expect(reviewLatencyLabels.length).toBeGreaterThan(0);

    // "Throughput" appears in the HUD as a label
    const throughputLabels = screen.getAllByText("Throughput");
    expect(throughputLabels.length).toBeGreaterThan(0);

    // Verify alert feed items are rendered (combined from anomalies + rule_engine + statistical_layer)
    // "Review Bottleneck on @bob" from anomalies (severity: high)
    expect(screen.getByText("Review Bottleneck on @bob")).toBeInTheDocument();
    // "High Work in Progress" from rule_engine (severity: medium) — added to combinedAlerts
    expect(screen.getByText("High Work in Progress")).toBeInTheDocument();
    // "Review Latency Increased 42%" from statistical_layer (severity: medium) — added to combinedAlerts
    expect(screen.getByText("Review Latency Increased 42%")).toBeInTheDocument();

    // Verify action buttons exist for alert cards
    const actionBtns = container.querySelectorAll("[id^='action-primary-']");
    expect(actionBtns.length).toBeGreaterThan(0);

    // Expand supporting telemetry to render metric cards and charts
    const accordionBtn = screen.getByText("Supporting Telemetry & Historical Trends");
    await act(async () => {
      accordionBtn.click();
    });

    // Check metric cards are rendered inside the telemetry section
    expect(screen.getByText("Cycle Time")).toBeInTheDocument();
    expect(screen.getByText("Work in Progress")).toBeInTheDocument();
  });
});
