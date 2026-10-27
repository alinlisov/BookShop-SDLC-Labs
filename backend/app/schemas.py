from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    genre: str
    price: Decimal = Field(ge=0)
    cover: str | None = None
    is_available: bool
