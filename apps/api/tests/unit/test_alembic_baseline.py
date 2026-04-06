from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.modules import model_registry as _model_registry  # noqa: F401
from app.shared.db.base import Base

API_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_DIR = API_ROOT / "alembic"
ALEMBIC_INI = API_ROOT / "alembic.ini"
MODEL_CREDENTIALS_REQUIRED_COLUMNS = {
    "api_dialect",
    "context_window_tokens",
    "default_max_output_tokens",
    "default_model",
}


def test_alembic_upgrade_head_matches_current_metadata(tmp_path) -> None:
    database_path = tmp_path / "alembic-baseline.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _build_alembic_config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    try:
        assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
        columns = {column["name"] for column in inspector.get_columns("model_credentials")}
        assert MODEL_CREDENTIALS_REQUIRED_COLUMNS <= columns
    finally:
        engine.dispose()

    command.check(config)


def test_alembic_upgrade_head_tolerates_preexisting_credential_token_columns(tmp_path) -> None:
    database_path = tmp_path / "alembic-preexisting-token-columns.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _build_alembic_config(database_url)

    command.upgrade(config, "b8d9f7c1a2e3")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE model_credentials ADD COLUMN context_window_tokens INTEGER")
            )
            connection.execute(
                text("ALTER TABLE model_credentials ADD COLUMN default_max_output_tokens INTEGER")
            )
        command.upgrade(config, "head")
        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("model_credentials")}
        assert MODEL_CREDENTIALS_REQUIRED_COLUMNS <= columns
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                _resolve_alembic_head_revision(config)
            )
    finally:
        engine.dispose()


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _resolve_alembic_head_revision(config: Config) -> str:
    return str(ScriptDirectory.from_config(config).get_current_head())
