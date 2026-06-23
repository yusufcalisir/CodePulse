"""Sync log model for tracking data ingestion status."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SyncLog(Base):
    """Tracks the status and progress of GitHub data sync operations."""

    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # running, completed, failed
    pr_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    # Relationships
    repository: Mapped["Repository"] = relationship(  # noqa: F821
        back_populates="sync_logs"
    )

    def __repr__(self) -> str:
        return f"<SyncLog(id={self.id}, repo_id={self.repo_id}, status='{self.status}')>"
