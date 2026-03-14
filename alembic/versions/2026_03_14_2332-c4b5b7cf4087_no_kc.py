"""no-kc

Revision ID: c4b5b7cf4087
Revises: bank_transactions_2026
Create Date: 2026-03-14 23:32:58.301675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4b5b7cf4087'
down_revision: Union[str, Sequence[str], None] = 'bank_transactions_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop deodap tables."""
    # Drop items first (has FK to emails)
    with op.batch_alter_table('deodap_order_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_deodap_order_items_id'))
        batch_op.drop_index(batch_op.f('ix_deodap_order_items_order_email_id'))

    op.drop_table('deodap_order_items')

    with op.batch_alter_table('deodap_order_emails', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_deodap_order_emails_gmail_message_id'))
        batch_op.drop_index(batch_op.f('ix_deodap_order_emails_id'))
        batch_op.drop_index(batch_op.f('ix_deodap_order_emails_order_id'))

    op.drop_table('deodap_order_emails')


def downgrade() -> None:
    """Recreate deodap tables."""
    # Create emails first (items has FK to it)
    op.create_table('deodap_order_emails',
    sa.Column('gmail_message_id', sa.VARCHAR(length=100), nullable=False),
    sa.Column('gmail_thread_id', sa.VARCHAR(length=100), nullable=True),
    sa.Column('email_subject', sa.VARCHAR(length=500), nullable=True),
    sa.Column('email_date', sa.DATETIME(), nullable=True),
    sa.Column('email_from', sa.VARCHAR(length=200), nullable=True),
    sa.Column('order_id', sa.VARCHAR(length=100), nullable=True),
    sa.Column('order_name', sa.VARCHAR(length=200), nullable=True),
    sa.Column('product_name', sa.VARCHAR(length=500), nullable=True),
    sa.Column('sku', sa.VARCHAR(length=100), nullable=True),
    sa.Column('price', sa.VARCHAR(length=50), nullable=True),
    sa.Column('quantity', sa.VARCHAR(length=20), nullable=True),
    sa.Column('payment_status', sa.VARCHAR(length=50), nullable=True),
    sa.Column('customer_name', sa.VARCHAR(length=200), nullable=True),
    sa.Column('address_line', sa.VARCHAR(length=500), nullable=True),
    sa.Column('city_state_pincode', sa.VARCHAR(length=200), nullable=True),
    sa.Column('country', sa.VARCHAR(length=100), nullable=True),
    sa.Column('whatsapp_sent', sa.BOOLEAN(), nullable=False),
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('created_at', sa.DATETIME(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.Column('deleted_at', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('deodap_order_emails', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_deodap_order_emails_order_id'), ['order_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_deodap_order_emails_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_deodap_order_emails_gmail_message_id'), ['gmail_message_id'], unique=1)

    op.create_table('deodap_order_items',
    sa.Column('order_email_id', sa.INTEGER(), nullable=False),
    sa.Column('product_name', sa.VARCHAR(length=500), nullable=True),
    sa.Column('sku', sa.VARCHAR(length=100), nullable=True),
    sa.Column('price', sa.VARCHAR(length=50), nullable=True),
    sa.Column('quantity', sa.VARCHAR(length=20), nullable=True),
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('created_at', sa.DATETIME(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.Column('deleted_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['order_email_id'], ['deodap_order_emails.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('deodap_order_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_deodap_order_items_order_email_id'), ['order_email_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_deodap_order_items_id'), ['id'], unique=False)
