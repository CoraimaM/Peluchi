"""Prueba de humo contra la API en ejecución (uvicorn en :8000)."""

import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
ok = 0
fail = 0


def check(name, resp, expect=200):
    global ok, fail
    status_ok = resp.status_code == expect
    if status_ok:
        ok += 1
        print(f"  [OK] {name} ({resp.status_code})")
    else:
        fail += 1
        print(f"  [FAIL] {name} -> {resp.status_code}: {resp.text[:300]}")
    return resp


def main():
    c = httpx.Client(base_url=BASE, timeout=30)

    print("== Sistema ==")
    r = check("health", c.get("/api/health"))
    if r.status_code != 200:
        sys.exit(1)

    # Login admin al principio para dejar stock fresco en el producto de prueba
    admin_h = {"Authorization": f"Bearer " + check(
        "login admin", c.post("/api/auth/login",
                              data={"username": "admin@peluchi.es", "password": "admin1234"})
    ).json()["access_token"]}

    print("== Catálogo ==")
    r = check("categorias", c.get("/api/categories"))
    cats = r.json()
    print(f"     {len(cats)} categorias")
    r = check("productos", c.get("/api/products?per_page=5"))
    data = r.json()
    print(f"     {data['total']} productos, {data['pages']} paginas")

    # Elegir el producto con mas stock y dejarlo en 99 para el test de carrito
    todos = c.get("/api/products?per_page=48").json()["items"]
    prod = max(todos, key=lambda p: p["stock"])
    pid = prod["id"]
    slug = prod["slug"]
    check("preparar stock del producto de prueba",
          c.put(f"/api/admin/products/{pid}", json={"stock": 99}, headers=admin_h))
    check("producto por slug", c.get(f"/api/products/{slug}"))
    check("busqueda q=oso", c.get("/api/products?q=oso"))
    check("filtro categoria", c.get(f"/api/products?category={cats[0]['slug']}"))
    check("filtro precio", c.get("/api/products?min_price=10&max_price=30&sort=price_asc"))

    print("== Auth ==")
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    r = check("registro", c.post("/api/auth/register", json={
        "email": email, "password": "secreta123", "full_name": "Tester API"}), 201)
    tokens = r.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    check("refresh", c.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}))
    check("login", c.post("/api/auth/login", data={"username": email, "password": "secreta123"}))
    check("me", c.get("/api/auth/me", headers=headers))
    check("login malo (401)", c.post("/api/auth/login", data={"username": email, "password": "mala"}), 401)
    check("sin token (401)", c.get("/api/auth/me"), 401)

    print("== GitHub OAuth ==")
    prov = check("providers", c.get("/api/auth/providers")).json()
    print(f"     github configurado: {prov['github']['enabled']}")
    r = c.get("/api/auth/github/login", follow_redirects=False)
    if prov["github"]["enabled"]:
        check("redirect github (302)", r, 302)
    else:
        check("github sin configurar (400)", r, 400)

    print("== Carrito ==")
    check("anadir al carrito", c.post("/api/cart", json={"product_id": pid, "quantity": 2},
                                      headers=headers), 201)
    cart = check("ver carrito", c.get("/api/cart", headers=headers)).json()
    print(f"     {cart['count']} art., subtotal {cart['subtotal']} EUR")
    item_id = cart["items"][0]["id"]
    check("actualizar cantidad", c.put(f"/api/cart/{item_id}", json={"quantity": 3}, headers=headers))
    check("anadir repetido (suma)", c.post("/api/cart", json={"product_id": pid, "quantity": 1},
                                           headers=headers), 201)

    print("== Pedidos ==")
    r = check("checkout", c.post("/api/orders", json={
        "shipping": {"name": "Tester", "address": "Calle Falsa 123", "city": "Madrid",
                     "postal_code": "28001", "phone": "600111222"},
        "payment_method": "card",
    }, headers=headers), 201)
    order = r.json()
    print(f"     pedido #{order['id']} total {order['total']} EUR estado {order['status']}")
    check("lista pedidos", c.get("/api/orders", headers=headers))
    check("detalle pedido", c.get(f"/api/orders/{order['id']}", headers=headers))
    check("stock descontado", c.get(f"/api/products/{pid}"))  # comprobar visualmente abajo
    stock = c.get(f"/api/products/{pid}").json()["stock"]
    print(f"     stock producto: {stock} (deberia bajar)")

    print("== Resenas ==")
    check("crear resena", c.post(f"/api/products/{slug}/reviews",
                                 json={"rating": 5, "comment": "¡Increíble calidad!"},
                                 headers=headers), 201)
    check("resena duplicada (409)", c.post(f"/api/products/{slug}/reviews",
                                           json={"rating": 4, "comment": "otra"},
                                           headers=headers), 409)
    check("listar resenas", c.get(f"/api/products/{slug}/reviews"))

    print("== Usuario ==")
    check("stats", c.get("/api/users/me/stats", headers=headers))
    check("actualizar perfil", c.put("/api/users/me", json={"full_name": "Tester Actualizado"},
                                     headers=headers))
    check("cambiar password", c.put("/api/users/me/password", json={
        "current_password": "secreta123", "new_password": "nuevaClave456"}, headers=headers))

    print("== Admin ==")
    stats = check("stats admin", c.get("/api/admin/stats", headers=admin_h)).json()
    print(f"     users={stats['users']} products={stats['products']} "
          f"orders={stats['orders']} revenue={stats['revenue']}")
    check("lista productos admin", c.get("/api/admin/products", headers=admin_h))
    r = check("crear producto", c.post("/api/admin/products", json={
        "name": "Peluche Test Admin", "price": 15.5, "stock": 5,
        "category_id": cats[0]["id"], "emoji": "🧸",
    }, headers=admin_h), 201)
    new_id = r.json()["id"]
    check("editar producto", c.put(f"/api/admin/products/{new_id}",
                                   json={"price": 12.0}, headers=admin_h))
    check("cambiar estado pedido", c.patch(f"/api/admin/orders/{order['id']}",
                                           json={"status": "paid"}, headers=admin_h))
    check("lista usuarios admin", c.get("/api/admin/users", headers=admin_h))
    check("borrar producto", c.delete(f"/api/admin/products/{new_id}", headers=admin_h), 204)
    check("no admin sin permisos (403)", c.get("/api/admin/stats", headers=headers), 403)

    print("== Frontend ==")
    for page in ["/", "/tienda.html", "/login.html", "/registro.html", "/carrito.html",
                 "/producto.html", "/admin.html", "/pedidos.html", "/cuenta.html",
                 "/checkout.html", "/static/css/styles.css", "/static/js/api.js"]:
        check(f"GET {page}", c.get(page))

    print(f"\nResultado: {ok} OK, {fail} FALLOS")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
