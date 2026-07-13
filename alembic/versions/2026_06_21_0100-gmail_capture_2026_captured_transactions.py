"""gmail_capture: drop legacy processed_bank_transactions, add captured_transactions

Revision ID: gmail_capture_2026
Revises: 7e1a2b3c4d5f
Create Date: 2026-06-21 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'gmail_capture_2026'
down_revision: Union[str, Sequence[str], None] = '7e1a2b3c4d5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Remove the dead legacy table from the old (regex-based) pipeline.
    if 'processed_bank_transactions' in existing_tables:
        op.drop_table('processed_bank_transactions')

    op.create_table(
        'captured_transactions',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('gmail_message_id', sa.String(), nullable=False),
        sa.Column('bank', sa.String(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('card_last4', sa.String(), nullable=True),
        sa.Column('merchant_hint', sa.String(), nullable=True),
        sa.Column('raw_subject', sa.String(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('expense_id', sa.Integer(), nullable=True),
        sa.Column('telegram_chat_id', sa.String(), nullable=True),
        sa.Column('telegram_message_id', sa.String(), nullable=True),
        sa.Column('last_nudged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gmail_message_id'),
    )
    op.create_index(op.f('ix_captured_transactions_id'), 'captured_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_captured_transactions_user_id'), 'captured_transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_captured_transactions_gmail_message_id'), 'captured_transactions', ['gmail_message_id'], unique=True)
    op.create_index(op.f('ix_captured_transactions_telegram_message_id'), 'captured_transactions', ['telegram_message_id'], unique=False)
    op.create_index('idx_captured_txn_status', 'captured_transactions', ['status'], unique=False)
    op.create_index('idx_captured_txn_user', 'captured_transactions', ['user_id'], unique=False)
    op.create_index('idx_captured_txn_tg_msg', 'captured_transactions', ['telegram_message_id'], unique=False)

    op.create_table(
        'capture_state',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('gmail_last_checked_epoch', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_capture_state_user_id'), 'capture_state', ['user_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_capture_state_user_id'), table_name='capture_state')
    op.drop_table('capture_state')

    op.drop_index('idx_captured_txn_tg_msg', table_name='captured_transactions')
    op.drop_index('idx_captured_txn_user', table_name='captured_transactions')
    op.drop_index('idx_captured_txn_status', table_name='captured_transactions')
    op.drop_index(op.f('ix_captured_transactions_telegram_message_id'), table_name='captured_transactions')
    op.drop_index(op.f('ix_captured_transactions_gmail_message_id'), table_name='captured_transactions')
    op.drop_index(op.f('ix_captured_transactions_user_id'), table_name='captured_transactions')
    op.drop_index(op.f('ix_captured_transactions_id'), table_name='captured_transactions')
    op.drop_table('captured_transactions')

    op.create_table(
        'processed_bank_transactions',
        sa.Column('gmail_message_id', sa.String(), nullable=False),
        sa.Column('bank', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('merchant', sa.String(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reference_number', sa.String(), nullable=True),
        sa.Column('whatsapp_sent', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('user_action', sa.String(), nullable=True),
        sa.Column('expense_id', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gmail_message_id'),
    )
    op.create_index(op.f('ix_processed_bank_transactions_gmail_message_id'), 'processed_bank_transactions', ['gmail_message_id'], unique=True)
    op.create_index(op.f('ix_processed_bank_transactions_id'), 'processed_bank_transactions', ['id'], unique=False)
