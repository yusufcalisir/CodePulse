"""Pydantic schemas for metrics endpoints."""

from pydantic import BaseModel


class StatSummary(BaseModel):
    """Statistical summary with avg, median, and p90."""

    avg: float
    median: float
    p90: float
    unit: str = "hours"


class WeeklyDataPoint(BaseModel):
    """A single data point in a weekly trend."""

    week: str  # ISO week format e.g. "2026-W20"
    value: float
    count: int | None = None


class ThroughputWeek(BaseModel):
    """Weekly throughput data with opened and merged counts."""

    week: str
    merged: int
    opened: int


class ContributorMetric(BaseModel):
    """Metric breakdown by contributor."""

    author: str
    avg: float
    count: int


# ── Response schemas ─────────────────────────────────────────


class CycleTimeResponse(BaseModel):
    """PR cycle time metrics response."""

    summary: StatSummary
    trend: list[WeeklyDataPoint]
    period_days: int


class ReviewLatencyResponse(BaseModel):
    """Review latency metrics response."""

    summary: StatSummary
    by_reviewer: list[ContributorMetric]
    trend: list[WeeklyDataPoint]
    period_days: int


class ThroughputResponse(BaseModel):
    """Throughput metrics response."""

    weekly: list[ThroughputWeek]
    rolling_avg: float
    period_weeks: int


class OverviewMetrics(BaseModel):
    """Overview metrics for the dashboard cards."""

    cycle_time: StatSummary
    review_latency: StatSummary
    wip: int
    throughput_current_week: int
    throughput_avg_4_week: float
    period: str = "last_30_days"


class OverviewResponse(BaseModel):
    """Full overview response including metrics and trends."""

    metrics: OverviewMetrics
    cycle_time_trend: list[WeeklyDataPoint]
    throughput_trend: list[ThroughputWeek]
