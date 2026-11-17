"""Esquemas Pydantic para validación y serialización de la API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# --------------------------------------------------------------------------
# Auth / Usuarios
# --------------------------------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(default="", max_length=120)


class UserRegister(UserBase):
    password: str = Field(min_length=6, max_length=128)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    provider: str
    role: str
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    avatar_url: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


# --------------------------------------------------------------------------
# Categorías
# --------------------------------------------------------------------------
class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    emoji: str
    description: str
    product_count: int = 0


# --------------------------------------------------------------------------
# Productos
# --------------------------------------------------------------------------
class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
    sku: str
    price: float
    compare_price: float | None = None
    stock: int
    size_cm: int | None = None
    emoji: str
    image_url: str | None = None
    brand: str
    material: str
    category_id: int
    category: CategoryOut | None = None
    is_featured: bool
    is_new: bool
    is_on_sale: bool
    is_active: bool
    created_at: datetime
    rating_avg: float = 0.0
    rating_count: int = 0


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    pages: int
    per_page: int


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=180)
    description: str = ""
    sku: str | None = None
    price: float = Field(gt=0)
    compare_price: float | None = Field(default=None, gt=0)
    stock: int = Field(default=0, ge=0)
    size_cm: int | None = Field(default=None, ge=1)
    emoji: str = "🧸"
    image_url: str | None = None
    brand: str = "Peluchi"
    material: str = "Peluche suave PP"
    category_id: int
    is_featured: bool = False
    is_new: bool = False
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    compare_price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    size_cm: int | None = Field(default=None, ge=1)
    emoji: str | None = None
    image_url: str | None = None
    brand: str | None = None
    material: str | None = None
    category_id: int | None = None
    is_featured: bool | None = None
    is_new: bool | None = None
    is_active: bool | None = None


# --------------------------------------------------------------------------
# Reseñas
# --------------------------------------------------------------------------
class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    rating: int
    comment: str
    created_at: datetime
    user_name: str = "Anónimo"


# --------------------------------------------------------------------------
# Carrito
# --------------------------------------------------------------------------
class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=99)


class CartItemOut(BaseModel):
    id: int
    quantity: int
    product: ProductOut
    line_total: float


class CartOut(BaseModel):
    items: list[CartItemOut]
    subtotal: float
    count: int
    shipping: float
    total: float


# --------------------------------------------------------------------------
# Pedidos
# --------------------------------------------------------------------------
class ShippingInfo(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=5, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=4, max_length=10)
    phone: str = Field(min_length=6, max_length=20)


class OrderCreate(BaseModel):
    shipping: ShippingInfo
    payment_method: str = Field(default="card", pattern="^(card|paypal|cod)$")


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    product_name: str
    product_emoji: str
    unit_price: float
    quantity: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    subtotal: float
    shipping_cost: float
    total: float
    payment_method: str
    ship_name: str
    ship_address: str
    ship_city: str
    ship_postal_code: str
    ship_phone: str
    created_at: datetime
    items: list[OrderItemOut] = []


class OrderStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|paid|shipped|delivered|cancelled)$")


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------
class AdminUserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    is_active: bool | None = None


class AdminStats(BaseModel):
    users: int
    products: int
    orders: int
    revenue: float
    pending_orders: int
    low_stock_products: int
    recent_orders: list[OrderOut]
