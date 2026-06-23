"""Pydantic schemas for anomaly detection endpoints."""

from typing import Optional
from pydantic import BaseModel


class Anomaly(BaseModel):
    """Pydantic schema representing a single engineering process anomaly."""

    type: str  # cycle_time_spike, pr_size_anomaly, reviewer_bottleneck, high_wip
    title: str
    description: str
    severity: str  # low, medium, high
    pr_number: Optional[int] = None
    author: Optional[str] = None
    value: float
