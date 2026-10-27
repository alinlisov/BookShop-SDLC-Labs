from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import Book
from .schemas import BookOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Інтернет-магазин книжок — API", version="0.1.0", lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/books", response_model=list[BookOut])
def get_books(
    search: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
):
    query = select(Book).order_by(Book.id)
    if search.strip():
        query = query.where(Book.title.ilike(f"%{search.strip()}%"))
    return db.scalars(query).all()
