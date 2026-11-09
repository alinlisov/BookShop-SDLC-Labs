from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    genre: str
    price: Decimal = Field(ge=0)
    cover: str | None = None
    is_available: bool


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=25)
    password: str = Field(min_length=8, max_length=128, repr=False)
    password_confirmation: str = Field(repr=False)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Ім'я має містити щонайменше два символи")
        return cleaned

    @field_validator("phone")
    @classmethod
    def normalize_ukrainian_phone(cls, value: str) -> str:
        cleaned = re.sub(r"[\s()\-]", "", value)
        if re.fullmatch(r"0\d{9}", cleaned):
            return "+38" + cleaned
        if re.fullmatch(r"\+380\d{9}", cleaned):
            return cleaned
        raise ValueError("Вкажіть телефон у форматі +380XXXXXXXXX або 0XXXXXXXXX")

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterIn":
        if self.password != self.password_confirmation:
            raise ValueError("Пароль та його підтвердження не збігаються")
        return self


class RegisterOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str
    is_admin: bool


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, repr=False)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserProfileOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    is_admin: bool

class ProfileAddressUpdate(BaseModel):
    address: str = Field(min_length=5, max_length=500)

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 5:
            raise ValueError("Адреса доставки повинна містити принаймні 5 символів")
        return cleaned


class LogoutOut(BaseModel):
    message: str

# ЛР5 — етап 3. Каталог, оформлення замовлень і відгуки.
from datetime import datetime
from typing import Literal


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=150)
    genre: str = Field(min_length=1, max_length=80)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    cover: str | None = Field(default=None, max_length=255)
    is_available: bool = True

    @field_validator("title", "author", "genre")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Поле не може бути порожнім")
        return value


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=150)
    genre: str | None = Field(default=None, min_length=1, max_length=80)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    cover: str | None = Field(default=None, max_length=255)
    is_available: bool | None = None

    @field_validator("title", "author", "genre")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if not value:
            raise ValueError("Поле не може бути порожнім")
        return value


class OrderLineIn(BaseModel):
    book_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=20)


class OrderCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=25)
    address: str = Field(min_length=5, max_length=500)
    items: list[OrderLineIn] = Field(min_length=1, max_length=20)

    @field_validator("full_name", "address")
    @classmethod
    def clean_order_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Поле не може бути порожнім")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        value = re.sub(r"[\s()\-]", "", value)
        if re.fullmatch(r"0\d{9}", value):
            return "+38" + value
        if re.fullmatch(r"\+380\d{9}", value):
            return value
        raise ValueError("Телефон має бути у форматі +380XXXXXXXXX або 0XXXXXXXXX")

    @model_validator(mode="after")
    def unique_books(self) -> "OrderCreate":
        ids = [line.book_id for line in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Одна книжка не повинна повторюватися двічі у замовленні")
        return self


class OrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    book_id: int
    quantity: int
    price_per_item: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    items: list[OrderLineOut]


class OrderAdminOut(OrderOut):
    user_id: int | None
    customer_name: str
    email: EmailStr
    phone: str
    address: str


class OrderStatusUpdate(BaseModel):
    status: Literal["processing", "approved", "rejected", "cancelled"]


class ReviewCreate(BaseModel):
    comment_text: str = Field(min_length=3, max_length=2000)

    @field_validator("comment_text")
    @classmethod
    def clean_comment(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Відгук має містити щонайменше три символи")
        return value


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    author_name: str
    comment_text: str
    created_at: datetime
