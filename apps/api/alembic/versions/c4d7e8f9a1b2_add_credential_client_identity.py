"""add credential client identity

Revision ID: c4d7e8f9a1b2
Revises: 5a1c9e8d4b72
Create Date: 2026-04-02 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

MODEL_CREDENTIALS_TABLE = "model_credentials"
CLIENT_NAME_COLUMN = "client_name"
CLIENT_VERSION_COLUMN = "client_version"
RUNTIME_KIND_COLUMN = "runtime_kind"


revision = "c4d7e8f9a1b2"
down_revision = "5a1c9e8d4b72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _get_model_credential_columns()
    if CLIENT_NAME_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(CLIENT_NAME_COLUMN, sa.String(length=100), nullable=True),
        )
    if CLIENT_VERSION_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(CLIENT_VERSION_COLUMN, sa.String(length=50), nullable=True),
        )
    if RUNTIME_KIND_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(RUNTIME_KIND_COLUMN, sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    columns = _get_model_credential_columns()
    if RUNTIME_KIND_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, RUNTIME_KIND_COLUMN)
    if CLIENT_VERSION_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, CLIENT_VERSION_COLUMN)
    if CLIENT_NAME_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, CLIENT_NAME_COLUMN)


def _get_model_credential_columns() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(MODEL_CREDENTIALS_TABLE)
    }
