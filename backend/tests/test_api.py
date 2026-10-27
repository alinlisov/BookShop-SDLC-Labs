from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import Book
from decimal import Decimal


def make_client():
    test_engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=test_engine)
    testing_session = sessionmaker(bind=test_engine)

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session, test_engine


def test_health():
    client, _, engine = make_client()
    try:
        with client:
            response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_books_and_search():
    client, sessions, engine = make_client()
    try:
        with sessions.begin() as db:
            db.add(Book(title="Зоря", author="Автор", genre="Роман", price=Decimal("150.00")))
            db.add(Book(title="Місто", author="Інший автор", genre="Детектив", price=Decimal("180.00")))
        with client:
            response = client.get("/api/books")
            filtered = client.get("/api/books", params={"search": "Зор"})
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert filtered.status_code == 200
        assert [item["title"] for item in filtered.json()] == ["Зоря"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
