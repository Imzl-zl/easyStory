from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.modules import model_registry as _model_registry  # noqa: F401
from app.shared.db.base import Base

API_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_DIR = API_ROOT / "alembic"
ALEMBIC_INI = API_ROOT / "alembic.ini"
MODEL_CREDENTIALS_REQUIRED_COLUMNS = {"api_dialect", "default_model"}


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


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", database_url)
    return config
