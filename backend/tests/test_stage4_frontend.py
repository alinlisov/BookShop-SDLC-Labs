
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.web_pages import FRONTEND_ROOT


def test_health_survives_frontend_integration():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page_and_same_origin_api_script():
    assert (FRONTEND_ROOT / "index.html").exists(), "Потрібна папка сайту поруч із backend"
    with TestClient(app, follow_redirects=False) as client:
        home = client.get("/")
        script = client.get("/js/api.js")
    assert home.status_code == 200
    assert 'id="books-container"' in home.text
    assert 'src="js/api.js"' in home.text
    assert script.status_code == 200
    assert '"/api/' in script.text


def test_frontend_serves_only_allowlisted_files():
    with TestClient(app, follow_redirects=False) as client:
        assert client.get("/login.html").status_code == 200
        assert client.get("/register.html").status_code == 200
        assert client.get("/profile.html").status_code == 200
        assert client.get("/admin.html").status_code == 200
        assert client.get("/backend/.env").status_code == 404
        assert client.get("/.gitignore").status_code == 404
        assert client.get("/backend/app/main.py").status_code == 404
