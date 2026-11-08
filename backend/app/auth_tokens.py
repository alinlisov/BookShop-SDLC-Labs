"""Signed, short-lived JWT; DB session record enables real logout."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
import jwt
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TOKEN_LIFETIME_SECONDS=1800
ISSUER="bookshop-api"
AUDIENCE="bookshop-users"

def signing_key() -> bytes:
    text=os.environ.get("AUTH_SIGNING_KEY", "")
    if not text:
        raise RuntimeError("Вкажіть AUTH_SIGNING_KEY у backend/.env")
    try:
        key=base64.urlsafe_b64decode(text.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("AUTH_SIGNING_KEY має бути у форматі base64") from exc
    if len(key)!=32:
        raise RuntimeError("AUTH_SIGNING_KEY має містити 32 випадкові байти")
    return key

def token_digest(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()

def make_token(user_id: int) -> tuple[str,str,datetime]:
    now=datetime.now(timezone.utc)
    expires_at=now+timedelta(seconds=TOKEN_LIFETIME_SECONDS)
    jti=secrets.token_urlsafe(32)
    payload={"sub":str(user_id),"jti":jti,"type":"access",
             "iss":ISSUER,"aud":AUDIENCE,"iat":now,"exp":expires_at}
    token=jwt.encode(payload,signing_key(),algorithm="HS256")
    return token,token_digest(jti),expires_at

def read_token(token: str) -> tuple[int,str]:
    data=jwt.decode(token,signing_key(),algorithms=["HS256"],
                    audience=AUDIENCE,issuer=ISSUER,
                    options={"require":["sub","jti","iat","exp","iss","aud"]})
    sub=data.get("sub")
    jti=data.get("jti")
    if data.get("type")!="access" or not isinstance(sub,str) or not sub.isdigit()       or not isinstance(jti,str) or not jti:
        raise jwt.InvalidTokenError("Invalid token payload")
    return int(sub),token_digest(jti)
