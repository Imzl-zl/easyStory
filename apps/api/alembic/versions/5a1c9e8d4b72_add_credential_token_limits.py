"""add credential token limits

Revision ID: 5a1c9e8d4b72
Revises: b8d9f7c1a2e3
Create Date: 2026-03-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

MODEL_CREDENTIALS_TABLE = "model_credentials"
CONTEXT_WINDOW_TOKENS_COLUMN = "context_window_tokens"
DEFAULT_MAX_OUTPUT_TOKENS_COLUMN = "default_max_output_tokens"


revision = "5a1c9e8d4b72"
down_revision = "b8d9f7c1a2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _get_model_credential_columns()
    if CONTEXT_WINDOW_TOKENS_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(CONTEXT_WINDOW_TOKENS_COLUMN, sa.Integer(), nullable=True),
        )
    if DEFAULT_MAX_OUTPUT_TOKENS_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(DEFAULT_MAX_OUTPUT_TOKENS_COLUMN, sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    columns = _get_model_credential_columns()
    if DEFAULT_MAX_OUTPUT_TOKENS_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, DEFAULT_MAX_OUTPUT_TOKENS_COLUMN)
    if CONTEXT_WINDOW_TOKENS_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, CONTEXT_WINDOW_TOKENS_COLUMN)


def _get_model_credential_columns() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(MODEL_CREDENTIALS_TABLE)
    }
