"""Endpoints de cuenta de usuario: perfil, contraseña y estadísticas."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_active_user
from app.models import Order, Review, User
from app.schemas import PasswordChange, UserOut, UserUpdate
from app.security import hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


@router.get("/me", response_model=UserOut)
def get_profile(user: User = Depends(get_current_active_user)) -> User:
    return user


@router.put("/me", response_model=UserOut)
def update_profile(
    payload: UserUpdate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.email is not None:
        new_email = payload.email.lower().strip()
        other = db.scalar(select(User).where(User.email == new_email, User.id != user.id))
        if other:
            raise HTTPException(status_code=409, detail="Ese email ya está en uso")
        user.email = new_email
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    db.commit()
    db.refresh(user)
    return user


@router.put("/me/password", response_model=UserOut)
def change_password(
    payload: PasswordChange,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    if user.provider == "github" and not user.hashed_password:
        raise HTTPException(
            status_code=400,
            detail="Tu cuenta se crea con GitHub, no tiene contraseña propia",
        )
    if not verify_password(payload.current_password, user.hashed_password or ""):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/stats")
def my_stats(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    orders = db.scalar(
        select(func.count(Order.id)).where(
            Order.user_id == user.id, Order.status != Order.STATUS_CANCELLED
        )
    ) or 0
    spent = db.scalar(
        select(func.coalesce(func.sum(Order.total), 0.0)).where(
            Order.user_id == user.id, Order.status != Order.STATUS_CANCELLED
        )
    ) or 0.0
    reviews = db.scalar(select(func.count(Review.id)).where(Review.user_id == user.id)) or 0
    return {
        "orders": orders,
        "spent": round(float(spent), 2),
        "reviews": reviews,
        "member_since": user.created_at.isoformat(),
    }
