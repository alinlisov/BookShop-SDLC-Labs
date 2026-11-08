import base64
import secrets

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import decrypt_personal_data


def random_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


@pytest.fixture
def test_context(monkeypatch):
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", random_key())
    monkeypatch.setenv("EMAIL_LOOKUP_KEY", random_key())

    test_engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    sessions = sessionmaker(bind=test_engine)

    def override_get_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), sessions
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


def valid_registration():
    return {
        "full_name": "Тестова Покупчиня",
        "email": "test@example.com",
        "phone": "0501234567",
        "password": "TestPassword123!",
        "password_confirmation": "TestPassword123!",
    }


def test_registration_creates_encrypted_user(test_context):
    client, sessions = test_context
    response = client.post("/api/auth/register", json=valid_registration())
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["phone"] == "+380501234567"
    assert data["is_admin"] is False
    assert "password" not in data and "password_hash" not in data

    with sessions() as db:
        user = db.scalar(select(User))
        assert user is not None
        assert user.email_encrypted != "test@example.com"
        assert user.phone_encrypted != "+380501234567"
        assert decrypt_personal_data(user.email_encrypted) == "test@example.com"
        assert decrypt_personal_data(user.phone_encrypted) == "+380501234567"
        assert user.password_hash.startswith("$argon2id$")
        assert PasswordHasher().verify(user.password_hash, "TestPassword123!")


def test_duplicate_email_cannot_register_twice(test_context):
    client, sessions = test_context
    first = client.post("/api/auth/register", json=valid_registration())
    duplicate = valid_registration()
    duplicate["email"] = "TEST@example.com"
    second = client.post("/api/auth/register", json=duplicate)
    assert first.status_code == 201
    assert second.status_code == 409
    with sessions() as db:
        assert len(db.scalars(select(User)).all()) == 1


@pytest.mark.parametrize(
    "field,bad_value",
    [("email", "invalid-email"), ("phone", "123456"),
     ("password_confirmation", "NotTheSame"), ("password", "123")],
)
def test_registration_rejects_bad_data(test_context, field, bad_value):
    client, sessions = test_context
    data = valid_registration()
    data[field] = bad_value
    response = client.post("/api/auth/register", json=data)
    assert response.status_code == 422, response.text
    with sessions() as db:
        assert db.scalars(select(User)).first() is None
