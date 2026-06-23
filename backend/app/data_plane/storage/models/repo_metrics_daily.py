"""RepoMetricsDaily model for caching precomputed daily engineering metrics."""

from datetime import date
from sqlalchemy import Date, ForeignKey, Integer, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RepoMetricsDaily(Base):
    """Precomputed daily metrics table for faster dashboard rendering and intelligence querying."""

    __tablename__ = "repo_metrics_daily"
    __table_args__ = (
        UniqueConstraint("repo_id", "date", name="uq_repo_metrics_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Cycle time metrics (for PRs merged on this day) in hours
    cycle_time_avg: Mapped[float] = mapped_column(Float, default=0.0)
    cycle_time_median: Mapped[float] = mapped_column(Float, default=0.0)
    cycle_time_p90: Mapped[float] = mapped_column(Float, default=0.0)

    # Review latency metrics (for first reviews submitted on this day) in hours
    review_latency_avg: Mapped[float] = mapped_column(Float, default=0.0)
    review_latency_median: Mapped[float] = mapped_column(Float, default=0.0)
    review_latency_p90: Mapped[float] = mapped_column(Float, default=0.0)

    # Throughput metrics
    throughput_merged: Mapped[int] = mapped_column(Integer, default=0)
    throughput_opened: Mapped[int] = mapped_column(Integer, default=0)

    # WIP metrics (open PRs at the end of the day)
    wip: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    repository: Mapped["Repository"] = relationship(  # noqa: F821
        back_populates="daily_metrics"
    )

    def __repr__(self) -> str:
        return f"<RepoMetricsDaily(id={self.id}, repo_id={self.repo_id}, date={self.date})>"
