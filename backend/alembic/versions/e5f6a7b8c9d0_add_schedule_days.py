"""add schedule_days to tasks

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tasks", sa.Column("schedule_days", sa.String(), nullable=True))


def downgrade():
    op.drop_column("tasks", "schedule_days")
