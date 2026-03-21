import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.modules import model_registry as _model_registry  # noqa: F401
from app.shared.db.base import Base
from app.shared.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def reset_settings_cache():
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session
