"""add_analysis_columns_manual

Revision ID: 529f6b49792a
Revises: 
Create Date: 2026-02-14 01:44:57.312788

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '529f6b49792a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('papers', sa.Column('analysis', sa.JSON(), nullable=True))
    op.add_column('papers', sa.Column('figures', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('papers', 'figures')
    op.drop_column('papers', 'analysis')
