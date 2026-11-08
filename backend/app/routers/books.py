"""Book catalog with searchable listings and manager-only editing."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_admin
from ..models import Book, OrderItem, Review
from ..schemas import BookCreate, BookOut, BookUpdate

router = APIRouter(prefix="/api/books", tags=["Каталог книжок"])
admin_router = APIRouter(prefix="/api/admin/books", tags=["Адміністрування книжок"])


@router.get("", response_model=list[BookOut])
def list_books(search: str = Query(default="", max_length=100), db: Session = Depends(get_db)):
    statement = select(Book).order_by(Book.id)
    if search.strip():
        # Escape wildcard tokens so '%' and '_' are interpreted literally.
        term = search.strip().replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        statement = statement.where(Book.title.ilike(f"%{term}%", escape="\\"))
    return db.scalars(statement).all()


@router.get("/{book_id}", response_model=BookOut)
def book_details(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Книжку не знайдено")
    return book


@admin_router.post("", response_model=BookOut, status_code=201, dependencies=[Depends(require_admin)])
def add_book(payload: BookCreate, db: Session = Depends(get_db)):
    book = Book(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@admin_router.patch("/{book_id}", response_model=BookOut, dependencies=[Depends(require_admin)])
def edit_book(book_id: int, payload: BookUpdate, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Книжку не знайдено")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Вкажіть хоча б одне поле для зміни")
    for name, value in changes.items():
        if value is None and name != "cover":
            raise HTTPException(status_code=422, detail=f"Поле {name} не може бути порожнім")
        setattr(book, name, value)
    db.commit()
    db.refresh(book)
    return book


@admin_router.delete("/{book_id}", status_code=204, dependencies=[Depends(require_admin)])
def remove_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Книжку не знайдено")
    used_in_order = db.scalar(select(OrderItem.id).where(OrderItem.book_id == book_id).limit(1))
    has_reviews = db.scalar(select(Review.id).where(Review.book_id == book_id).limit(1))
    if used_in_order is not None or has_reviews is not None:
        raise HTTPException(status_code=409, detail="Книжка має замовлення або відгуки. Змініть наявність замість видалення")
    db.delete(book)
    db.commit()
    return None
