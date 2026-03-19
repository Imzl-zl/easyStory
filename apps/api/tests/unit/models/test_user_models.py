import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.user.models import User


def test_user_creation(db):
    user = User(username="testuser", hashed_password="hashed123")
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.username == "testuser"
    assert user.id is not None
    assert user.is_active is True
    assert user.created_at is not None


def test_user_unique_username(db):
    db.add(User(username="unique_user", hashed_password="x"))
    db.commit()
    db.add(User(username="unique_user", hashed_password="y"))

    with pytest.raises(IntegrityError):
        db.commit()


def test_user_optional_email(db):
    user = User(username="no_email", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.email is None


def test_user_with_email(db):
    user = User(
        username="has_email",
        hashed_password="x",
        email="test@example.com",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.email == "test@example.com"
