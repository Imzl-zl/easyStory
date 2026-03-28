"""add assistant user preferences

Revision ID: b8d9f7c1a2e3
Revises: 3f2a6b9d1c44
Create Date: 2026-03-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b8d9f7c1a2e3"
down_revision = "3f2a6b9d1c44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_user_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("default_provider", sa.String(length=50), nullable=True),
        sa.Column("default_model_name", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_assistant_user_preferences_user_id"),
    )


def downgrade() -> None:
    op.drop_table("assistant_user_preferences")
