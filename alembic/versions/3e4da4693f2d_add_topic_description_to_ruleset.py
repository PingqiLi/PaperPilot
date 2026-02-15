"""add_topic_description_to_ruleset

Revision ID: 3e4da4693f2d
Revises: 529f6b49792a
Create Date: 2026-02-14 12:42:29.100444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e4da4693f2d'
down_revision: Union[str, Sequence[str], None] = '529f6b49792a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('rulesets', sa.Column('topic_description', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('rulesets', 'topic_description')
