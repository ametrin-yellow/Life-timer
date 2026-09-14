"""add google_id and telegram_id to users, make hashed_password nullable

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-14 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('google_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)
    op.add_column('users', sa.Column('telegram_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)
    op.alter_column('users', 'hashed_password', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'hashed_password', existing_type=sa.String(), nullable=False)
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_column('users', 'telegram_id')
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_column('users', 'google_id')
