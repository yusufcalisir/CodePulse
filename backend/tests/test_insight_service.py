"""Unit tests for the AI/Rule-based Insight service (insight_service.py)."""

import pytest

from app.schemas.metrics import (
    OverviewMetrics,
    OverviewResponse,
    StatSummary,
    ThroughputWeek,
    WeeklyDataPoint,
)
from app.intelligence_plane.insights.insight_service import InsightService


@pytest.fixture
def base_overview() -> OverviewResponse:
    """Provide a baseline OverviewResponse helper for tests."""
    return OverviewResponse(
        metrics=OverviewMetrics(
            cycle_time=StatSummary(avg=12.0, median=10.0, p90=20.0),
            review_latency=StatSummary(avg=3.0, median=2.0, p90=8.0),
            wip=3,
            throughput_current_week=5,
            throughput_avg_4_week=5.0,
        ),
        cycle_time_trend=[
            WeeklyDataPoint(week="2026-W21", value=10.0, count=5),
            WeeklyDataPoint(week="2026-W22", value=10.0, count=5),
            WeeklyDataPoint(week="2026-W23", value=10.0, count=5),
            WeeklyDataPoint(week="2026-W24", value=10.0, count=5),
        ],
        throughput_trend=[
            ThroughputWeek(week="2026-W21", merged=5, opened=5),
            ThroughputWeek(week="2026-W22", merged=5, opened=5),
            ThroughputWeek(week="2026-W23", merged=5, opened=5),
            ThroughputWeek(week="2026-W24", merged=5, opened=5),
        ],
    )


def test_generate_insights_baseline_clean(base_overview: OverviewResponse) -> None:
    """Test that stable, healthy metrics generate no critical warnings."""
    service = InsightService()
    insights = service.generate_insights(base_overview)

    # With base metrics (cycle time 10h, wip 3, throughput 5)
    # it shouldn't trigger warnings (median ct <= 24h, p90 not 4x median, wip <= throughput * 2)
    warnings = [i for i in insights if i.type == "warning"]
    assert len(warnings) == 0


def test_high_cycle_time_warning(base_overview: OverviewResponse) -> None:
    """Test warning triggers when median cycle time is extremely high (>48h)."""
    service = InsightService()

    base_overview.metrics.cycle_time = StatSummary(avg=50.0, median=55.0, p90=70.0)
    insights = service.generate_insights(base_overview)

    high_ct_insights = [
        i
        for i in insights
        if i.title == "High PR Cycle Time" and i.type == "warning"
    ]
    assert len(high_ct_insights) == 1
    assert high_ct_insights[0].severity == "high"


def test_inconsistent_cycle_time_warning(base_overview: OverviewResponse) -> None:
    """Test warning when p90 cycle time is a significant multiple of median."""
    service = InsightService()

    # Median is 10h, p90 is 45h (> 4x median)
    base_overview.metrics.cycle_time = StatSummary(avg=15.0, median=10.0, p90=45.0)
    insights = service.generate_insights(base_overview)

    inconsistent_insights = [
        i for i in insights if i.title == "Inconsistent PR Cycle Time"
    ]
    assert len(inconsistent_insights) == 1
    assert inconsistent_insights[0].type == "warning"
    assert "investigate outliers" in inconsistent_insights[0].description


def test_cycle_time_increasing_trend_warning(
    base_overview: OverviewResponse,
) -> None:
    """Test warning trigger when cycle time increases by >30% over the last 2 weeks."""
    service = InsightService()

    # Previous weeks: 10h, Recent weeks: 15h (+50% increase)
    base_overview.cycle_time_trend = [
        WeeklyDataPoint(week="2026-W21", value=10.0, count=5),
        WeeklyDataPoint(week="2026-W22", value=10.0, count=5),
        WeeklyDataPoint(week="2026-W23", value=15.0, count=5),
        WeeklyDataPoint(week="2026-W24", value=15.0, count=5),
    ]

    insights = service.generate_insights(base_overview)
    increasing_insights = [
        i for i in insights if i.title == "Cycle Time Increasing"
    ]
    assert len(increasing_insights) == 1
    assert increasing_insights[0].type == "warning"
    assert "increased 50%" in increasing_insights[0].description


