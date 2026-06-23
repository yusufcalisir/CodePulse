"""Commit model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Commit(Base):
    """A commit in a tracked GitHub repository."""

    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    sha: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))
    authored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(  # noqa: F821
        back_populates="commits"
    )

    def __repr__(self) -> str:
        return f"<Commit(id={self.id}, sha='{self.sha[:8]}...', author='{self.author}')>"
