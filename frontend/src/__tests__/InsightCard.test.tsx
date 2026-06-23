import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InsightCard from "../components/ui/InsightCard";
import type { Insight } from "@/types";
import React from "react";

describe("InsightCard Component", () => {
  it("renders success insight status correctly", () => {
    const mockInsight: Insight = {
      type: "success",
      title: "Cycle Time Improved",
      description: "PR process is much faster now.",
      metric: "cycle_time",
      severity: "low",
    };

    render(<InsightCard insight={mockInsight} />);

    expect(screen.getByText("Cycle Time Improved")).toBeInTheDocument();
    expect(screen.getByText("PR process is much faster now.")).toBeInTheDocument();
    expect(screen.getByText("cycle time")).toBeInTheDocument();
    
    // Check it gets styled with success left border
    const cardContainer = screen.getByText("Cycle Time Improved").closest(".glass-card");
    expect(cardContainer).toHaveStyle({ borderLeftColor: "rgba(16, 185, 129, 0.3)" });
  });

  it("renders warning insight status correctly", () => {
    const mockInsight: Insight = {
      type: "warning",
      title: "High WIP",
      description: "WIP exceeds throughput guidelines.",
      metric: "wip",
      severity: "high",
    };

    render(<InsightCard insight={mockInsight} />);

    expect(screen.getByText("High WIP")).toBeInTheDocument();
    expect(screen.getByText("WIP exceeds throughput guidelines.")).toBeInTheDocument();
    expect(screen.getByText("wip")).toBeInTheDocument();
    
    // Check it gets styled with warning left border
    const cardContainer = screen.getByText("High WIP").closest(".glass-card");
    expect(cardContainer).toHaveStyle({ borderLeftColor: "rgba(245, 158, 11, 0.3)" });
  });
});
