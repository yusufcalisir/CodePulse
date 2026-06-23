"""AI-powered insight generation — rule-based, statistical, and interpretive layers."""

import logging
from dataclasses import dataclass

from app.schemas.metrics import OverviewResponse
from app.schemas.anomalies import Anomaly
from app.schemas.insights import (
    InsightsResponse,
    RuleEngineInsight,
    StatisticalInsight,
    LLMInterpretation,
)

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """A single insight generated from metrics data (legacy wrapper)."""

    type: str  # warning, info, success
    title: str
    description: str
    metric: str  # which metric triggered this
    severity: str = "medium"  # low, medium, high


class InsightService:
    """Generates actionable insights from engineering metrics.

    Provides a 3-layer intelligence core:
    1. Rule Engine (deterministic anomaly and bottleneck detection)
    2. Statistical Layer (trend deviations and percentile shifts)
    3. Interpretive Layer (executive summary and contextual explanation)
    """

    def generate_insights(self, overview: OverviewResponse) -> list[Insight]:
        """Legacy method for backward compatibility — runs rule checks and returns flat list."""
        insights: list[Insight] = []

        insights.extend(self._check_cycle_time(overview))
        insights.extend(self._check_review_latency(overview))
        insights.extend(self._check_wip(overview))
        insights.extend(self._check_throughput(overview))
        insights.extend(self._check_reviewer_bottleneck(overview))

        return insights

    def generate_structured_insights(
        self, overview: OverviewResponse, anomalies: list[Anomaly]
    ) -> InsightsResponse:
        """Core Insight Engine. Generates 3-layer structured intelligence reports."""
        
        # ── Layer 1: Rule Engine (deterministic bottleneck and anomaly detection) ──
        rule_insights: list[RuleEngineInsight] = []
        for anomaly in anomalies:
            rule_insights.append(
                RuleEngineInsight(
                    type="bottleneck" if anomaly.type in ("reviewer_bottleneck", "high_wip") else "anomaly",
                    title=anomaly.title,
                    description=anomaly.description,
                    severity=anomaly.severity,
                    metric=anomaly.type,
                    meta={
                        "author": anomaly.author,
                        "pr_number": anomaly.pr_number,
                        "value": anomaly.value,
                    },
                )
            )

        # ── Layer 2: Statistical Layer (trend deviations and percentile shifts) ──
        statistical_insights: list[StatisticalInsight] = []

        # Trend deviations (Cycle time trend)
        ct_trend = overview.cycle_time_trend
        if len(ct_trend) >= 4:
            recent_ct = sum(t.value for t in ct_trend[-2:]) / 2
            prev_ct = sum(t.value for t in ct_trend[-4:-2]) / 2
            if prev_ct > 0:
                change_pct = ((recent_ct - prev_ct) / prev_ct) * 100
                if change_pct > 20:
                    statistical_insights.append(
                        StatisticalInsight(
                            type="trend_deviation",
                            title="Cycle Time Trend Increasing",
                            description=(
                                f"PR cycle time increased {change_pct:.0f}% over the last 2 weeks "
                                f"({prev_ct:.1f}h → {recent_ct:.1f}h)."
                            ),
                            metric="cycle_time",
                            change_pct=round(change_pct, 1),
                            severity="high" if change_pct > 40 else "medium",
                        )
                    )
                elif change_pct < -15:
                    statistical_insights.append(
                        StatisticalInsight(
                            type="trend_deviation",
                            title="Cycle Time Trend Improving",
                            description=(
                                f"PR cycle time decreased {abs(change_pct):.0f}% over the last 2 weeks. "
                                f"Engineering velocity is improving."
                            ),
                            metric="cycle_time",
                            change_pct=round(change_pct, 1),
                            severity="low",
                        )
                    )

        # Trend deviations (Throughput trend)
        tp_trend = overview.throughput_trend
        if len(tp_trend) >= 4:
            recent_tp = sum(t.merged for t in tp_trend[-2:]) / 2
            prev_tp = sum(t.merged for t in tp_trend[-4:-2]) / 2
            if prev_tp > 0:
                change_pct = ((recent_tp - prev_tp) / prev_tp) * 100
                if change_pct < -25:
                    statistical_insights.append(
                        StatisticalInsight(
                            type="trend_deviation",
                            title="Throughput Trend Declining",
                            description=(
                                f"Merged PR throughput dropped by {abs(change_pct):.0f}% "
                                f"over the last 2 weeks ({prev_tp:.1f} → {recent_tp:.1f} PRs/week)."
                            ),
                            metric="throughput",
                            change_pct=round(change_pct, 1),
                            severity="high" if change_pct < -40 else "medium",
                        )
                    )

        # Percentile shifts (Cycle time median vs p90)
        ct = overview.metrics.cycle_time
        if ct.median > 0 and ct.p90 > ct.median * 3:
            ratio = ct.p90 / ct.median
            statistical_insights.append(
                StatisticalInsight(
                    type="percentile_shift",
                    title="PR Cycle Time Percentile Shift",
                    description=(
                        f"The p90 cycle time ({ct.p90}h) is {ratio:.1f}x higher than the median ({ct.median}h). "
                        f"This suggests delivery unpredictability due to outlier PR delays."
                    ),
                    metric="cycle_time",
                    change_pct=round(ratio * 100, 1),
                    severity="medium",
                )
            )

        # Percentile shifts (Review latency median)
        rl = overview.metrics.review_latency
        if rl.median > 24:
            statistical_insights.append(
                StatisticalInsight(
                    type="percentile_shift",
                    title="Slow Median Review Latency",
                    description=(
                        f"Median review latency is {rl.median}h, exceeding the healthy threshold of 8h. "
                        f"Queue time for code reviews is sluggish."
                    ),
                    metric="review_latency",
                    severity="high",
                )
            )

        # ── Layer 3: Interpretive Layer (Executive Summary and 'Why' Explanation) ──
        anoms_count = len(anomalies)
        bottlenecks = [a for a in anomalies if a.type == "reviewer_bottleneck"]
        wip_anom = [a for a in anomalies if a.type == "high_wip"]
        large_prs = [a for a in anomalies if a.type == "pr_size_anomaly"]

        if anoms_count == 0:
            exec_summary = (
                "Engineering delivery velocity and process health are within normal parameters. "
                "PR review distribution is balanced, and work-in-progress is aligned with weekly throughput."
            )
            why_happened = (
                "Process consistency is high. The default branch is receiving steady, small updates "
                "with minimal reviewer overload or large batch pushes."
            )
        else:
            summary_parts = []
            why_parts = []

            if bottlenecks:
                summary_parts.append(f"a severe review distribution bottleneck on @{bottlenecks[0].author}")
                why_parts.append(f"@{bottlenecks[0].author} handling {bottlenecks[0].value}% of all code reviews, creating a single point of failure.")
            if wip_anom:
                summary_parts.append("high context-switching overhead due to work-in-progress overload")
                why_parts.append(f"concurrent open PRs ({overview.metrics.wip}) exceeding weekly throughput ({overview.metrics.throughput_avg_4_week}/week) by over 2.5x, causing queue blockages.")
            if large_prs:
                summary_parts.append(f"outlier delays from excessively large PR changes (e.g. PR #{large_prs[0].pr_number})")
                why_parts.append(f"large code changes (>500 lines) dragging down cycle times and overloading reviewers.")

            if not summary_parts:
                summary_parts.append("minor process outliers in cycle times or review latency trends")
                why_parts.append("fluctuating PR sizes and review latency response times.")

            exec_summary = f"Process telemetry identifies workflow friction points: {', '.join(summary_parts)}. Team delivery throughput is at risk of decline due to resource concentration."
            why_happened = f"These anomalies are primarily driven by: {', '.join(why_parts)} Streamlining PR sizing and distributing reviews will restore pipeline efficiency."

        llm_layer = LLMInterpretation(
            executive_summary=exec_summary,
            why_did_this_happen=why_happened,
        )

        return InsightsResponse(
            rule_engine=rule_insights,
            statistical_layer=statistical_insights,
            llm_layer=llm_layer,
        )

    # ── Legacy Rule-based checks ──────────────────────────────

    def _check_cycle_time(self, overview: OverviewResponse) -> list[Insight]:
        """Detect cycle time anomalies (legacy)."""
        insights = []
        ct = overview.metrics.cycle_time

        if ct.median > 48:
            insights.append(Insight(
                type="warning",
                title="High PR Cycle Time",
                description=(
                    f"Median PR cycle time is {ct.median}h (>48h). "
                    "Consider breaking PRs into smaller chunks or reviewing process bottlenecks."
                ),
                metric="cycle_time",
                severity="high",
            ))
        elif ct.median > 24:
            insights.append(Insight(
                type="info",
                title="Moderate PR Cycle Time",
                description=(
                    f"Median PR cycle time is {ct.median}h. "
                    "This is acceptable but could be improved."
                ),
                metric="cycle_time",
                severity="medium",
            ))

        if ct.median > 0 and ct.p90 > ct.median * 4:
            insights.append(Insight(
                type="warning",
                title="Inconsistent PR Cycle Time",
                description=(
                    f"p90 cycle time ({ct.p90}h) is {ct.p90/ct.median:.0f}x the median ({ct.median}h). "
                    "Some PRs are taking much longer than average — investigate outliers."
                ),
                metric="cycle_time",
                severity="medium",
            ))

        trend = overview.cycle_time_trend
        if len(trend) >= 4:
            recent = sum(t.value for t in trend[-2:]) / 2
            previous = sum(t.value for t in trend[-4:-2]) / 2
            if previous > 0:
                change_pct = ((recent - previous) / previous) * 100
                if change_pct > 30:
                    insights.append(Insight(
                        type="warning",
                        title="Cycle Time Increasing",
                        description=(
                            f"PR cycle time increased {change_pct:.0f}% over the last 2 weeks "
                            f"({previous:.1f}h → {recent:.1f}h)."
                        ),
                        metric="cycle_time",
                        severity="high",
                    ))
                elif change_pct < -20:
                    insights.append(Insight(
                        type="success",
                        title="Cycle Time Improving",
                        description=(
                            f"PR cycle time decreased {abs(change_pct):.0f}% over the last 2 weeks. "
                            "Great progress!"
                        ),
                        metric="cycle_time",
                        severity="low",
                    ))

        return insights

    def _check_review_latency(self, overview: OverviewResponse) -> list[Insight]:
        """Detect review latency issues (legacy)."""
        insights = []
        rl = overview.metrics.review_latency

        if rl.median > 24:
            insights.append(Insight(
                type="warning",
                title="Slow Code Reviews",
                description=(
                    f"Median time to first review is {rl.median}h (>24h). "
                    "PRs are waiting too long for review attention."
                ),
                metric="review_latency",
                severity="high",
            ))
        elif rl.median > 8:
            insights.append(Insight(
                type="info",
                title="Review Latency Could Improve",
                description=(
                    f"Median time to first review is {rl.median}h. "
                    "Aim for <4h for optimal flow."
                ),
                metric="review_latency",
                severity="medium",
            ))

        return insights

    def _check_wip(self, overview: OverviewResponse) -> list[Insight]:
        """Detect WIP overload (legacy)."""
        insights = []
        wip = overview.metrics.wip
        throughput = overview.metrics.throughput_avg_4_week

        if throughput > 0 and wip > throughput * 2:
            insights.append(Insight(
                type="warning",
                title="High Work in Progress",
                description=(
                    f"{wip} open PRs vs {throughput:.0f}/week throughput. "
                    "WIP exceeds 2x throughput — this signals a review bottleneck."
                ),
                metric="wip",
                severity="high",
            ))

        return insights

    def _check_throughput(self, overview: OverviewResponse) -> list[Insight]:
        """Detect throughput changes (legacy)."""
        insights = []
        trend = overview.throughput_trend

        if len(trend) >= 4:
            recent = sum(t.merged for t in trend[-2:]) / 2
            previous = sum(t.merged for t in trend[-4:-2]) / 2
            if previous > 0:
                change_pct = ((recent - previous) / previous) * 100
                if change_pct < -30:
                    insights.append(Insight(
                        type="warning",
                        title="Throughput Declining",
                        description=(
                            f"Merged PR throughput dropped {abs(change_pct):.0f}% "
                            f"over the last 2 weeks ({previous:.0f} → {recent:.0f}/week)."
                        ),
                        metric="throughput",
                        severity="high",
                    ))

        return insights

    def _check_reviewer_bottleneck(self, overview: OverviewResponse) -> list[Insight]:
        """Detect bus factor issues in code review (legacy)."""
        return []
