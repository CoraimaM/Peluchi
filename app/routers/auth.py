"""Endpoints de autenticación: registro, login JWT, refresh y OAuth de GitHub."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import (
    RefreshRequest,
    TokenResponse,
    UserOut,
    UserRegister,
    UserUpdate,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


# --------------------------------------------------------------------------
# Registro y login clásico
# --------------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email")
    user = User(
        email=email,
        full_name=payload.full_name or email.split("@")[0],
        hashed_password=hash_password(payload.password),
        provider="local",
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Login con email (campo `username`) y contraseña → JWT."""
    email = form.username.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(form.password, user.hashed_password or ""):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="La cuenta está desactivada")
    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Intercambia un refresh token por uno nuevo (access + refresh rotados)."""
    data = decode_token(payload.refresh_token, expected_type="refresh")
    if data is None:
        raise HTTPException(status_code=401, detail="Refresh token inválido o caducado")
    user = db.get(User, int(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no válido")
    return _issue_tokens(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
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


# --------------------------------------------------------------------------
# OAuth con GitHub
# --------------------------------------------------------------------------
@router.get("/providers")
def providers() -> dict:
    """Indica al frontend qué proveedores OAuth están configurados."""
    return {
        "github": {
            "enabled": settings.github_enabled,
            "url": "/api/auth/github/login" if settings.github_enabled else None,
        }
    }


@router.get("/github/login")
def github_login() -> RedirectResponse:
    if not settings.github_enabled:
        raise HTTPException(
            status_code=400,
            detail=(
                "GitHub OAuth no está configurado. Añade GITHUB_CLIENT_ID y "
                "GITHUB_CLIENT_SECRET a tu archivo .env (ver README)."
            ),
        )
    state = secrets.token_urlsafe(24)
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
    )
    resp = RedirectResponse(url=f"{GITHUB_AUTHORIZE_URL}?{params}", status_code=302)
    # Cookie firmada para validar el state en el callback (protección CSRF)
    resp.set_cookie(
        key="gh_oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,
    )
    return resp


@router.get("/github/callback")
def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if not settings.github_enabled:
        raise HTTPException(status_code=400, detail="GitHub OAuth no está configurado")
    if not code or not state or state != request.cookies.get("gh_oauth_state"):
        raise HTTPException(status_code=400, detail="State OAuth inválido o caducado")

    try:
        tokens = _exchange_github_code(code)
        gh_user = _fetch_github_profile(tokens["access_token"])
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Error comunicando con GitHub: {exc}") from exc

    email = (gh_user.get("email") or f"{gh_user['login']}@users.noreply.github.com").lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = db.scalar(select(User).where(User.provider == "github", User.provider_id == str(gh_user["id"])))
    if user is None:
        user = User(
            email=email,
            full_name=gh_user.get("name") or gh_user["login"],
            avatar_url=gh_user.get("avatar_url"),
            provider="github",
            provider_id=str(gh_user["id"]),
            hashed_password=None,
            role="user",
        )
        db.add(user)
    else:  # vincular/actualizar cuenta existente
        user.provider_id = str(gh_user["id"])
        user.avatar_url = user.avatar_url or gh_user.get("avatar_url")
        if not user.full_name:
            user.full_name = gh_user.get("name") or gh_user["login"]
    db.commit()
    db.refresh(user)

    tokens_out = _issue_tokens(user)
    # Devolvemos los tokens en el fragmento (#) para que solo los lea el JS del navegador
    fragment = urlencode(
        {
            "access_token": tokens_out.access_token,
            "refresh_token": tokens_out.refresh_token,
        }
    )
    resp = RedirectResponse(url=f"{settings.frontend_url}/login.html#{fragment}", status_code=302)
    resp.delete_cookie("gh_oauth_state")
    return resp


def _exchange_github_code(code: str) -> dict:
    resp = httpx.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": settings.github_redirect_uri,
        },
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise HTTPException(status_code=502, detail=f"GitHub no devolvió access token: {data}")
    return data


def _fetch_github_profile(access_token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Peluchi-API",
    }
    resp = httpx.get(GITHUB_USER_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    profile = resp.json()

    # Si el email es privado, buscamos el principal verificado
    if not profile.get("email"):
        emails_resp = httpx.get(GITHUB_EMAILS_URL, headers=headers, timeout=20)
        if emails_resp.status_code == 200:
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            if primary:
                profile["email"] = primary["email"]
    return profile
