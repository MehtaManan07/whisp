"""deodap_order_items

Revision ID: deodap_order_items_2026
Revises: 8ec0ba8dc9e1
Create Date: 2026-01-31 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'deodap_order_items_2026'
down_revision: Union[str, Sequence[str], None] = '8ec0ba8dc9e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create deodap_order_items table for storing multiple items per order
    op.create_table('deodap_order_items',
        sa.Column('order_email_id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(length=500), nullable=True),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('price', sa.String(length=50), nullable=True),
        sa.Column('quantity', sa.String(length=20), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['order_email_id'], ['deodap_order_emails.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deodap_order_items_id'), 'deodap_order_items', ['id'], unique=False)
    op.create_index(op.f('ix_deodap_order_items_order_email_id'), 'deodap_order_items', ['order_email_id'], unique=False)
    
    # Migrate existing data: copy single-item data from deodap_order_emails to deodap_order_items
    # This ensures backward compatibility with existing orders
    op.execute("""
        INSERT INTO deodap_order_items (order_email_id, product_name, sku, price, quantity, created_at)
        SELECT id, product_name, sku, price, quantity, created_at
        FROM deodap_order_emails
        WHERE product_name IS NOT NULL OR sku IS NOT NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_deodap_order_items_order_email_id'), table_name='deodap_order_items')
    op.drop_index(op.f('ix_deodap_order_items_id'), table_name='deodap_order_items')
    op.drop_table('deodap_order_items')
