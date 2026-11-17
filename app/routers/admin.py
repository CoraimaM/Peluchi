"""Endpoints de administración (rol 'admin'): productos, pedidos, usuarios y métricas."""

from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_admin
from app.models import Category, Order, Product, Review, User
from app.schemas import (
    AdminStats,
    AdminUserUpdate,
    OrderOut,
    OrderStatusUpdate,
    ProductCreate,
    ProductListOut,
    ProductOut,
    ProductUpdate,
    UserOut,
)

router = APIRouter(prefix="/api/admin", tags=["Administración"], dependencies=[Depends(require_admin)])


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "producto"


# --------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------
@router.get("/stats", response_model=AdminStats)
def stats(db: Session = Depends(get_db)) -> AdminStats:
    users = db.scalar(select(func.count(User.id))) or 0
    products = db.scalar(select(func.count(Product.id))) or 0
    orders = db.scalar(select(func.count(Order.id))) or 0
    revenue = (
        db.scalar(
            select(func.coalesce(func.sum(Order.total), 0.0)).where(
                Order.status.in_(["paid", "shipped", "delivered"])
            )
        )
        or 0.0
    )
    pending = db.scalar(select(func.count(Order.id)).where(Order.status == Order.STATUS_PENDING)) or 0
    low_stock = (
        db.scalar(select(func.count(Product.id)).where(Product.stock <= 5, Product.is_active.is_(True)))
        or 0
    )
    recent = db.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(5)
    ).unique().all()
    return AdminStats(
        users=users,
        products=products,
        orders=orders,
        revenue=round(float(revenue), 2),
        pending_orders=pending,
        low_stock_products=low_stock,
        recent_orders=[OrderOut.model_validate(o) for o in recent],
    )


# --------------------------------------------------------------------------
# Productos
# --------------------------------------------------------------------------
@router.get("/products", response_model=ProductListOut)
def admin_list_products(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> ProductListOut:
    stmt = select(Product)
    count_stmt = select(func.count(Product.id))
    if q:
        pattern = f"%{q.strip()}%"
        filt = Product.name.ilike(pattern) | Product.sku.ilike(pattern)
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.options(selectinload(Product.category), selectinload(Product.reviews))
        .order_by(Product.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).unique().all()
    return ProductListOut(
        items=[ProductOut.model_validate(p) for p in items],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
        per_page=per_page,
    )


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
) -> Product:
    category = db.get(Category, payload.category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    slug = _slugify(payload.slug or payload.name)
    if db.scalar(select(Product).where(Product.slug == slug)):
        slug = f"{slug}-{db.scalar(select(func.count(Product.id))) + 1}"
    sku = payload.sku or f"PL-{slug[:10].upper()}-{db.scalar(select(func.count(Product.id))) + 1:04d}"
    if db.scalar(select(Product).where(Product.sku == sku)):
        raise HTTPException(status_code=409, detail=f"Ya existe un producto con SKU {sku}")

    product = Product(**payload.model_dump(exclude={"slug", "sku"}), slug=slug, sku=sku)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and db.get(Category, data["category_id"]) is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    for key, value in data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(product)
    db.commit()


# --------------------------------------------------------------------------
# Pedidos
# --------------------------------------------------------------------------
@router.get("/orders", response_model=list[OrderOut])
def admin_list_orders(
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[Order]:
    stmt = select(Order).options(selectinload(Order.items))
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    return db.scalars(stmt.order_by(Order.created_at.desc())).unique().all()


@router.patch("/orders/{order_id}", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
) -> Order:
    order = db.scalar(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    # Si se cancela, se devuelve el stock
    if payload.status == Order.STATUS_CANCELLED and order.status != Order.STATUS_CANCELLED:
        for item in order.items:
            if item.product is not None:
                item.product.stock += item.quantity
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order


# --------------------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------------------
@router.get("/users", response_model=list[UserOut])
def admin_list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.scalars(select(User).order_by(User.created_at.desc())).unique().all()


@router.patch("/users/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user
