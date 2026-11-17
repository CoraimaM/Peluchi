"""Peluchi API — Tienda de peluches de coleccionista.

FastAPI + PostgreSQL + JWT/OAuth2 (GitHub).

Arranque:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import admin, auth, cart, orders, products, users
from app.seed import seed

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Crea las tablas y carga el catálogo de ejemplo la primera vez."""
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API REST de una tienda de peluches de coleccionista con autenticación "
        "JWT + OAuth2 (GitHub), carrito, pedidos y panel de administración."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Rutas de la API
# --------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(users.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["Sistema"])
def health() -> dict:
    """Comprobación de vida de la API."""
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


# --------------------------------------------------------------------------
# Frontend estático (HTML/CSS/JS puro) servido por la misma app
# --------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{page_name}.html", include_in_schema=False)
def page(page_name: str) -> FileResponse:
    """Sirve cualquier página del frontend (login.html, tienda.html, ...)."""
    target = FRONTEND_DIR / f"{page_name}.html"
    if not target.is_file():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Página no encontrada")
    return FileResponse(target)
