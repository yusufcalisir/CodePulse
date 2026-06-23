"""add_idempotency_key_to_events

Revision ID: 28217bbcf929
Revises: 6eee98afeb39
Create Date: 2026-06-23 21:24:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28217bbcf929'
down_revision: Union[str, None] = '6eee98afeb39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_event_idempotency_key', 'events', ['idempotency_key'])


def downgrade() -> None:
    op.drop_constraint('uq_event_idempotency_key', 'events', type_='unique')
    op.drop_column('events', 'idempotency_key')
