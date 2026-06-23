"""add_repo_metrics_daily

Revision ID: 6eee98afeb39
Revises: d48d26c51821
Create Date: 2026-06-23 21:12:13.044290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6eee98afeb39'
down_revision: Union[str, None] = 'd48d26c51821'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repo_metrics_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("cycle_time_avg", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cycle_time_median", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cycle_time_p90", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("review_latency_avg", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("review_latency_median", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("review_latency_p90", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("throughput_merged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("throughput_opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wip", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "date", name="uq_repo_metrics_date")
    )


def downgrade() -> None:
    op.drop_table("repo_metrics_daily")

