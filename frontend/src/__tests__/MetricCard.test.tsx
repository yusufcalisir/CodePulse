import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MetricCard from "../components/ui/MetricCard";
import React from "react";

describe("MetricCard Component", () => {
  const mockIcon = <span data-testid="mock-icon">📊</span>;

  it("renders basic metric info correctly", () => {
    render(
      <MetricCard
        title="Active PRs"
        value={15}
        format="count"
        icon={mockIcon}
        subtitle="Current active PR count"
      />
    );

    expect(screen.getByText("Active PRs")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByTestId("mock-icon")).toBeInTheDocument();
    expect(screen.getByText("Current active PR count")).toBeInTheDocument();
  });

  it("formats duration values correctly", () => {
    // 1.5h -> should be formatted to duration via utils (e.g. 1.5h)
    render(
      <MetricCard
        title="Cycle Time"
        value={18.5}
        format="duration"
        icon={mockIcon}
      />
    );

    expect(screen.getByText("18.5h")).toBeInTheDocument();
  });

  it("renders a positive change trend correctly", () => {
    render(
      <MetricCard
        title="Cycle Time"
        value={20}
        format="number"
        previousValue={10}
        icon={mockIcon}
      />
    );

    // change = ((20 - 10) / 10) * 100 = 100%
    expect(screen.getByText("100%")).toBeInTheDocument();
    // Since change > 5, it should render with danger color styling (red)
    const trendBadge = screen.getByText("100%");
    expect(trendBadge?.style.color).toBe("var(--color-danger)");
  });

  it("renders a negative change trend correctly", () => {
    render(
      <MetricCard
        title="Review Latency"
        value={5}
        format="number"
        previousValue={10}
        icon={mockIcon}
      />
    );

    // change = ((5 - 10) / 10) * 100 = -50%
    expect(screen.getByText("50%")).toBeInTheDocument();
    // Since change < -5, it should render with success color styling (green)
    const trendBadge = screen.getByText("50%");
    expect(trendBadge?.style.color).toBe("var(--color-success)");
  });
});
