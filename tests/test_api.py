"""Tests automatizados de la API (pytest).

Usan una base SQLite temporal: no tocan PostgreSQL.

    python -m pytest tests/ -v
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# La BD de tests debe configurarse ANTES de importar la app
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.gettempdir()) / 'peluchi_test.db'}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _arrancar_app():
    """Ejecuta el lifespan (create_all + seed) una sola vez."""
    with client:
        yield


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_seed_categorias_y_productos():
    cats = client.get("/api/categories").json()
    assert len(cats) >= 8
    data = client.get("/api/products").json()
    assert data["total"] >= 20
    assert all("price" in p and "slug" in p for p in data["items"])


def test_filtro_categoria_y_busqueda():
    cats = client.get("/api/categories").json()
    slug = cats[0]["slug"]
    data = client.get(f"/api/products?category={slug}").json()
    assert data["total"] >= 1
    buscados = client.get("/api/products?q=oso").json()
    assert buscados["total"] >= 1


def test_producto_por_slug():
    p = client.get("/api/products").json()["items"][0]
    r = client.get(f"/api/products/{p['slug']}")
    assert r.status_code == 200
    assert r.json()["id"] == p["id"]


def test_producto_inexistente_404():
    assert client.get("/api/products/no-existe-ninguno").status_code == 404


def test_registro_y_login():
    r = client.post("/api/auth/register", json={
        "email": "pytest@peluchi.es", "password": "clave123", "full_name": "Py Test"})
    assert r.status_code == 201
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    r2 = client.post("/api/auth/login",
                     data={"username": "pytest@peluchi.es", "password": "clave123"})
    assert r2.status_code == 200

    r3 = client.post("/api/auth/login",
                     data={"username": "pytest@peluchi.es", "password": "mala"})
    assert r3.status_code == 401


def test_registro_email_duplicado():
    payload = {"email": "dup@peluchi.es", "password": "clave123", "full_name": "Dup"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_refresh_token():
    tokens = client.post("/api/auth/register", json={
        "email": "refresh@peluchi.es", "password": "clave123", "full_name": "R"}).json()
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    # Refresh token inválido
    assert client.post("/api/auth/refresh",
                       json={"refresh_token": "basura"}).status_code == 401


def test_endpoints_protegidos_sin_token():
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/cart").status_code == 401
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/admin/stats").status_code == 401


def _registrar(email: str) -> dict:
    return client.post("/api/auth/register", json={
        "email": email, "password": "clave123", "full_name": "Flujo Test"}).json()


def _headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_flujo_completo_carrito_pedido():
    tokens = _registrar("flujo@peluchi.es")
    h = _headers(tokens)

    # Añadir dos productos distintos
    products = client.get("/api/products?per_page=2").json()["items"]
    r = client.post("/api/cart", json={"product_id": products[0]["id"], "quantity": 2}, headers=h)
    assert r.status_code == 201
    client.post("/api/cart", json={"product_id": products[1]["id"], "quantity": 1}, headers=h)

    cart = client.get("/api/cart", headers=h).json()
    assert cart["count"] == 3
    assert cart["subtotal"] == round(products[0]["price"] * 2 + products[1]["price"], 2)

    # Actualizar y borrar (identificando por producto para que sea determinista)
    item_a = next(i for i in cart["items"] if i["product"]["id"] == products[0]["id"])
    cart2 = client.put(f"/api/cart/{item_a['id']}", json={"quantity": 5}, headers=h).json()
    assert cart2["count"] == 6
    cart3 = client.delete(f"/api/cart/{item_a['id']}", headers=h).json()
    assert cart3["count"] == 1

    # Checkout (queda 1 unidad del segundo producto)
    stock_antes = client.get(f"/api/products/{products[1]['id']}").json()["stock"]
    r = client.post("/api/orders", json={
        "shipping": {"name": "Flujo Test", "address": "Calle Test 1", "city": "Sevilla",
                     "postal_code": "41001", "phone": "655111222"},
        "payment_method": "card",
    }, headers=h)
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "pending"
    assert order["items"][0]["quantity"] == 1

    # Stock descontado y carrito vacío
    stock_despues = client.get(f"/api/products/{products[1]['id']}").json()["stock"]
    assert stock_despues == stock_antes - 1
    assert client.get("/api/cart", headers=h).json()["count"] == 0

    # El pedido aparece en el historial
    pedidos = client.get("/api/orders", headers=h).json()
    assert any(p["id"] == order["id"] for p in pedidos)


def test_checkout_con_carrito_vacio():
    tokens = _registrar("vacio@peluchi.es")
    r = client.post("/api/orders", json={
        "shipping": {"name": "Sin Carrito", "address": "Calle Vacia 1", "city": "Madrid",
                     "postal_code": "28001", "phone": "600000000"},
        "payment_method": "card",
    }, headers=_headers(tokens))
    assert r.status_code == 400


def test_reseñas():
    tokens = _registrar("resena@peluchi.es")
    h = _headers(tokens)
    slug = client.get("/api/products").json()["items"][0]["slug"]
    r = client.post(f"/api/products/{slug}/reviews",
                    json={"rating": 5, "comment": "Precioso"}, headers=h)
    assert r.status_code == 201
    # Solo una reseña por usuario
    assert client.post(f"/api/products/{slug}/reviews",
                       json={"rating": 1, "comment": "Otra"}, headers=h).status_code == 409
    resenas = client.get(f"/api/products/{slug}/reviews").json()
    assert len(resenas) >= 1


def test_admin_solo_para_admins():
    tokens = _registrar("normal@peluchi.es")
    assert client.get("/api/admin/stats", headers=_headers(tokens)).status_code == 403

    # Login con el admin del seed
    r = client.post("/api/auth/login",
                    data={"username": "admin@peluchi.es", "password": "admin1234"})
    assert r.status_code == 200
    ah = _headers(r.json())
    stats = client.get("/api/admin/stats", headers=ah).json()
    assert stats["users"] >= 4
    assert stats["products"] >= 20


def test_admin_crud_producto():
    r = client.post("/api/auth/login",
                    data={"username": "admin@peluchi.es", "password": "admin1234"})
    ah = _headers(r.json())
    cat_id = client.get("/api/categories").json()[0]["id"]

    r = client.post("/api/admin/products", json={
        "name": "Peluche Pytest", "price": 10.0, "stock": 3,
        "category_id": cat_id, "emoji": "🧸"}, headers=ah)
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.put(f"/api/admin/products/{pid}", json={"price": 8.5}, headers=ah)
    assert r.status_code == 200
    assert r.json()["price"] == 8.5

    assert client.delete(f"/api/admin/products/{pid}", headers=ah).status_code == 204
    assert client.get(f"/api/products/{pid}").status_code == 404


def test_github_oauth_sin_configurar():
    prov = client.get("/api/auth/providers").json()
    assert prov["github"]["enabled"] is False
    r = client.get("/api/auth/github/login", follow_redirects=False)
    assert r.status_code == 400


def test_paginas_frontend():
    for pagina in ["/", "/tienda.html", "/login.html", "/registro.html",
                   "/carrito.html", "/producto.html", "/admin.html",
                   "/pedidos.html", "/cuenta.html", "/checkout.html"]:
        assert client.get(pagina).status_code == 200, pagina
