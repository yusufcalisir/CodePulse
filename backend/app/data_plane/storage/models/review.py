"""Review model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Review(Base):
    """A review submitted on a GitHub pull request."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("pr_id", "github_id", name="uq_review_pr_github"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pr_id: Mapped[int] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False
    )
    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship(  # noqa: F821
        back_populates="reviews"
    )

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, state='{self.state}', author='{self.author}')>"
