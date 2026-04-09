from __future__ import annotations

from sqlalchemy import bindparam, inspect, text
from sqlalchemy.engine import Connection

MODEL_CREDENTIALS_TABLE = "model_credentials"
API_DIALECT_COLUMN = "api_dialect"
DEFAULT_MODEL_COLUMN = "default_model"
INTEROP_PROFILE_COLUMN = "interop_profile"
VERIFIED_PROBE_KIND_COLUMN = "verified_probe_kind"
STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN = "stream_tool_verified_probe_kind"
STREAM_TOOL_LAST_VERIFIED_AT_COLUMN = "stream_tool_last_verified_at"
BUFFERED_TOOL_VERIFIED_PROBE_KIND_COLUMN = "buffered_tool_verified_probe_kind"
BUFFERED_TOOL_LAST_VERIFIED_AT_COLUMN = "buffered_tool_last_verified_at"
CONTEXT_WINDOW_TOKENS_COLUMN = "context_window_tokens"
DEFAULT_MAX_OUTPUT_TOKENS_COLUMN = "default_max_output_tokens"
CLIENT_NAME_COLUMN = "client_name"
CLIENT_VERSION_COLUMN = "client_version"
RUNTIME_KIND_COLUMN = "runtime_kind"
USER_AGENT_OVERRIDE_COLUMN = "user_agent_override"
LAST_VERIFIED_AT_COLUMN = "last_verified_at"
OPENAI_CHAT_DIALECT = "openai_chat_completions"
ANTHROPIC_MESSAGES_DIALECT = "anthropic_messages"
ANTHROPIC_PROVIDER = "anthropic"
TOOL_PROBE_KINDS = ("tool_definition_probe", "tool_call_probe", "tool_continuation_probe")


def reconcile_model_credentials_schema(connection: Connection) -> None:
    inspector = inspect(connection)
    if MODEL_CREDENTIALS_TABLE not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns(MODEL_CREDENTIALS_TABLE)}
    _add_missing_model_credential_columns(connection, columns)
    _backfill_model_credential_api_dialect(connection)
    _backfill_model_credential_tool_verification_state(connection)


def _add_missing_model_credential_columns(
    connection: Connection,
    columns: set[str],
) -> None:
    _add_missing_column(connection, columns, API_DIALECT_COLUMN, "VARCHAR(50)")
    _add_missing_column(connection, columns, DEFAULT_MODEL_COLUMN, "VARCHAR(100)")
    _add_missing_column(connection, columns, INTEROP_PROFILE_COLUMN, "VARCHAR(80)")
    _add_missing_column(connection, columns, VERIFIED_PROBE_KIND_COLUMN, "VARCHAR(40)")
    _add_missing_column(connection, columns, STREAM_TOOL_VERIFIED_PROBE_KIND_COLUMN, "VARCHAR(40)")
    _add_missing_column(connection, columns, STREAM_TOOL_LAST_VERIFIED_AT_COLUMN, "DATETIME")
    _add_missing_column(connection, columns, BUFFERED_TOOL_VERIFIED_PROBE_KIND_COLUMN, "VARCHAR(40)")
    _add_missing_column(connection, columns, BUFFERED_TOOL_LAST_VERIFIED_AT_COLUMN, "DATETIME")
    _add_missing_column(connection, columns, CONTEXT_WINDOW_TOKENS_COLUMN, "INTEGER")
    _add_missing_column(connection, columns, DEFAULT_MAX_OUTPUT_TOKENS_COLUMN, "INTEGER")
    _add_missing_column(connection, columns, CLIENT_NAME_COLUMN, "VARCHAR(100)")
    _add_missing_column(connection, columns, CLIENT_VERSION_COLUMN, "VARCHAR(50)")
    _add_missing_column(connection, columns, RUNTIME_KIND_COLUMN, "VARCHAR(50)")
    _add_missing_column(connection, columns, USER_AGENT_OVERRIDE_COLUMN, "VARCHAR(300)")


def _add_missing_column(
    connection: Connection,
    columns: set[str],
    column_name: str,
    column_type_sql: str,
) -> None:
    if column_name in columns:
        return
    connection.execute(
        text(
            f"ALTER TABLE {MODEL_CREDENTIALS_TABLE} "
            f"ADD COLUMN {column_name} {column_type_sql}"
        )
    )
    columns.add(column_name)


def _backfill_model_credential_api_dialect(connection: Connection) -> None:
    connection.execute(
        text(
            f"""
            UPDATE {MODEL_CREDENTIALS_TABLE}
            SET {API_DIALECT_COLUMN} = CASE
                WHEN lower(provider) = :anthropic_provider THEN :anthropic_dialect
                ELSE :default_dialect
            END
            WHERE {API_DIALECT_COLUMN} IS NULL OR trim({API_DIALECT_COLUMN}) = ''
            """
        ),
        {
            "anthropic_provider": ANTHROPIC_PROVIDER,
            "anthropic_dialect": ANTHROPIC_MESSAGES_DIALECT,
            "default_dialect": OPENAI_CHAT_DIALECT,
        },
    )


def _backfill_model_credential_tool_verification_state(connection: Connection) -> None:
    connection.execute(
        text(
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
        ).bindparams(bindparam("tool_probe_kinds", expanding=True)),
        {"tool_probe_kinds": TOOL_PROBE_KINDS},
    )
