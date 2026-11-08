"""Checks for authenticated user and administrator."""
from dataclasses import dataclass
from datetime import datetime, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .auth_tokens import read_token
from .database import get_db
from .models import User, AuthSession

bearer=HTTPBearer(auto_error=False)

@dataclass
class Authenticated:
    user: User
    token_hash: str

def _unauthorized():
    return HTTPException(status_code=401,detail="Потрібна авторизація або сесію завершено",
                         headers={"WWW-Authenticate":"Bearer"})

def require_authentication(
    credentials: HTTPAuthorizationCredentials | None=Depends(bearer),
    db: Session=Depends(get_db),
) -> Authenticated:
    if credentials is None or credentials.scheme.lower()!="bearer":
        raise _unauthorized()
    try:
        user_id,hashed_jti=read_token(credentials.credentials)
    except (jwt.InvalidTokenError, RuntimeError, ValueError):
        raise _unauthorized()
    active=db.get(AuthSession,hashed_jti)
    if active is None or active.user_id!=user_id:
        raise _unauthorized()
    expiry=active.expires_at
    if expiry.tzinfo is None: expiry=expiry.replace(tzinfo=timezone.utc)
    if expiry<=datetime.now(timezone.utc):
        raise _unauthorized()
    user=db.get(User,user_id)
    if user is None:
        raise _unauthorized()
    return Authenticated(user=user,token_hash=hashed_jti)

def require_admin(identity: Authenticated=Depends(require_authentication))->Authenticated:
    if not identity.user.is_admin:
        raise HTTPException(status_code=403,detail="Доступ лише для адміністратора")
    return identity


def optional_authentication(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Authenticated | None:
    """Guest checkout is allowed; if a token is supplied it must be valid."""
    if credentials is None:
        return None
    return require_authentication(credentials=credentials, db=db)
