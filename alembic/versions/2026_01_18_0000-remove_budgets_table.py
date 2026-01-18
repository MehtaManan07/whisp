"""remove_budgets_table

Revision ID: remove_budgets_001
Revises: 98adebd998a9
Create Date: 2026-01-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'remove_budgets_001'
down_revision: Union[str, Sequence[str], None] = '98adebd998a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop budgets table and all associated indexes."""
    
    # Drop all indexes first
    op.drop_index(op.f('ix_budgets_user_id'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_id'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_category_id'), table_name='budgets')
    op.drop_index('idx_budgets_user_period', table_name='budgets')
    op.drop_index('idx_budgets_is_active', table_name='budgets')
    op.drop_index('idx_budgets_deleted_at', table_name='budgets')
    op.drop_index('idx_budgets_category', table_name='budgets')
    
    # Drop the budgets table
    op.drop_table('budgets')


def downgrade() -> None:
    """Recreate budgets table if needed (rollback)."""
    
    # Recreate the budgets table
    op.create_table('budgets',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('period', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('alert_thresholds', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate indexes
    op.create_index('idx_budgets_category', 'budgets', ['category_id'], unique=False)
    op.create_index('idx_budgets_deleted_at', 'budgets', ['deleted_at'], unique=False)
    op.create_index('idx_budgets_is_active', 'budgets', ['is_active'], unique=False)
    op.create_index('idx_budgets_user_period', 'budgets', ['user_id', 'period'], unique=False)
    op.create_index(op.f('ix_budgets_category_id'), 'budgets', ['category_id'], unique=False)
    op.create_index(op.f('ix_budgets_id'), 'budgets', ['id'], unique=False)
    op.create_index(op.f('ix_budgets_user_id'), 'budgets', ['user_id'], unique=False)
