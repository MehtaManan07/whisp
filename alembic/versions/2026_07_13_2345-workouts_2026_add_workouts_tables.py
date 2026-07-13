"""workouts: add workouts, workout_exercises, workout_sets tables

Revision ID: workouts_2026
Revises: gmail_capture_2026
Create Date: 2026-07-13 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'workouts_2026'
down_revision: Union[str, Sequence[str], None] = 'gmail_capture_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'workouts' not in existing_tables:
        op.create_table(
            'workouts',
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=True),
            sa.Column('performed_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('source', sa.String(), nullable=True),
            sa.Column('notes', sa.String(), nullable=True),
            sa.Column('source_message_id', sa.String(), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_workouts_id'), 'workouts', ['id'], unique=False)
        op.create_index(op.f('ix_workouts_user_id'), 'workouts', ['user_id'], unique=False)
        op.create_index(op.f('ix_workouts_source_message_id'), 'workouts', ['source_message_id'], unique=False)
        op.create_index('idx_workouts_performed_at', 'workouts', ['performed_at'], unique=False)
        op.create_index('idx_workouts_user_performed', 'workouts', ['user_id', 'performed_at'], unique=False)
        op.create_index('idx_workouts_deleted_at', 'workouts', ['deleted_at'], unique=False)

    if 'workout_exercises' not in existing_tables:
        op.create_table(
            'workout_exercises',
            sa.Column('workout_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('normalized_key', sa.String(), nullable=False),
            sa.Column('order_index', sa.Integer(), nullable=False),
            sa.Column('is_warmup', sa.Boolean(), nullable=False),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_workout_exercises_id'), 'workout_exercises', ['id'], unique=False)
        op.create_index(op.f('ix_workout_exercises_workout_id'), 'workout_exercises', ['workout_id'], unique=False)
        op.create_index(op.f('ix_workout_exercises_normalized_key'), 'workout_exercises', ['normalized_key'], unique=False)
        op.create_index('idx_workout_exercises_workout', 'workout_exercises', ['workout_id'], unique=False)
        op.create_index('idx_workout_exercises_normalized', 'workout_exercises', ['normalized_key'], unique=False)

    if 'workout_sets' not in existing_tables:
        op.create_table(
            'workout_sets',
            sa.Column('exercise_id', sa.Integer(), nullable=False),
            sa.Column('set_index', sa.Integer(), nullable=False),
            sa.Column('weight_kg', sa.Float(), nullable=True),
            sa.Column('reps', sa.Integer(), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('rir', sa.Integer(), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['exercise_id'], ['workout_exercises.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_workout_sets_id'), 'workout_sets', ['id'], unique=False)
        op.create_index(op.f('ix_workout_sets_exercise_id'), 'workout_sets', ['exercise_id'], unique=False)
        op.create_index('idx_workout_sets_exercise', 'workout_sets', ['exercise_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'workout_sets' in existing_tables:
        op.drop_table('workout_sets')
    if 'workout_exercises' in existing_tables:
        op.drop_table('workout_exercises')
    if 'workouts' in existing_tables:
        op.drop_table('workouts')
