"""add timezone to user_settings

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_settings",
        sa.Column("timezone", sa.String(), server_default="UTC", nullable=False),
    )


def downgrade():
    op.drop_column("user_settings", "timezone")
