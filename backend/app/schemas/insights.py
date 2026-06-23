"""Pydantic schemas for the structured product-core insights."""

from pydantic import BaseModel


class RuleEngineInsight(BaseModel):
    """Deterministic insight from the rule engine (e.g., bottleneck, anomaly)."""

    type: str  # e.g., "bottleneck", "anomaly"
    title: str
    description: str
    severity: str  # low, medium, high
    metric: str | None = None
    meta: dict | None = None


class StatisticalInsight(BaseModel):
    """Statistical insight representing trend deviations or percentile shifts."""

    type: str  # e.g., "trend_deviation", "percentile_shift"
    title: str
    description: str
    metric: str  # cycle_time, review_latency, throughput, wip
    change_pct: float | None = None
    severity: str  # low, medium, high


class LLMInterpretation(BaseModel):
    """LLM-generated explanation of the metrics context and executive summary."""

    why_did_this_happen: str
    executive_summary: str


class InsightsResponse(BaseModel):
    """Structured insights response containing all three analytical layers."""

    rule_engine: list[RuleEngineInsight]
    statistical_layer: list[StatisticalInsight]
    llm_layer: LLMInterpretation
