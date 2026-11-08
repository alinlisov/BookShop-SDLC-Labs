"""Guest and authenticated checkout; server-controlled prices and atomic inserts."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dependencies import Authenticated, optional_authentication, require_admin, require_authentication
from ..models import Book, Order, OrderItem
from ..schemas import OrderCreate, OrderOut, OrderAdminOut, OrderStatusUpdate
from ..security import encrypt_personal_data, decrypt_personal_data

router = APIRouter(prefix="/api/orders", tags=["Замовлення"])
admin_router = APIRouter(prefix="/api/admin/orders", tags=["Адміністрування замовлень"])


def _load_order(db: Session, order_id: int) -> Order:
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Замовлення не знайдено")
    return order


def _admin_out(order: Order) -> OrderAdminOut:
    return OrderAdminOut(
        id=order.id, status=order.status, total_amount=order.total_amount,
        created_at=order.created_at, items=order.items, user_id=order.user_id,
        customer_name=order.customer_name,
        email=decrypt_personal_data(order.customer_email_encrypted),
        phone=decrypt_personal_data(order.customer_phone_encrypted),
        address=decrypt_personal_data(order.delivery_address_encrypted),
    )


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    identity: Authenticated | None = Depends(optional_authentication),
):
    normalized_email = str(payload.email).strip().casefold()
    if identity is not None:
        saved_email = decrypt_personal_data(identity.user.email_encrypted).casefold()
        if normalized_email != saved_email:
            raise HTTPException(status_code=422, detail="Для авторизованого користувача email має збігатися з адресою профілю")

    book_ids = [entry.book_id for entry in payload.items]
    books = {book.id: book for book in db.scalars(select(Book).where(Book.id.in_(book_ids))).all()}
    for book_id in book_ids:
        if book_id not in books:
            raise HTTPException(status_code=404, detail=f"Книжку з id={book_id} не знайдено")
        if not books[book_id].is_available:
            raise HTTPException(status_code=409, detail=f"Книжка з id={book_id} зараз недоступна")

    lines = [OrderItem(book_id=item.book_id, quantity=item.quantity,
                       price_per_item=books[item.book_id].price)
             for item in payload.items]
    total = sum((line.price_per_item * line.quantity for line in lines), Decimal("0.00"))
    order = Order(
        user_id=identity.user.id if identity is not None else None,
        customer_name=payload.full_name,
        customer_email_encrypted=encrypt_personal_data(normalized_email),
        customer_phone_encrypted=encrypt_personal_data(payload.phone),
        delivery_address_encrypted=encrypt_personal_data(payload.address),
        total_amount=total, status="new", items=lines,
    )
    db.add(order)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _load_order(db, order.id)


@router.get("/mine", response_model=list[OrderOut])
def my_orders(
    identity: Authenticated = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    statement = (select(Order).options(selectinload(Order.items))
                 .where(Order.user_id == identity.user.id)
                 .order_by(Order.id.desc()))
    return db.scalars(statement).all()


@admin_router.get("", response_model=list[OrderAdminOut])
def admin_orders(
    _: Authenticated = Depends(require_admin), db: Session = Depends(get_db),
):
    orders = db.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())).all()
    return [_admin_out(order) for order in orders]


ALLOWED_TRANSITIONS = {
    "new": {"processing", "approved", "rejected", "cancelled"},
    "processing": {"approved", "rejected", "cancelled"},
    "approved": set(), "rejected": set(), "cancelled": set(),
}


@admin_router.patch("/{order_id}/status", response_model=OrderOut)
def change_status(
    order_id: int, payload: OrderStatusUpdate,
    _: Authenticated = Depends(require_admin), db: Session = Depends(get_db),
):
    order = _load_order(db, order_id)
    if payload.status not in ALLOWED_TRANSITIONS.get(order.status, set()):
        raise HTTPException(status_code=409, detail="Перехід між статусами замовлення заборонений")
    order.status = payload.status
    db.commit()
    return _load_order(db, order.id)
