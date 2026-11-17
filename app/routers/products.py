"""Endpoints públicos de catálogo: categorías, productos y reseñas."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_active_user
from app.models import Category, Product, Review, User
from app.schemas import (
    CategoryOut,
    ProductListOut,
    ProductOut,
    ReviewCreate,
    ReviewOut,
)

router = APIRouter(prefix="/api", tags=["Catálogo"])

FREE_SHIPPING_FROM = 49.0
SHIPPING_COST = 4.95


def _product_out(product: Product) -> ProductOut:
    out = ProductOut.model_validate(product)
    # Ratings calculados desde la relación lazy (ya cargada con selectinload)
    out.rating_avg = product.rating_avg
    out.rating_count = product.rating_count
    return out


# --------------------------------------------------------------------------
# Categorías
# --------------------------------------------------------------------------
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    cats = db.scalars(select(Category).order_by(Category.name)).unique().all()
    counts = dict(
        db.execute(
            select(Product.category_id, func.count(Product.id))
            .where(Product.is_active.is_(True))
            .group_by(Product.category_id)
        ).all()
    )
    result = []
    for c in cats:
        out = CategoryOut.model_validate(c)
        out.product_count = counts.get(c.id, 0)
        result.append(out)
    return result


# --------------------------------------------------------------------------
# Productos
# --------------------------------------------------------------------------
@router.get("/products", response_model=ProductListOut)
def list_products(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=100, description="Buscar por nombre, sku o descripción"),
    category: str | None = Query(default=None, description="Slug de la categoría"),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    featured: bool | None = None,
    is_new: bool | None = None,
    on_sale: bool | None = None,
    in_stock: bool | None = None,
    sort: str = Query(default="recent", pattern="^(recent|price_asc|price_desc|name|featured)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=48),
) -> ProductListOut:
    stmt = select(Product).where(Product.is_active.is_(True))
    count_stmt = select(func.count(Product.id)).where(Product.is_active.is_(True))

    if q:
        pattern = f"%{q.strip()}%"
        filt = or_(
            Product.name.ilike(pattern),
            Product.sku.ilike(pattern),
            Product.description.ilike(pattern),
            Product.brand.ilike(pattern),
        )
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    if category:
        stmt = stmt.join(Category).where(Category.slug == category)
        count_stmt = count_stmt.join(Category).where(Category.slug == category)
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
        count_stmt = count_stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
        count_stmt = count_stmt.where(Product.price <= max_price)
    if featured:
        stmt = stmt.where(Product.is_featured.is_(True))
        count_stmt = count_stmt.where(Product.is_featured.is_(True))
    if is_new:
        stmt = stmt.where(Product.is_new.is_(True))
        count_stmt = count_stmt.where(Product.is_new.is_(True))
    if on_sale:
        stmt = stmt.where(Product.compare_price.is_not(None), Product.compare_price > Product.price)
        count_stmt = count_stmt.where(
            Product.compare_price.is_not(None), Product.compare_price > Product.price
        )
    if in_stock:
        stmt = stmt.where(Product.stock > 0)
        count_stmt = count_stmt.where(Product.stock > 0)

    total = db.scalar(count_stmt) or 0
    order_map = {
        "recent": [Product.created_at.desc()],
        "price_asc": [Product.price.asc()],
        "price_desc": [Product.price.desc()],
        "name": [Product.name.asc()],
        "featured": [Product.is_featured.desc(), Product.created_at.desc()],
    }

    items = db.scalars(
        stmt.options(selectinload(Product.category), selectinload(Product.reviews))
        .order_by(*order_map.get(sort, order_map["recent"]))
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).unique().all()

    return ProductListOut(
        items=[_product_out(p) for p in items],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
        per_page=per_page,
    )


def _get_product(db: Session, slug_or_id: str) -> Product:
    stmt = (
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.reviews))
    )
    if slug_or_id.isdigit():
        product = db.scalar(stmt.where(Product.id == int(slug_or_id)))
    else:
        product = db.scalar(stmt.where(Product.slug == slug_or_id))
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.get("/products/{slug_or_id}", response_model=ProductOut)
def get_product(slug_or_id: str, db: Session = Depends(get_db)) -> ProductOut:
    return _product_out(_get_product(db, slug_or_id))


# --------------------------------------------------------------------------
# Reseñas
# --------------------------------------------------------------------------
@router.get("/products/{slug_or_id}/reviews", response_model=list[ReviewOut])
def list_reviews(slug_or_id: str, db: Session = Depends(get_db)) -> list[ReviewOut]:
    product = _get_product(db, slug_or_id)
    reviews = db.scalars(
        select(Review)
        .where(Review.product_id == product.id)
        .options(selectinload(Review.user))
        .order_by(Review.created_at.desc())
    ).unique().all()
    return [
        ReviewOut(
            id=r.id,
            product_id=r.product_id,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
            user_name=r.user.full_name or r.user.email.split("@")[0] if r.user else "Anónimo",
        )
        for r in reviews
    ]


@router.post("/products/{slug_or_id}/reviews", response_model=ReviewOut, status_code=201)
def create_review(
    slug_or_id: str,
    payload: ReviewCreate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ReviewOut:
    product = _get_product(db, slug_or_id)
    existing = db.scalar(
        select(Review).where(Review.product_id == product.id, Review.user_id == user.id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Ya has reseñado este producto")
    review = Review(
        product_id=product.id,
        user_id=user.id,
        rating=payload.rating,
        comment=payload.comment.strip(),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return ReviewOut(
        id=review.id,
        product_id=review.product_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        user_name=user.full_name or user.email.split("@")[0],
    )