def test_cycle_time_improving_success(base_overview: OverviewResponse) -> None:
    """Test success notification when cycle time decreases by >20%."""
    service = InsightService()

    # Previous weeks: 10h, Recent weeks: 7h (30% decrease)
    base_overview.cycle_time_trend = [
        WeeklyDataPoint(week="2026-W21", value=10.0, count=5),
        WeeklyDataPoint(week="2026-W22", value=10.0, count=5),
        WeeklyDataPoint(week="2026-W23", value=7.0, count=5),
        WeeklyDataPoint(week="2026-W24", value=7.0, count=5),
    ]

    insights = service.generate_insights(base_overview)
    improving_insights = [
        i for i in insights if i.title == "Cycle Time Improving"
    ]
    assert len(improving_insights) == 1
    assert improving_insights[0].type == "success"
    assert "decreased 30%" in improving_insights[0].description


def test_wip_bottleneck_warning(base_overview: OverviewResponse) -> None:
    """Test warning trigger when WIP exceeds 2x the rolling average throughput."""
    service = InsightService()

    # Throughput is 5/week, WIP is 12 (> 2x 5)
    base_overview.metrics.wip = 12
    base_overview.metrics.throughput_avg_4_week = 5.0

    insights = service.generate_insights(base_overview)
    wip_insights = [i for i in insights if i.title == "High Work in Progress"]
    assert len(wip_insights) == 1
    assert wip_insights[0].type == "warning"
    assert "signals a review bottleneck" in wip_insights[0].description


def test_generate_structured_insights(base_overview: OverviewResponse) -> None:
    """Test that generate_structured_insights builds Rule, Statistical, and LLM layers."""
    service = InsightService()

    # Modify metrics to trigger statistical deviations
    base_overview.metrics.cycle_time = StatSummary(avg=12.0, median=10.0, p90=40.0) # p90 > median * 3 (percentile shift)
    base_overview.metrics.review_latency = StatSummary(avg=3.0, median=30.0, p90=50.0) # median > 24 (percentile shift)

    # Setup trend to trigger a positive cycle time trend shift (+50%)
    base_overview.cycle_time_trend = [
        WeeklyDataPoint(week="2026-W21", value=10.0, count=5),
        WeeklyDataPoint(week="2026-W22", value=10.0, count=5),
        WeeklyDataPoint(week="2026-W23", value=15.0, count=5),
        WeeklyDataPoint(week="2026-W24", value=15.0, count=5),
    ]

    from app.schemas.anomalies import Anomaly
    mock_anomalies = [
        Anomaly(
            type="reviewer_bottleneck",
            title="Review Bottleneck: @charlie",
            description="@charlie did 55% of all reviews.",
            severity="medium",
            pr_number=None,
            author="charlie",
            value=55.0
        )
    ]

    res = service.generate_structured_insights(base_overview, mock_anomalies)

    # 1. Rule Engine
    assert len(res.rule_engine) == 1
    assert res.rule_engine[0].type == "bottleneck"
    assert res.rule_engine[0].severity == "medium"
    assert res.rule_engine[0].meta["author"] == "charlie"

    # 2. Statistical Layer
    # We expect 3 statistical insights: cycle time trend increase, cycle time percentile shift, and review latency percentile shift
    assert len(res.statistical_layer) >= 2
    types = [s.type for s in res.statistical_layer]
    assert "trend_deviation" in types
    assert "percentile_shift" in types

    # 3. LLM / Interpretive Layer
    assert "bottleneck on @charlie" in res.llm_layer.executive_summary
    assert "charlie handling 55" in res.llm_layer.why_did_this_happen

