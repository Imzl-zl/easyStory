"""add assistant rule profiles

Revision ID: 3f2a6b9d1c44
Revises: 97c3e2dcb2f1
Create Date: 2026-03-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "3f2a6b9d1c44"
down_revision = "97c3e2dcb2f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_rule_profiles",
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_type", "owner_id", name="uq_assistant_rule_profiles_owner"),
    )


def downgrade() -> None:
    op.drop_table("assistant_rule_profiles")
