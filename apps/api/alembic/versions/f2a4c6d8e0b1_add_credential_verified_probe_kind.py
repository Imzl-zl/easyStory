"""add credential verified probe kind

Revision ID: f2a4c6d8e0b1
Revises: e1b2c3d4f5a6
Create Date: 2026-04-08 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

MODEL_CREDENTIALS_TABLE = "model_credentials"
VERIFIED_PROBE_KIND_COLUMN = "verified_probe_kind"


revision = "f2a4c6d8e0b1"
down_revision = "e1b2c3d4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _get_model_credential_columns()
    if VERIFIED_PROBE_KIND_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(VERIFIED_PROBE_KIND_COLUMN, sa.String(length=40), nullable=True),
        )


def downgrade() -> None:
    columns = _get_model_credential_columns()
    if VERIFIED_PROBE_KIND_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, VERIFIED_PROBE_KIND_COLUMN)


def _get_model_credential_columns() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(MODEL_CREDENTIALS_TABLE)
    }
