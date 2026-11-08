"""Serve only explicitly allowed frontend pages; never expose backend/.env."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

FRONTEND_ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(include_in_schema=False)

PAGES = ("index.html", "login.html", "register.html", "profile.html", "admin.html", "business.html")

@router.get("/")
@router.get("/index.html")
def home():
    page = FRONTEND_ROOT / "index.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="index.html не знайдено")
    return FileResponse(page)


def _register_page(filename: str) -> None:
    def serve_page():
        page = FRONTEND_ROOT / filename
        if not page.is_file():
            raise HTTPException(status_code=404, detail="Сторінку не знайдено")
        return FileResponse(page)
    router.add_api_route(f"/{filename}", serve_page, methods=["GET"], include_in_schema=False)

for name in PAGES[1:]:
    _register_page(name)
