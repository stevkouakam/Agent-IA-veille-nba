"""add headline classification columns

Revision ID: 642153b7d316
Revises: e8d72f0f6b46
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '642153b7d316'
down_revision: Union[str, Sequence[str], None] = 'e8d72f0f6b46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('headlines', sa.Column('category', sa.String(length=20), server_default='general', nullable=False))
    op.add_column('headlines', sa.Column('teams', postgresql.ARRAY(sa.String(length=3)), server_default='{}', nullable=False))
    op.add_column('headlines', sa.Column('credibility_score', sa.Float(), server_default='0.5', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('headlines', 'credibility_score')
    op.drop_column('headlines', 'teams')
    op.drop_column('headlines', 'category')
