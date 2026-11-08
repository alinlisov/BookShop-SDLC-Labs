"""Public reviews, authenticated posting and administrator moderation."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import Authenticated, require_admin, require_authentication
from ..models import Book, Review
from ..schemas import ReviewCreate, ReviewOut

router = APIRouter(prefix="/api/books/{book_id}/reviews", tags=["Відгуки"])
admin_router = APIRouter(prefix="/api/admin/reviews", tags=["Модерація відгуків"])


def _require_book(book_id: int, db: Session):
    if db.get(Book, book_id) is None:
        raise HTTPException(status_code=404, detail="Книжку не знайдено")


@router.get("", response_model=list[ReviewOut])
def list_reviews(book_id: int, db: Session = Depends(get_db)):
    _require_book(book_id, db)
    return db.scalars(select(Review).where(Review.book_id == book_id)
                      .order_by(Review.created_at.desc(), Review.id.desc())).all()


@router.post("", response_model=ReviewOut, status_code=201)
def add_review(
    book_id: int, payload: ReviewCreate,
    identity: Authenticated = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    _require_book(book_id, db)
    existing = db.scalar(select(Review.id).where(Review.book_id == book_id,
                                                Review.user_id == identity.user.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Відгук до цієї книжки вже залишено")
    review = Review(book_id=book_id, user_id=identity.user.id,
                    author_name=identity.user.full_name, comment_text=payload.comment_text)
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Відгук до цієї книжки вже залишено")
    db.refresh(review)
    return review


@admin_router.delete("/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    _: Authenticated = Depends(require_admin),
    db: Session = Depends(get_db),
):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Відгук не знайдено")
    db.delete(review)
    db.commit()
    return None
