"""add credential connection overrides

Revision ID: 97c3e2dcb2f1
Revises: 6df7d5dfd8d7
Create Date: 2026-03-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "97c3e2dcb2f1"
down_revision = "6df7d5dfd8d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_credentials", sa.Column("auth_strategy", sa.String(length=50), nullable=True))
    op.add_column(
        "model_credentials",
        sa.Column("api_key_header_name", sa.String(length=100), nullable=True),
    )
    op.add_column("model_credentials", sa.Column("extra_headers", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("model_credentials", "extra_headers")
    op.drop_column("model_credentials", "api_key_header_name")
    op.drop_column("model_credentials", "auth_strategy")
