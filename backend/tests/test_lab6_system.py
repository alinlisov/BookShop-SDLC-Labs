"""Lab 6 end-to-end API workflows with isolated database (no real user data)."""
from sqlalchemy import select
from app.models import Book, Order, Review, User
from conftest import login_buyer, order_data, register_buyer


def test_system_customer_full_journey(lab6_client):
    client, factory = lab6_client
    # User path: catalog → registration → login → save address → buy → review → history → logout.
    assert client.get("/api/health").json() == {"status": "ok"}
    assert len(client.get("/api/books").json()) == 3
    register_buyer(client)
    headers = login_buyer(client)
    address = "Хмельницька, м. Хмельницький, вул. Тестова, 10"
    saved = client.patch("/api/auth/me/address", json={"address": address}, headers=headers)
    assert saved.status_code == 200, saved.text
    created = client.post("/api/orders", json=order_data(), headers=headers)
    assert created.status_code == 201, created.text
    assert created.json()["total_amount"] == "241.00"
    review = client.post("/api/books/1/reviews", headers=headers,
                         json={"comment_text": "Цікава книга, рекомендую."})
    assert review.status_code == 201, review.text
    history = client.get("/api/orders/mine", headers=headers)
    assert history.status_code == 200
    assert [entry["id"] for entry in history.json()] == [created.json()["id"]]
    assert client.get("/api/auth/me", headers=headers).json()["address"] == address
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/orders/mine", headers=headers).status_code == 401
    with factory() as db:
        assert len(db.scalars(select(Order)).all()) == 1
        assert len(db.scalars(select(Review)).all()) == 1


def test_system_two_customers_have_separate_order_history(lab6_client):
    client, _ = lab6_client
    first = "buyer-one@example.com"
    second = "buyer-two@example.com"
    register_buyer(client, email=first)
    token_one = login_buyer(client, email=first)
    first_order = client.post("/api/orders", json=order_data(email=first, book_id=1), headers=token_one)
    assert first_order.status_code == 201, first_order.text
    register_buyer(client, email=second)
    token_two = login_buyer(client, email=second)
    second_order = client.post("/api/orders", json=order_data(email=second, book_id=2), headers=token_two)
    assert second_order.status_code == 201, second_order.text
    ids1 = [item["id"] for item in client.get("/api/orders/mine", headers=token_one).json()]
    ids2 = [item["id"] for item in client.get("/api/orders/mine", headers=token_two).json()]
    assert ids1 == [first_order.json()["id"]]
    assert ids2 == [second_order.json()["id"]]
    assert ids1 != ids2
    assert client.get("/api/orders/mine").status_code == 401


def test_system_administrator_manages_book_order_and_review(lab6_client):
    client, factory = lab6_client
    register_buyer(client)
    with factory.begin() as db:
        db.scalar(select(User)).is_admin = True  # Only in isolated test DB.
    admin = login_buyer(client)
    created_book = client.post("/api/admin/books", headers=admin,
                               json={"title": "Нова книга", "author": "Новий автор", "genre": "Роман", "price": "85.50"})
    assert created_book.status_code == 201, created_book.text
    book_id = created_book.json()["id"]
    assert client.get(f"/api/books/{book_id}").status_code == 200
    created_order = client.post("/api/orders", headers=admin,
                                json=order_data(book_id=book_id, quantity=1))
    assert created_order.status_code == 201, created_order.text
    order_id = created_order.json()["id"]
    changed = client.patch(f"/api/admin/orders/{order_id}/status", headers=admin,
                           json={"status": "processing"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "processing"
    review = client.post(f"/api/books/{book_id}/reviews", headers=admin,
                         json={"comment_text": "Рекомендую для читання."})
    assert review.status_code == 201, review.text
    # A referenced book must not be deleted, but its availability can be changed.
    assert client.delete(f"/api/admin/books/{book_id}", headers=admin).status_code == 409
    patched = client.patch(f"/api/admin/books/{book_id}", headers=admin,
                           json={"is_available": False})
    assert patched.status_code == 200, patched.text
    assert patched.json()["is_available"] is False
    assert client.delete(f"/api/admin/reviews/{review.json()['id']}", headers=admin).status_code == 204
    with factory() as db:
        assert db.get(Book, book_id).is_available is False
