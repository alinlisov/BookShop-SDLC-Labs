"""FR-4.3 + NFR-2.2: profile address editing; isolated in-memory DB."""
import base64
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import decrypt_personal_data


def key():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


@pytest.fixture
def context(monkeypatch):
    for variable in ("DATA_ENCRYPTION_KEY", "EMAIL_LOOKUP_KEY", "AUTH_SIGNING_KEY"):
        monkeypatch.setenv(variable, key())
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def dependency():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = dependency
    try:
        yield TestClient(app), factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def register_and_login(client):
    result = client.post("/api/auth/register", json={
        "full_name": "Тестова Покупчиня", "email": "address-test@example.com", "phone": "0501234567",
        "password": "StrongPassword123!", "password_confirmation": "StrongPassword123!"
    })
    assert result.status_code == 201, result.text
    result = client.post("/api/auth/login", json={"email": "address-test@example.com", "password": "StrongPassword123!"})
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def test_profile_address_saved_encrypted_and_returned(context):
    client, factory = context
    headers = register_and_login(client)
    original = client.get("/api/auth/me", headers=headers)
    assert original.status_code == 200 and original.json()["address"] is None
    address = "Хмельницька, м. Хмельницький, вул. Тестова, 10"
    updated = client.patch("/api/auth/me/address", headers=headers, json={"address": address})
    assert updated.status_code == 200, updated.text
    assert updated.json()["address"] == address
    assert client.get("/api/auth/me", headers=headers).json()["address"] == address
    with factory() as session:
        stored = session.scalar(select(User)).address_encrypted
        assert stored != address and "Хмельницька" not in stored
        assert decrypt_personal_data(stored) == address


def test_profile_address_requires_authentication(context):
    client, _ = context
    response = client.patch("/api/auth/me/address", json={"address": "Хмельницька, м. Хмельницький"})
    assert response.status_code == 401


def test_short_address_rejected_without_change(context):
    client, _ = context
    headers = register_and_login(client)
    response = client.patch("/api/auth/me/address", headers=headers, json={"address": "    "})
    assert response.status_code == 422
    assert client.get("/api/auth/me", headers=headers).json()["address"] is None
