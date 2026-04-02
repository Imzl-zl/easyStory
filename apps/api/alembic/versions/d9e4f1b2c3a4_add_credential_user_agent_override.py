"""add credential user agent override

Revision ID: d9e4f1b2c3a4
Revises: c4d7e8f9a1b2
Create Date: 2026-04-02 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

MODEL_CREDENTIALS_TABLE = "model_credentials"
USER_AGENT_OVERRIDE_COLUMN = "user_agent_override"


revision = "d9e4f1b2c3a4"
down_revision = "c4d7e8f9a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _get_model_credential_columns()
    if USER_AGENT_OVERRIDE_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(USER_AGENT_OVERRIDE_COLUMN, sa.String(length=300), nullable=True),
        )


def downgrade() -> None:
    columns = _get_model_credential_columns()
    if USER_AGENT_OVERRIDE_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, USER_AGENT_OVERRIDE_COLUMN)


def _get_model_credential_columns() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(MODEL_CREDENTIALS_TABLE)
    }
