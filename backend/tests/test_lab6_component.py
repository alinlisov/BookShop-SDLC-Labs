"""Lab 6 component tests: HTTP API, validation, persistence and access control."""
from decimal import Decimal
from sqlalchemy import select

from app.models import Book, Order, OrderItem, Review, User
from app.security import decrypt_personal_data
from conftest import login_buyer, order_data, register_buyer


def test_component_catalog_http_json_and_missing_book(lab6_client):
    client, _ = lab6_client
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert len(response.json()) == 3
    assert response.json()[0]["title"] == "Весняні історії"
    assert client.get("/api/books?search=Весняні").json()[0]["id"] == 1
    assert client.get("/api/books/999").status_code == 404


def test_component_registration_email_encrypted_and_conflict(lab6_client):
    client, factory = lab6_client
    register_buyer(client)
    assert client.post("/api/auth/register", json={
        "full_name": "Інший Покупець", "email": "LAB6@example.com", "phone": "0501234567",
        "password": "StrongTestPass123!", "password_confirmation": "StrongTestPass123!",
    }).status_code == 409
    with factory() as db:
        users = db.scalars(select(User)).all()
        assert len(users) == 1
        assert "lab6@example.com" not in users[0].email_encrypted
        assert decrypt_personal_data(users[0].email_encrypted) == "lab6@example.com"


def test_component_profile_address_persists_and_requires_token(lab6_client):
    client, factory = lab6_client
    register_buyer(client)
    assert client.patch("/api/auth/me/address", json={"address": "м. Київ, вул. Тестова, 1"}).status_code == 401
    headers = login_buyer(client)
    address = "Хмельницька, м. Хмельницький, вул. Тестова, 10"
    saved = client.patch("/api/auth/me/address", json={"address": address}, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["address"] == address
    assert client.get("/api/auth/me", headers=headers).json()["address"] == address
    with factory() as db:
        encrypted = db.scalar(select(User)).address_encrypted
        assert encrypted != address
        assert decrypt_personal_data(encrypted) == address


def test_component_orders_use_server_prices_and_encrypt_address(lab6_client):
    client, factory = lab6_client
    order = order_data(email="guest@example.com", quantity=3)
    created = client.post("/api/orders", json=order)
    assert created.status_code == 201, created.text
    assert created.json()["total_amount"] == "361.50"
    assert "address" not in created.json()
    assert "email" not in created.json()
    with factory() as db:
        row = db.scalar(select(Order))
        assert row.total_amount == Decimal("361.50")
        assert decrypt_personal_data(row.delivery_address_encrypted) == order["address"]
        assert len(db.scalars(select(OrderItem)).all()) == 1


def test_component_unavailable_book_does_not_create_order(lab6_client):
    client, factory = lab6_client
    response = client.post("/api/orders", json=order_data(email="guest@example.com", book_id=3))
    assert response.status_code == 409
    with factory() as db:
        assert db.scalars(select(Order)).all() == []


def test_component_review_requires_login_and_prevents_duplicate(lab6_client):
    client, factory = lab6_client
    review = {"comment_text": "Чудовий сюжет і приємна мова"}
    assert client.post("/api/books/1/reviews", json=review).status_code == 401
    register_buyer(client)
    headers = login_buyer(client)
    created = client.post("/api/books/1/reviews", json=review, headers=headers)
    assert created.status_code == 201, created.text
    assert client.post("/api/books/1/reviews", json=review, headers=headers).status_code == 409
    assert len(client.get("/api/books/1/reviews").json()) == 1
    with factory() as db:
        assert len(db.scalars(select(Review)).all()) == 1


def test_component_admin_rejects_customer_permissions(lab6_client):
    client, _ = lab6_client
    register_buyer(client)
    headers = login_buyer(client)
    assert client.get("/api/admin/orders", headers=headers).status_code == 403
    assert client.post("/api/admin/books", headers=headers, json={
        "title": "Заборонена книга", "author": "Автор", "genre": "Роман", "price": "70.00"
    }).status_code == 403
    assert client.get("/api/auth/admin-check", headers=headers).status_code == 403


def test_component_logout_invalidates_api_session(lab6_client):
    client, _ = lab6_client
    register_buyer(client)
    headers = login_buyer(client)
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
