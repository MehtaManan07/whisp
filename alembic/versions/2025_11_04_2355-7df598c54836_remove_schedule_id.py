"""remove_schedule_id

Revision ID: 7df598c54836
Revises: 0caeb3505a72
Create Date: 2025-11-04 23:55:13.072953

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7df598c54836'
down_revision: Union[str, Sequence[str], None] = '0caeb3505a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
