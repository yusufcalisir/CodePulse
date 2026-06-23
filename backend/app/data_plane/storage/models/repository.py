"""Repository model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Repository(Base):
    """A GitHub repository tracked by CodePulse."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False)
    org: Mapped[str | None] = mapped_column(String(255))
    org_id: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="default_org"
    )
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    pull_requests: Mapped[list["PullRequest"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[list["Commit"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
    sync_logs: Mapped[list["SyncLog"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
    daily_metrics: Mapped[list["RepoMetricsDaily"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )


    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, full_name='{self.full_name}')>"
