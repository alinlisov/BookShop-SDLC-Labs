"""Eight checks for login, profile, logout and role access."""
import base64, secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base,get_db
from app.main import app
from app.models import AuthSession,User

def key(): return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")

@pytest.fixture
def ctx(monkeypatch):
    for name in ("DATA_ENCRYPTION_KEY","EMAIL_LOOKUP_KEY","AUTH_SIGNING_KEY"):
        monkeypatch.setenv(name,key())
    engine=create_engine("sqlite+pysqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory=sessionmaker(bind=engine)
    def dependency():
        with factory() as db: yield db
    app.dependency_overrides[get_db]=dependency
    try: yield TestClient(app),factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

def register(client):
    result=client.post("/api/auth/register",json={
        "full_name":"Тестова Покупчиня","email":"test@example.com","phone":"0501234567",
        "password":"TestPassword123!","password_confirmation":"TestPassword123!"})
    assert result.status_code==201,result.text

def login(client, email="test@example.com", password="TestPassword123!"):
    return client.post("/api/auth/login",json={"email":email,"password":password})

def auth(token): return {"Authorization":f"Bearer {token}"}

def test_login_and_profile(ctx):
    client,factory=ctx;register(client)
    r=login(client);assert r.status_code==200,r.text
    assert r.json()["token_type"]=="bearer" and r.json()["expires_in"]==1800
    profile=client.get("/api/auth/me",headers=auth(r.json()["access_token"]))
    assert profile.status_code==200,profile.text
    assert profile.json()["email"]=="test@example.com"
    assert profile.json()["phone"]=="+380501234567"
    assert "password_hash" not in profile.json()
    with factory() as db: assert len(db.scalars(select(AuthSession)).all())==1

def test_wrong_password(ctx):
    client,_=ctx;register(client)
    assert login(client,password="wrong-Password123!").status_code==401

def test_unknown_email(ctx):
    client,_=ctx
    assert login(client,email="missing@example.com").status_code==401

def test_no_token(ctx):
    client,_=ctx;assert client.get("/api/auth/me").status_code==401

def test_bad_token(ctx):
    client,_=ctx;assert client.get("/api/auth/me",headers=auth("invalid-jwt")).status_code==401

def test_logout_revokes_session(ctx):
    client,factory=ctx;register(client)
    token=login(client).json()["access_token"]
    assert client.post("/api/auth/logout",headers=auth(token)).status_code==200
    assert client.get("/api/auth/me",headers=auth(token)).status_code==401
    with factory() as db: assert db.scalars(select(AuthSession)).all()==[]

def test_user_forbidden_admin(ctx):
    client,_=ctx;register(client)
    token=login(client).json()["access_token"]
    assert client.get("/api/auth/admin-check",headers=auth(token)).status_code==403

def test_admin_is_allowed(ctx):
    client,factory=ctx;register(client)
    with factory.begin() as db: db.scalar(select(User)).is_admin=True
    token=login(client).json()["access_token"]
    r=client.get("/api/auth/admin-check",headers=auth(token))
    assert r.status_code==200,r.text
    assert r.json()["role"]=="admin"
