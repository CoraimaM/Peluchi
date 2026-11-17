"""Test E2E del frontend con Playwright (Chromium headless).

Valida que cada página renderiza sin errores de JavaScript y ejecuta
el flujo completo: login → carrito → checkout → pedidos → admin.

Ejecutar con el servidor levantado:  python scripts/ui_test.py
"""

import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
errores_js: list[str] = []
fallos: list[str] = []
ok_count = 0


def check(nombre: str, cond: bool, extra: str = ""):
    global ok_count
    if cond:
        ok_count += 1
        print(f"  [OK] {nombre}")
    else:
        fallos.append(nombre)
        print(f"  [FAIL] {nombre} {extra}")


def escuchar(page, nombre_pagina):
    page.on("pageerror", lambda e: errores_js.append(f"{nombre_pagina}: {e}"))
    page.on(
        "console",
        lambda m: errores_js.append(f"{nombre_pagina} (console): {m.text}")
        if m.type == "error"
        else None,
    )


def main() -> int:
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        ctx = navegador.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()

        # ------------------------------------------------------------------
        print("== Inicio ==")
        escuchar(page, "inicio")
        page.goto(f"{BASE}/", wait_until="networkidle")
        check("hero visible", page.locator(".hero h1").count() == 1)
        check("categorias pintadas", page.locator(".cat-card").count() >= 6,
              f"(hay {page.locator('.cat-card').count()})")
        check("productos destacados", page.locator("#destacados .producto-card").count() >= 1)
        check("productos novedades", page.locator("#novedades .producto-card").count() >= 1)
        check("ofertas", page.locator("#ofertas .producto-card").count() >= 1)
        check("footer renderizado", page.locator(".footer-grid").count() == 1)
        check("header con buscador", page.locator("#search-form").count() == 1)
        check("badge carrito oculto al entrar", not page.locator("#cart-badge").is_visible())

        # ------------------------------------------------------------------
        print("== Tienda y filtros ==")
        escuchar(page, "tienda")
        page.goto(f"{BASE}/tienda.html", wait_until="networkidle")
        total_inicial = page.locator(".producto-card").count()
        check("grid de productos", total_inicial >= 8, f"(hay {total_inicial})")
        check("filtros laterales", page.locator(".filtros").count() == 1)

        # Filtrar por una categoría concreta
        page.locator('#filtro-categorias input[value="kawaii"]').check()
        page.wait_for_timeout(900)
        check("filtro por categoria aplica",
              "cat=kawaii" in page.url and page.locator(".producto-card").count() >= 1,
              f"(url={page.url})")

        # Búsqueda por texto
        page.goto(f"{BASE}/tienda.html?q=oso", wait_until="networkidle")
        check("busqueda q=oso", page.locator(".producto-card").count() >= 1)

        # ------------------------------------------------------------------
        print("== Ficha de producto ==")
        escuchar(page, "producto")
        page.goto(f"{BASE}/producto.html?slug=oso-vintage-serie-1950-30cm", wait_until="networkidle")
        check("nombre del producto", page.locator("#ficha-nombre").inner_text().startswith("Oso Vintage"))
        check("precio visible", "€" in page.locator("#ficha-precio").inner_text())
        check("meta (tamaño/material)", page.locator(".ficha-meta div").count() >= 4)
        check("seccion resenas", page.locator("#lista-resenas").count() == 1)

        # ------------------------------------------------------------------
        print("== Registro ==")
        escuchar(page, "registro")
        page.goto(f"{BASE}/registro.html", wait_until="networkidle")
        import time
        email_e2e = f"e2e-{int(time.time())}@example.com"
        page.fill("#nombre", "Usuario E2E")
        page.fill("#email", email_e2e)
        page.fill("#password", "clave12345")
        page.fill("#password2", "clave12345")
        page.click("#btn-crear")
        page.wait_for_url(f"{BASE}/", timeout=10000)
        check("registro redirige al inicio", page.url == f"{BASE}/")
        check("header muestra usuario", "Usuario" in page.locator(".header-actions").inner_text())

        # ------------------------------------------------------------------
        print("== Anadir al carrito ==")
        escuchar(page, "carrito")
        page.goto(f"{BASE}/tienda.html", wait_until="networkidle")
        page.locator(".producto-card .anadir-carrito:not([disabled])").first.click()
        page.wait_for_timeout(1200)
        badge = page.locator("#cart-badge")
        check("badge del carrito actualiza", badge.is_visible() and badge.inner_text() == "1",
              f"(texto={badge.inner_text() if badge.count() else 'n/a'})")

        page.goto(f"{BASE}/carrito.html", wait_until="networkidle")
        check("articulo en el carrito", page.locator(".carrito-item").count() >= 1)
        check("resumen con total", "Total" in page.locator(".resumen").inner_text())

        # ------------------------------------------------------------------
        print("== Checkout ==")
        escuchar(page, "checkout")
        page.goto(f"{BASE}/checkout.html", wait_until="networkidle")
        page.fill("#nombre", "Usuario E2E")
        page.fill("#direccion", "Calle de la Prueba 42")
        page.fill("#cp", "28001")
        page.fill("#ciudad", "Madrid")
        page.fill("#telefono", "600111222")
        page.click("#btn-pagar")
        page.wait_for_selector("text=confirmado", timeout=10000)
        check("pedido confirmado", "confirmado" in page.locator("#contenido").inner_text())

        # ------------------------------------------------------------------
        print("== Pedidos y cuenta ==")
        escuchar(page, "pedidos")
        page.goto(f"{BASE}/pedidos.html", wait_until="networkidle")
        check("lista de pedidos", page.locator(".fila-pedido").count() >= 1)
        page.locator(".fila-pedido").first.click()
        page.wait_for_timeout(400)
        check("detalle de pedido desplegable",
              page.locator(".detalle-pedido").count() >= 1)

        escuchar(page, "cuenta")
        page.goto(f"{BASE}/cuenta.html", wait_until="networkidle")
        check("stats de cuenta", page.locator(".stat-card").count() >= 4)
        check("formulario de perfil", page.locator("#form-perfil").count() == 1)

        # ------------------------------------------------------------------
        print("== Login (cliente demo) ==")
        # Cerrar la sesión del usuario E2E antes de continuar
        page.goto(f"{BASE}/", wait_until="networkidle")
        if page.locator("#btn-logout").count():
            page.click("#btn-logout")
            page.wait_for_timeout(1500)

        escuchar(page, "login")
        page.goto(f"{BASE}/login.html", wait_until="networkidle")
        check("boton GitHub presente", page.locator("#btn-github").count() == 1)
        page.fill("#email", "cliente@peluchi.es")
        page.fill("#password", "cliente123")
        page.click("#btn-entrar")
        page.wait_for_url(f"{BASE}/", timeout=10000)
        check("login cliente demo OK", page.url == f"{BASE}/")

        # ------------------------------------------------------------------
        print("== Admin ==")
        escuchar(page, "admin")
        page.goto(f"{BASE}/login.html", wait_until="networkidle")
        if page.url != f"{BASE}/login.html":
            # Si arrastra sesión, salir primero
            page.goto(f"{BASE}/", wait_until="networkidle")
            if page.locator("#btn-logout").count():
                page.click("#btn-logout")
                page.wait_for_timeout(1200)
            page.goto(f"{BASE}/login.html", wait_until="networkidle")
        page.fill("#email", "admin@peluchi.es")
        page.fill("#password", "admin1234")
        page.click("#btn-entrar")
        page.wait_for_url(f"{BASE}/admin.html", timeout=10000)
        check("login admin redirige al panel", "admin" in page.url)
        page.wait_for_selector(".admin-stat", timeout=10000)
        check("stats admin", page.locator(".admin-stat").count() >= 4)

        page.click('[data-tab="productos"]')
        page.wait_for_selector(".tabla", timeout=8000)
        check("tabla de productos admin", page.locator(".tabla tbody tr").count() >= 5)

        page.click('[data-tab="pedidos"]')
        page.wait_for_selector(".tabla", timeout=8000)
        check("tabla de pedidos admin", page.locator(".tabla tbody tr").count() >= 1)

        page.click('[data-tab="usuarios"]')
        page.wait_for_selector(".tabla", timeout=8000)
        check("tabla de usuarios admin", page.locator(".tabla tbody tr").count() >= 2)

        # ------------------------------------------------------------------
        print("== Errores de JavaScript ==")
        check("sin errores JS en todo el recorrido", not errores_js,
              "| " + " || ".join(errores_js[:5]))

        navegador.close()

    print(f"\nResultado UI: {ok_count} OK, {len(fallos)} FALLOS")
    if fallos:
        for f in fallos:
            print(f"  - {f}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
