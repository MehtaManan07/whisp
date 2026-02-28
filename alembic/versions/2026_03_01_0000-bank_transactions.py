"""bank_transaction_processing

Revision ID: bank_transactions_2026
Revises: deodap_order_items_2026
Create Date: 2026-03-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bank_transactions_2026'
down_revision: Union[str, Sequence[str], None] = 'deodap_order_items_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create processed_bank_transactions table for tracking processed emails
    op.create_table('processed_bank_transactions',
        sa.Column('gmail_message_id', sa.String(), nullable=False, comment='Gmail message ID for deduplication'),
        sa.Column('bank', sa.String(), nullable=False, comment='Bank name (ICICI or HDFC)'),
        sa.Column('amount', sa.Float(), nullable=False, comment='Transaction amount'),
        sa.Column('merchant', sa.String(), nullable=True, comment='Merchant/vendor name'),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=True, comment='Transaction timestamp'),
        sa.Column('reference_number', sa.String(), nullable=True, comment='Bank reference number'),
        sa.Column('whatsapp_sent', sa.Boolean(), server_default='0', nullable=False, comment='Whether WhatsApp notification was sent'),
        sa.Column('user_action', sa.String(), nullable=True, comment='User action: confirmed, dismissed, or None if pending'),
        sa.Column('expense_id', sa.Integer(), nullable=True, comment='Created expense ID if user confirmed'),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gmail_message_id')
    )
    op.create_index(op.f('ix_processed_bank_transactions_gmail_message_id'), 'processed_bank_transactions', ['gmail_message_id'], unique=True)
    op.create_index(op.f('ix_processed_bank_transactions_id'), 'processed_bank_transactions', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_processed_bank_transactions_id'), table_name='processed_bank_transactions')
    op.drop_index(op.f('ix_processed_bank_transactions_gmail_message_id'), table_name='processed_bank_transactions')
    op.drop_table('processed_bank_transactions')
