"""Password hashing and reversible encryption for the BookShop demo.

Real encryption/HMAC keys are read from the local .env file at request time.
Never commit those keys to Git.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

from argon2 import PasswordHasher
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_password_hasher = PasswordHasher()


def _key_from_env(variable: str) -> bytes:
    """Read and validate a URL-safe base64 encoded 256-bit secret key."""
    encoded = os.environ.get(variable, "")
    if not encoded:
        raise RuntimeError(f"Missing {variable} in backend/.env")
    try:
        key = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError(f"Invalid base64 in {variable}") from exc
    if len(key) != 32:
        raise RuntimeError(f"{variable} must contain a base64-encoded 32-byte key")
    return key


def hash_password(password: str) -> str:
    """Hash a password using Argon2id; never encrypt or store plaintext passwords."""
    return _password_hasher.hash(password)


def email_lookup(email: str) -> str:
    """Deterministic, keyed lookup used to enforce case-insensitive email uniqueness."""
    key = _key_from_env("EMAIL_LOOKUP_KEY")
    normalized = email.strip().casefold()
    return hmac.new(key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def encrypt_personal_data(value: str) -> str:
    """Encrypt with AES-256-GCM using a fresh 96-bit nonce for each field."""
    key = _key_from_env("DATA_ENCRYPTION_KEY")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, value.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_personal_data(encoded: str) -> str:
    """Available for future authenticated profile/order endpoints."""
    key = _key_from_env("DATA_ENCRYPTION_KEY")
    raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
    if len(raw) < 12 + 16:
        raise ValueError("Encrypted value is too short")
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
