"""Lab 6 unit tests: validation, encryption, password hashing, tokens, transitions."""
import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets

import jwt
import pytest
from cryptography.exceptions import InvalidTag
from pydantic import ValidationError

from app.auth_tokens import make_token, read_token, signing_key
from app.routers.orders import ALLOWED_TRANSITIONS
from app.schemas import BookCreate, LoginIn, OrderCreate, RegisterIn, ReviewCreate
from app.security import (
    decrypt_personal_data, email_lookup, encrypt_personal_data, hash_password,
)
from argon2 import PasswordHasher


def test_passwords_hashed_and_salted(lab6_keys):
    first = hash_password("SafePassword123!")
    second = hash_password("SafePassword123!")
    assert first != "SafePassword123!"
    assert first != second  # random salt
    assert PasswordHasher().verify(first, "SafePassword123!")
    with pytest.raises(Exception):
        PasswordHasher().verify(first, "incorrect")


def test_email_lookup_normalizes_case_and_spaces(lab6_keys):
    assert email_lookup(" Example@DOMAIN.COM ") == email_lookup("example@domain.com")
    assert email_lookup("other@domain.com") != email_lookup("example@domain.com")


def test_email_lookup_changes_when_secret_changes(monkeypatch, lab6_keys):
    lookup = email_lookup("test@example.com")
    monkeypatch.setenv("EMAIL_LOOKUP_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    assert email_lookup("test@example.com") != lookup


def test_aes_round_trip_and_unique_ciphertexts(lab6_keys):
    original = "Хмельницька, м. Хмельницький, вул. Тестова, 10"
    first, second = encrypt_personal_data(original), encrypt_personal_data(original)
    assert first != second  # fresh nonce each time
    assert original not in first
    assert decrypt_personal_data(first) == original
    assert decrypt_personal_data(second) == original


def test_aes_rejects_tampered_ciphertext(lab6_keys):
    original = encrypt_personal_data("Перевірка цілісності")
    raw = bytearray(base64.urlsafe_b64decode(original))
    raw[-1] ^= 1
    tampered = base64.urlsafe_b64encode(raw).decode()
    with pytest.raises(InvalidTag):
        decrypt_personal_data(tampered)


def test_aes_rejects_wrong_secret(monkeypatch, lab6_keys):
    ciphertext = encrypt_personal_data("Перевірка ключа")
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    with pytest.raises(InvalidTag):
        decrypt_personal_data(ciphertext)


def test_missing_encryption_key_is_error(monkeypatch, lab6_keys):
    monkeypatch.delenv("DATA_ENCRYPTION_KEY")
    with pytest.raises(RuntimeError, match="DATA_ENCRYPTION_KEY"):
        encrypt_personal_data("Це тест")


def test_registration_normalizes_name_and_phone():
    account = RegisterIn(full_name="  Тестова    Покупчиня ", email="TEST@example.com",
                         phone="050 123 45 67", password="Secret123!",
                         password_confirmation="Secret123!")
    assert account.full_name == "Тестова Покупчиня"
    assert account.phone == "+380501234567"


@pytest.mark.parametrize("phone", ["123", "+381501234567", "0abcdefghi"])
def test_registration_rejects_wrong_phone(phone):
    with pytest.raises(ValidationError):
        RegisterIn(full_name="Тестовий Користувач", email="test@example.com", phone=phone,
                   password="Secret123!", password_confirmation="Secret123!")


def test_registration_rejects_password_mismatch():
    with pytest.raises(ValidationError):
        RegisterIn(full_name="Тестовий Користувач", email="test@example.com", phone="0501234567",
                   password="Secret123!", password_confirmation="Different123!")


def test_orders_validate_distinct_items_and_quantity():
    common = dict(full_name="Тестовий Покупець", email="test@example.com", phone="0501234567",
                  address="м. Київ, вулиця Прикладна, 10")
    with pytest.raises(ValidationError):
        OrderCreate(**common, items=[{"book_id": 1, "quantity": 0}])
    with pytest.raises(ValidationError):
        OrderCreate(**common, items=[{"book_id": 1, "quantity": 1}, {"book_id": 1, "quantity": 2}])
    order = OrderCreate(**common, items=[{"book_id": 1, "quantity": 2}])
    assert order.phone == "+380501234567"


def test_book_price_and_title_validation():
    book = BookCreate(title="  Тестова   книга ", author=" Автор ", genre=" Роман ", price=Decimal("99.50"))
    assert book.title == "Тестова книга"
    assert book.price == Decimal("99.50")
    with pytest.raises(ValidationError):
        BookCreate(title="   ", author="Автор", genre="Роман", price=Decimal("10"))
    with pytest.raises(ValidationError):
        BookCreate(title="Книга", author="Автор", genre="Роман", price=Decimal("-1"))


def test_review_text_is_trimmed_and_validated():
    assert ReviewCreate(comment_text="  Чудова книга!  ").comment_text == "Чудова книга!"
    with pytest.raises(ValidationError):
        ReviewCreate(comment_text="   ")


def test_jwt_round_trip_and_tampering(lab6_keys):
    token, digest, expires = make_token(42)
    user_id, decoded_digest = read_token(token)
    assert user_id == 42 and decoded_digest == digest
    assert expires > datetime.now(timezone.utc)
    with pytest.raises(jwt.InvalidTokenError):
        read_token(token + "invalid")


def test_jwt_expired_token_is_rejected(lab6_keys):
    now = datetime.now(timezone.utc)
    expired = jwt.encode({"sub": "42", "jti": "expired-example", "type": "access",
                          "iss": "bookshop-api", "aud": "bookshop-users",
                          "iat": now - timedelta(days=2), "exp": now - timedelta(days=1)},
                         signing_key(), algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        read_token(expired)


def test_status_transitions_have_final_states():
    assert {"processing", "approved"} <= ALLOWED_TRANSITIONS["new"]
    for final in ("approved", "rejected", "cancelled"):
        assert ALLOWED_TRANSITIONS[final] == set()
    assert "new" not in ALLOWED_TRANSITIONS["processing"]
