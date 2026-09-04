"""server-side timer: add started_at, procrastination_started_at, drop device_events

Revision ID: a1b2c3d4e5f6
Revises: 5b30abf7effb
Create Date: 2026-08-08 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5b30abf7effb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('day_plans', sa.Column('procrastination_started_at', sa.DateTime(timezone=True), nullable=True))

    op.alter_column('users', 'created_at', type_=sa.DateTime(timezone=True))
    op.alter_column('tasks', 'created_at', type_=sa.DateTime(timezone=True))
    op.alter_column('tasks', 'completed_at', type_=sa.DateTime(timezone=True))
    op.alter_column('coin_transactions', 'created_at', type_=sa.DateTime(timezone=True))
    op.alter_column('rewards', 'created_at', type_=sa.DateTime(timezone=True))

    op.drop_index(op.f('ix_device_events_occurred_at'), table_name='device_events')
    op.drop_index(op.f('ix_device_events_user_id'), table_name='device_events')
    op.drop_table('device_events')
    op.execute("DROP TYPE IF EXISTS eventtype")


def downgrade() -> None:
    op.create_table('device_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.Enum('TASK_CREATED', 'TASK_UPDATED', 'TASK_DELETED', 'TASK_STARTED', 'TASK_STOPPED', 'TASK_COMPLETED', 'TASK_SKIPPED', 'TASK_TRANSFERRED', name='eventtype'), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_events_occurred_at'), 'device_events', ['occurred_at'], unique=False)
    op.create_index(op.f('ix_device_events_user_id'), 'device_events', ['user_id'], unique=False)

    op.drop_column('day_plans', 'procrastination_started_at')
    op.drop_column('tasks', 'started_at')
