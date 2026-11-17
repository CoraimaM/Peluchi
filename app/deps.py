"""Dependencias comunes de FastAPI: sesión de BD y usuario actual."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Usuario autenticado a partir del JWT de la cabecera Authorization."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise credentials_error
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise credentials_error
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="La cuenta está desactivada")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Solo usuarios con rol 'admin'."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return user
