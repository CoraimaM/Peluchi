"""Endpoints de pedidos: checkout y consulta del historial."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_active_user
from app.models import CartItem, Order, OrderItem, Product, User
from app.routers.products import FREE_SHIPPING_FROM, SHIPPING_COST
from app.schemas import OrderCreate, OrderOut

router = APIRouter(prefix="/api/orders", tags=["Pedidos"])


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Order:
    cart_items = db.scalars(
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(selectinload(CartItem.product))
    ).unique().all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="El carrito está vacío")

    # Validar stock y calcular totales
    subtotal = 0.0
    for item in cart_items:
        product: Product | None = item.product
        if product is None or not product.is_active:
            raise HTTPException(status_code=409, detail="Un producto del carrito ya no está disponible")
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Stock insuficiente para '{product.name}' (quedan {product.stock})",
            )
        subtotal += product.price * item.quantity

    shipping = 0.0 if subtotal >= FREE_SHIPPING_FROM else SHIPPING_COST
    order = Order(
        user_id=user.id,
        status=Order.STATUS_PENDING,
        subtotal=round(subtotal, 2),
        shipping_cost=shipping,
        total=round(subtotal + shipping, 2),
        payment_method=payload.payment_method,
        ship_name=payload.shipping.name,
        ship_address=payload.shipping.address,
        ship_city=payload.shipping.city,
        ship_postal_code=payload.shipping.postal_code,
        ship_phone=payload.shipping.phone,
    )
    db.add(order)
    db.flush()

    for item in cart_items:
        product = item.product
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                product_emoji=product.emoji,
                unit_price=product.price,
                quantity=item.quantity,
            )
        )
        product.stock -= item.quantity

    # Vaciar el carrito
    for item in cart_items:
        db.delete(item)

    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=list[OrderOut])
def my_orders(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[Order]:
    return db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    ).unique().all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if order.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="No tienes acceso a este pedido")
    return order
