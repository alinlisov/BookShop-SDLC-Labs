"""Add sample books. Safe to run multiple times."""
from decimal import Decimal
from sqlalchemy import select
from .database import Base, SessionLocal, engine
from .models import Book  # imports the remaining models as well

SAMPLE_BOOKS = [
    {"title": "Тестова книга 1", "author": "Приклад автора", "genre": "Роман", "price": Decimal("250.00")},
    {"title": "Тестова книга 2", "author": "Другий автор", "genre": "Фантастика", "price": Decimal("320.00")},
    {"title": "Тестова книга 3", "author": "Третій автор", "genre": "Детектив", "price": Decimal("199.00")},
]


def seed():
    Base.metadata.create_all(bind=engine)
    with SessionLocal.begin() as db:
        added = 0
        for data in SAMPLE_BOOKS:
            existing = db.scalar(select(Book.id).where(Book.title == data["title"], Book.author == data["author"]))
            if existing is None:
                db.add(Book(**data))
                added += 1
    print(f"Додано книжок: {added}")


if __name__ == "__main__":
    seed()
