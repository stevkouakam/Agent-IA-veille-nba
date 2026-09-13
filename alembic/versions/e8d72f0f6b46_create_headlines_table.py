"""create headlines table

Revision ID: e8d72f0f6b46
Revises: 5bb91c1c773a
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8d72f0f6b46'
down_revision: Union[str, Sequence[str], None] = '5bb91c1c773a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('headlines',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('headline_id', sa.String(length=32), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('link', sa.String(length=1000), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_headlines_headline_id'), 'headlines', ['headline_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_headlines_headline_id'), table_name='headlines')
    op.drop_table('headlines')
