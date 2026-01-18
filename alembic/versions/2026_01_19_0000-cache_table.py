"""add cache table

Revision ID: cache_table_2026
Revises: remove_budgets_001
Create Date: 2026-01-19 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cache_table_2026'
down_revision: Union[str, Sequence[str], None] = 'remove_budgets_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create cache table
    op.create_table(
        'cache',
        sa.Column('key', sa.String(255), primary_key=True, index=True, nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create index on expires_at for efficient cleanup
    op.create_index('idx_expires_at', 'cache', ['expires_at'])


def downgrade() -> None:
    # Drop cache table
    op.drop_index('idx_expires_at', table_name='cache')
    op.drop_table('cache')
