"""rename wa_id to telegram_id

Revision ID: 7e1a2b3c4d5f
Revises: 38334bc8f2c6
Create Date: 2026-05-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7e1a2b3c4d5f'
down_revision: Union[str, Sequence[str], None] = '38334bc8f2c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Uses direct ALTER ops instead of batch_alter_table because libSQL/Turso's
    Hrana protocol enforces FOREIGN KEY checks during the batch-mode table
    rebuild even when PRAGMA foreign_keys=OFF is set on the session.
    SQLite 3.35+ (which libSQL is built on) supports ALTER TABLE DROP COLUMN
    natively, so we don't need batch mode for this migration.
    """
    op.drop_index('ix_users_wa_id', table_name='users')
    op.drop_column('users', 'wa_id')
    op.add_column(
        'users',
        sa.Column(
            'telegram_id',
            sa.String(),
            nullable=True,
            comment='Telegram user ID',
        ),
    )
    op.create_index(
        'ix_users_telegram_id', 'users', ['telegram_id'], unique=True
    )


def downgrade() -> None:
    """Downgrade schema.

    Note: wa_id values cannot be restored — re-added as nullable.
    """
    op.drop_index('ix_users_telegram_id', table_name='users')
    op.drop_column('users', 'telegram_id')
    op.add_column(
        'users',
        sa.Column(
            'wa_id',
            sa.String(),
            nullable=True,
            comment='WhatsApp ID from webhook',
        ),
    )
    op.create_index('ix_users_wa_id', 'users', ['wa_id'], unique=True)
