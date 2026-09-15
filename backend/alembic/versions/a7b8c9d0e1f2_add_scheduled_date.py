"""add scheduled_date to tasks

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tasks", sa.Column("scheduled_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("tasks", "scheduled_date")
