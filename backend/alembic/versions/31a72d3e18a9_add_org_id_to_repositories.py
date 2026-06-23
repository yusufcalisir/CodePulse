"""add_org_id_to_repositories

Revision ID: 31a72d3e18a9
Revises: 28217bbcf929
Create Date: 2026-06-23 21:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31a72d3e18a9'
down_revision: Union[str, None] = '28217bbcf929'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'repositories',
        sa.Column('org_id', sa.String(length=255), nullable=False, server_default='default_org')
    )


def downgrade() -> None:
    op.drop_column('repositories', 'org_id')
