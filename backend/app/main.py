"""BookShop API + allow-listed static frontend, laboratory 5 stage 4."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers.auth import router as auth_router
from .routers.books import router as books_router, admin_router as admin_books_router
from .routers.orders import router as orders_router, admin_router as admin_orders_router
from .routers.reviews import router as reviews_router, admin_router as admin_reviews_router
from .web_pages import router as web_router, FRONTEND_ROOT


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do not drop tables or delete any existing PostgreSQL rows.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Інтернет-магазин книжок — API", version="0.5.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(books_router)
app.include_router(orders_router)
app.include_router(reviews_router)
app.include_router(admin_books_router)
app.include_router(admin_orders_router)
app.include_router(admin_reviews_router)


@app.get("/api/health", tags=["Система"])
def health():
    return {"status": "ok"}


# Explicit pages and public asset subdirectories only. Never expose the project
# root with StaticFiles: it contains backend/.env and other sensitive files.
app.include_router(web_router)
for asset_dir in ("css", "js", "covers"):
    folder = FRONTEND_ROOT / asset_dir
    if folder.is_dir():
        app.mount(f"/{asset_dir}", StaticFiles(directory=folder), name=f"assets_{asset_dir}")
