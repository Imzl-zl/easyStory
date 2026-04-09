"""add credential transport tool verification

Revision ID: a7b8c9d0e1f2
Revises: f2a4c6d8e0b1
Create Date: 2026-04-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

MODEL_CREDENTIALS_TABLE = "model_credentials"
VERIFIED_PROBE_KIND_COLUMN = "verified_probe_kind"
LAST_VERIFIED_AT_COLUMN = "last_verified_at"
STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN = "stream_tool_verified_probe_kind"
STREAM_TOOL_LAST_VERIFIED_AT_COLUMN = "stream_tool_last_verified_at"
BUFFERED_TOOL_VERIFIED_PROBE_KIND_COLUMN = "buffered_tool_verified_probe_kind"
BUFFERED_TOOL_LAST_VERIFIED_AT_COLUMN = "buffered_tool_last_verified_at"
TOOL_PROBE_KINDS = ("tool_definition_probe", "tool_call_probe", "tool_continuation_probe")


revision = "a7b8c9d0e1f2"
down_revision = "f2a4c6d8e0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = _get_model_credential_columns()
    if STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN, sa.String(length=40), nullable=True),
        )
    if STREAM_TOOL_LAST_VERIFIED_AT_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(STREAM_TOOL_LAST_VERIFIED_AT_COLUMN, sa.DateTime(timezone=True), nullable=True),
        )
    if BUFFERED_TOOL_VERIFIED_PROBE_KIND_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(BUFFERED_TOOL_VERIFIED_PROBE_KIND_COLUMN, sa.String(length=40), nullable=True),
        )
    if BUFFERED_TOOL_LAST_VERIFIED_AT_COLUMN not in columns:
        op.add_column(
            MODEL_CREDENTIALS_TABLE,
            sa.Column(BUFFERED_TOOL_LAST_VERIFIED_AT_COLUMN, sa.DateTime(timezone=True), nullable=True),
        )
    _backfill_stream_tool_verification_state()


def downgrade() -> None:
    columns = _get_model_credential_columns()
    if BUFFERED_TOOL_LAST_VERIFIED_AT_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, BUFFERED_TOOL_LAST_VERIFIED_AT_COLUMN)
    if BUFFERED_TOOL_VERIFIED_PROBE_KIND_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, BUFFERED_TOOL_VERIFIED_PROBE_KIND_COLUMN)
    if STREAM_TOOL_LAST_VERIFIED_AT_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, STREAM_TOOL_LAST_VERIFIED_AT_COLUMN)
    if STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN in columns:
        op.drop_column(MODEL_CREDENTIALS_TABLE, STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN)


def _backfill_stream_tool_verification_state() -> None:
    op.get_bind().execute(
        sa.text(
            f"""
            UPDATE {MODEL_CREDENTIALS_TABLE}
            SET
                {STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN} = CASE
                    WHEN {STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN} IS NULL
                        AND {VERIFIED_PROBE_KIND_COLUMN} IN :tool_probe_kinds
                    THEN {VERIFIED_PROBE_KIND_COLUMN}
                    ELSE {STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN}
                END,
                {STREAM_TOOL_LAST_VERIFIED_AT_COLUMN} = CASE
                    WHEN {STREAM_TOOL_LAST_VERIFIED_AT_COLUMN} IS NULL
                        AND {VERIFIED_PROBE_KIND_COLUMN} IN :tool_probe_kinds
                    THEN {LAST_VERIFIED_AT_COLUMN}
                    ELSE {STREAM_TOOL_LAST_VERIFIED_AT_COLUMN}
                END
            """
        ).bindparams(sa.bindparam("tool_probe_kinds", expanding=True)),
        {"tool_probe_kinds": TOOL_PROBE_KINDS},
    )


def _get_model_credential_columns() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(MODEL_CREDENTIALS_TABLE)
    }
