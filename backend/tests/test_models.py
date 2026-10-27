from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import Book, Order, OrderItem, Review, User


def test_all_tables_created():
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with engine.connect() as connection:
        from sqlalchemy import inspect
        assert {"users", "books", "orders", "order_items", "reviews"}.issubset(set(inspect(connection).get_table_names()))
    engine.dispose()


def test_order_relationship_and_amount():
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        book = Book(title="Тест", author="Автор", genre="Роман", price=Decimal("120.00"))
        db.add(book)
        db.flush()
        order = Order(customer_name="Тестовий покупець", customer_email_encrypted="encrypted", customer_phone_encrypted="encrypted", delivery_address_encrypted="encrypted", total_amount=Decimal("240.00"))
        order.items.append(OrderItem(book=book, quantity=2, price_per_item=book.price))
        db.add(order)
        db.commit()
        assert order.items[0].book_id == book.id
        assert order.total_amount == Decimal("240.00")
    engine.dispose()
