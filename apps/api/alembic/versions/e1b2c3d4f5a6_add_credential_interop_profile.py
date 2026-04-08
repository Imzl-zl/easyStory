"""add credential interop profile

Revision ID: e1b2c3d4f5a6
Revises: d9e4f1b2c3a4
Create Date: 2026-04-08 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

MODEL_CREDENTIALS_TABLE = "model_credentials"
INTEROP_PROFILE_COLUMN = "interop_profile"


revision = "e1b2c3d4f5a6"
down_revision = "d9e4f1b2c3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _get_model_credential_columns()
    if INTEROP_PROFILE_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(INTEROP_PROFILE_COLUMN, sa.String(length=80), nullable=True),
        )


def downgrade() -> None:
    columns = _get_model_credential_columns()
    if INTEROP_PROFILE_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, INTEROP_PROFILE_COLUMN)


def _get_model_credential_columns() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(MODEL_CREDENTIALS_TABLE)
    }
