import base64
from decimal import Decimal
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Book, Order, OrderItem, Review, User
from app.security import decrypt_personal_data


def make_key():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


@pytest.fixture
def system(monkeypatch):
    for name in ("DATA_ENCRYPTION_KEY", "EMAIL_LOOKUP_KEY", "AUTH_SIGNING_KEY"):
        monkeypatch.setenv(name, make_key())
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def overridden_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = overridden_db
    with factory.begin() as db:
        db.add_all([
            Book(title="Spring Stories", author="Author A", genre="Роман", price=Decimal("125.50")),
            Book(title="Winter Nights", author="Author B", genre="Детектив", price=Decimal("299.00")),
            Book(title="Hidden Tales", author="Author C", genre="Фантастика", price=Decimal("50.00"), is_available=False),
        ])
    try:
        yield TestClient(app), factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def register(client, email="test@example.com"):
    data = {"full_name": "Тестова Покупчиня", "email": email, "phone": "0501234567",
            "password": "StrongTestPassword123!", "password_confirmation": "StrongTestPassword123!"}
    response = client.post("/api/auth/register", json=data)
    assert response.status_code == 201, response.text
    return response.json()


def token(client, email="test@example.com"):
    response = client.post("/api/auth/login", json={"email": email, "password": "StrongTestPassword123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def checkout(items=None, email="guest@example.com"):
    return {"full_name": "Гість Покупець", "email": email, "phone": "0501234567",
            "address": "м. Київ, вулиця Прикладна, 10", "items": items or [{"book_id": 1, "quantity": 2}]}


def test_catalog_list_details_and_search(system):
    client, _ = system
    assert len(client.get("/api/books").json()) == 3
    assert client.get("/api/books?search=Spring").json()[0]["id"] == 1
    assert client.get("/api/books/1").json()["title"] == "Spring Stories"
    assert client.get("/api/books/1000").status_code == 404
    assert client.get("/api/books?search=%25").json() == []  # wildcard escaped


def test_admin_books_cannot_be_changed_by_guest_or_buyer(system):
    client, _ = system
    assert client.post("/api/admin/books", json={"title":"X", "author":"Y","genre":"Z","price":"50"}).status_code == 401
    register(client)
    assert client.delete("/api/admin/books/1", headers=token(client)).status_code == 403


def test_admin_books_crud(system):
    client, factory = system
    register(client)
    with factory.begin() as db:
        db.scalar(select(User)).is_admin = True
    auth = token(client)
    response = client.post("/api/admin/books", json={"title":"Another","author":"Writer", "genre":"Роман", "price":"250.00"}, headers=auth)
    assert response.status_code == 201, response.text
    book_id = response.json()["id"]
    edited = client.patch(f"/api/admin/books/{book_id}", json={"price":"230.50", "is_available":False}, headers=auth)
    assert edited.status_code == 200 and edited.json()["price"] == "230.50"
    assert client.patch(f"/api/admin/books/{book_id}", json={"price":None}, headers=auth).status_code == 422
    assert client.delete(f"/api/admin/books/{book_id}", headers=auth).status_code == 204
    assert client.get(f"/api/books/{book_id}").status_code == 404


def test_guest_order_total_and_encryption(system):
    client, factory = system
    response = client.post("/api/orders", json=checkout([{"book_id":1,"quantity":2},{"book_id":2,"quantity":1}]))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["total_amount"] == "550.00" and len(body["items"]) == 2
    assert "email" not in body and "phone" not in body
    with factory() as db:
        order = db.scalar(select(Order))
        assert order.user_id is None
        assert order.customer_email_encrypted != "guest@example.com"
        assert decrypt_personal_data(order.customer_email_encrypted) == "guest@example.com"
        assert decrypt_personal_data(order.customer_phone_encrypted) == "+380501234567"
        assert len(db.scalars(select(OrderItem)).all()) == 2
        assert order.total_amount == Decimal("550.00")


def test_order_unknown_book_and_unavailable_book(system):
    client, factory = system
    assert client.post("/api/orders", json=checkout([{"book_id":999,"quantity":1}])).status_code == 404
    assert client.post("/api/orders", json=checkout([{"book_id":3,"quantity":1}])).status_code == 409
    with factory() as db: assert db.scalars(select(Order)).all() == []


@pytest.mark.parametrize("items", [[], [{"book_id":1,"quantity":0}],
                                   [{"book_id":1,"quantity":1}, {"book_id":1,"quantity":2}]])
def test_order_rejects_invalid_items(system, items):
    client, _ = system
    data = checkout(); data["items"] = items
    assert client.post("/api/orders", json=data).status_code == 422


def test_orders_are_linked_to_authenticated_profile(system):
    client, factory = system
    register(client)
    auth = token(client)
    wrong_email = client.post("/api/orders", json=checkout(email="other@example.com"), headers=auth)
    assert wrong_email.status_code == 422
    created = client.post("/api/orders", json=checkout(email="test@example.com"), headers=auth)
    assert created.status_code == 201, created.text
    mine = client.get("/api/orders/mine", headers=auth)
    assert mine.status_code == 200 and len(mine.json()) == 1
    assert mine.json()[0]["id"] == created.json()["id"]
    assert client.get("/api/orders/mine").status_code == 401
    client.post("/api/orders", json=checkout(email="guest@example.com"))
    assert len(client.get("/api/orders/mine", headers=auth).json()) == 1


def test_reviews_require_login_and_are_persistent(system):
    client, factory = system
    assert client.post("/api/books/1/reviews", json={"comment_text":"Чудова книга"}).status_code == 401
    register(client); auth = token(client)
    created = client.post("/api/books/1/reviews", json={"comment_text":"  Чудова книга!  "}, headers=auth)
    assert created.status_code == 201, created.text
    assert created.json()["comment_text"] == "Чудова книга!"
    assert client.post("/api/books/1/reviews", json={"comment_text":"ще відгук"}, headers=auth).status_code == 409
    response = client.get("/api/books/1/reviews")
    assert response.status_code == 200 and len(response.json()) == 1
    with factory() as db:
        assert len(db.scalars(select(Review)).all()) == 1


def test_reviews_validate_comment_and_book(system):
    client,_ = system
    register(client); auth = token(client)
    assert client.post("/api/books/1/reviews", json={"comment_text":"  "}, headers=auth).status_code == 422
    assert client.post("/api/books/900/reviews", json={"comment_text":"Хороший текст"}, headers=auth).status_code == 404
    assert client.get("/api/books/900/reviews").status_code == 404


def test_admin_orders_status_and_customer_details(system):
    client, factory = system
    register(client)
    with factory.begin() as db: db.scalar(select(User)).is_admin = True
    auth = token(client)
    created = client.post("/api/orders", json=checkout())
    order_id = created.json()["id"]
    all_orders = client.get("/api/admin/orders", headers=auth)
    assert all_orders.status_code == 200
    assert all_orders.json()[0]["email"] == "guest@example.com"
    assert all_orders.json()[0]["address"] == "м. Київ, вулиця Прикладна, 10"
    first = client.patch(f"/api/admin/orders/{order_id}/status",json={"status":"processing"}, headers=auth)
    assert first.status_code == 200 and first.json()["status"] == "processing"
    second = client.patch(f"/api/admin/orders/{order_id}/status",json={"status":"approved"}, headers=auth)
    assert second.status_code == 200 and second.json()["status"] == "approved"
    assert client.patch(f"/api/admin/orders/{order_id}/status",json={"status":"new"}, headers=auth).status_code == 422
    assert client.patch(f"/api/admin/orders/{order_id}/status",json={"status":"cancelled"}, headers=auth).status_code == 409


def test_reviews_admin_moderation_and_book_delete_protection(system):
    client, factory = system
    register(client); user_auth = token(client)
    r = client.post("/api/books/1/reviews", json={"comment_text":"Гарна книжка"}, headers=user_auth)
    review_id = r.json()["id"]
    assert client.delete(f"/api/admin/reviews/{review_id}", headers=user_auth).status_code == 403
    with factory.begin() as db: db.scalar(select(User)).is_admin = True
    admin_auth = token(client)
    assert client.delete("/api/admin/books/1", headers=admin_auth).status_code == 409
    assert client.delete(f"/api/admin/reviews/{review_id}", headers=admin_auth).status_code == 204
    assert client.get("/api/books/1/reviews").json() == []


def test_admin_order_view_forbidden_to_buyer(system):
    client, _ = system
    register(client)
    assert client.get("/api/admin/orders", headers=token(client)).status_code == 403
