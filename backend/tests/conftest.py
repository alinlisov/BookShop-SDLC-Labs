"""Fixtures used by Lab 6. Database isolation: never connects to user's PostgreSQL."""
import base64
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Book
from decimal import Decimal


def _new_key():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


@pytest.fixture
def lab6_keys(monkeypatch):
    """All secrets are ephemeral; real .env and PostgreSQL are never changed."""
    for variable in ("DATA_ENCRYPTION_KEY", "EMAIL_LOOKUP_KEY", "AUTH_SIGNING_KEY"):
        monkeypatch.setenv(variable, _new_key())


@pytest.fixture
def lab6_client(lab6_keys):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False)

    def isolated_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = isolated_db
    with factory.begin() as session:
        session.add_all([
            Book(title="Весняні історії", author="Автор А", genre="Роман", price=Decimal("120.50")),
            Book(title="Нічні історії", author="Автор Б", genre="Детектив", price=Decimal("200.00")),
            Book(title="Недоступна книга", author="Автор В", genre="Фантастика",
                 price=Decimal("50.00"), is_available=False),
        ])
    try:
        # Avoid starting FastAPI lifespan: it would try to initialize user's configured DB.
        client = TestClient(app)
        yield client, factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def register_buyer(client, email="lab6@example.com", phone="0501234567"):
    result = client.post("/api/auth/register", json={
        "full_name": "Тестовий Покупець", "email": email, "phone": phone,
        "password": "StrongTestPass123!", "password_confirmation": "StrongTestPass123!",
    })
    assert result.status_code == 201, result.text
    return result.json()


def login_buyer(client, email="lab6@example.com"):
    result = client.post("/api/auth/login", json={"email": email, "password": "StrongTestPass123!"})
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def order_data(email="lab6@example.com", book_id=1, quantity=2):
    return {
        "full_name": "Тестовий Покупець", "email": email, "phone": "0501234567",
        "address": "Хмельницька, м. Хмельницький, вул. Тестова, 10",
        "items": [{"book_id": book_id, "quantity": quantity}],
    }
