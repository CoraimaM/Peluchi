"""Endpoints del carrito de compra (requiere autenticación)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_active_user
from app.models import CartItem, Product, User
from app.routers.products import FREE_SHIPPING_FROM, SHIPPING_COST, _product_out
from app.schemas import CartItemAdd, CartItemOut, CartItemUpdate, CartOut

router = APIRouter(prefix="/api/cart", tags=["Carrito"])


def _build_cart(db: Session, user: User) -> CartOut:
    items = db.scalars(
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(selectinload(CartItem.product).selectinload(Product.category),
                 selectinload(CartItem.product).selectinload(Product.reviews))
        .order_by(CartItem.added_at.desc())
    ).unique().all()

    out_items: list[CartItemOut] = []
    subtotal = 0.0
    count = 0
    for item in items:
        if not item.product or not item.product.is_active:
            continue
        line_total = round(item.product.price * item.quantity, 2)
        subtotal += line_total
        count += item.quantity
        out_items.append(
            CartItemOut(
                id=item.id,
                quantity=item.quantity,
                product=_product_out(item.product),
                line_total=line_total,
            )
        )

    subtotal = round(subtotal, 2)
    if count == 0:
        shipping = 0.0
    elif subtotal >= FREE_SHIPPING_FROM:
        shipping = 0.0
    else:
        shipping = SHIPPING_COST
    return CartOut(
        items=out_items,
        subtotal=subtotal,
        count=count,
        shipping=shipping,
        total=round(subtotal + shipping, 2),
    )


@router.get("", response_model=CartOut)
def get_cart(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CartOut:
    return _build_cart(db, user)


@router.post("", response_model=CartOut, status_code=201)
def add_to_cart(
    payload: CartItemAdd,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CartOut:
    product = db.get(Product, payload.product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.stock < 1:
        raise HTTPException(status_code=409, detail="Producto agotado")

    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == product.id
        )
    )
    new_qty = (item.quantity if item else 0) + payload.quantity
    if new_qty > product.stock:
        raise HTTPException(
            status_code=409,
            detail=f"Solo quedan {product.stock} unidades en stock",
        )
    if item:
        item.quantity = new_qty
    else:
        db.add(CartItem(user_id=user.id, product_id=product.id, quantity=payload.quantity))
    db.commit()
    return _build_cart(db, user)


@router.put("/{item_id}", response_model=CartOut)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CartOut:
    item = db.scalar(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Artículo no encontrado en el carrito")
    if item.product and payload.quantity > item.product.stock:
        raise HTTPException(
            status_code=409,
            detail=f"Solo quedan {item.product.stock} unidades en stock",
        )
    item.quantity = payload.quantity
    db.commit()
    return _build_cart(db, user)


@router.delete("/{item_id}", response_model=CartOut)
def remove_cart_item(
    item_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CartOut:
    item = db.scalar(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Artículo no encontrado en el carrito")
    db.delete(item)
    db.commit()
    return _build_cart(db, user)


@router.delete("", response_model=CartOut)
def clear_cart(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CartOut:
    db.query(CartItem).filter(CartItem.user_id == user.id).delete()
    db.commit()
    return _build_cart(db, user)
