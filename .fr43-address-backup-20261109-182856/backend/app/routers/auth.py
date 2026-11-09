"""Registration endpoint for FR-1.1 and FR-1.2."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, AuthSession
from ..schemas import RegisterIn, RegisterOut, LoginIn, TokenOut, UserProfileOut, LogoutOut
from ..security import email_lookup, encrypt_personal_data, hash_password, decrypt_personal_data
from ..auth_tokens import make_token, TOKEN_LIFETIME_SECONDS
from ..dependencies import Authenticated, require_admin, require_authentication
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

router = APIRouter(prefix="/api/auth", tags=["Користувачі"])


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> RegisterOut:
    email = str(payload.email).strip().casefold()
    lookup = email_lookup(email)

    if db.scalar(select(User.id).where(User.email_lookup == lookup)) is not None:
        raise HTTPException(status_code=409, detail="Користувач із таким email уже зареєстрований")

    user = User(
        full_name=payload.full_name,
        email_encrypted=encrypt_personal_data(email),
        email_lookup=lookup,
        phone_encrypted=encrypt_personal_data(payload.phone),
        password_hash=hash_password(payload.password),
        is_admin=False,  # Users may never assign their own administrator role.
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Covers two simultaneous requests registering the same email.
        raise HTTPException(status_code=409, detail="Користувач із таким email уже зареєстрований")
    db.refresh(user)
    return RegisterOut(
        id=user.id,
        full_name=user.full_name,
        email=email,
        phone=payload.phone,
        is_admin=user.is_admin,
    )


_password_verifier = PasswordHasher()
_DUMMY_HASH = _password_verifier.hash("dummy-used-to-reduce-email-enumeration-timing")

def _valid_password(hash_value: str, password: str) -> bool:
    try:
        return bool(_password_verifier.verify(hash_value, password))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False

@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    lookup = email_lookup(str(payload.email).strip().casefold())
    user = db.scalar(select(User).where(User.email_lookup == lookup))
    valid = _valid_password(user.password_hash if user else _DUMMY_HASH, payload.password)
    if not valid or user is None:
        raise HTTPException(status_code=401, detail="Неправильний email або пароль",
                            headers={"WWW-Authenticate": "Bearer"})
    token, hashed_jti, expires_at = make_token(user.id)
    db.add(AuthSession(token_hash=hashed_jti, user_id=user.id, expires_at=expires_at))
    db.commit()
    return TokenOut(access_token=token, expires_in=TOKEN_LIFETIME_SECONDS)

@router.get("/me", response_model=UserProfileOut)
def me(identity: Authenticated = Depends(require_authentication)) -> UserProfileOut:
    user=identity.user
    return UserProfileOut(
        id=user.id, full_name=user.full_name,
        email=decrypt_personal_data(user.email_encrypted),
        phone=decrypt_personal_data(user.phone_encrypted) if user.phone_encrypted else None,
        is_admin=user.is_admin,
    )

@router.post("/logout", response_model=LogoutOut)
def logout(identity: Authenticated = Depends(require_authentication),
           db: Session = Depends(get_db)) -> LogoutOut:
    saved=db.get(AuthSession, identity.token_hash)
    if saved is not None:
        db.delete(saved)
        db.commit()
    return LogoutOut(message="Сесію завершено")

@router.get("/admin-check")
def admin_check(identity: Authenticated = Depends(require_admin)) -> dict:
    return {"user_id": identity.user.id, "role": "admin", "access": "granted"}
