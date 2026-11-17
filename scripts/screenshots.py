"""Capturas de pantalla del frontend (Playwright) para documentación.

    python scripts/screenshots.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
SALIDA = Path(__file__).resolve().parent.parent / "screenshots"
SALIDA.mkdir(exist_ok=True)


def main() -> None:
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        ctx = navegador.new_context(viewport={"width": 1366, "height": 900},
                                    device_scale_factor=1)
        page = ctx.new_page()

        # 1. Inicio
        page.goto(f"{BASE}/", wait_until="networkidle")
        page.wait_for_timeout(600)
        page.screenshot(path=SALIDA / "01-inicio.png", full_page=True)
        print("  01-inicio.png")

        # 2. Tienda
        page.goto(f"{BASE}/tienda.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=SALIDA / "02-tienda.png", full_page=True)
        print("  02-tienda.png")

        # 3. Ficha de producto
        page.goto(f"{BASE}/producto.html?slug=oso-vintage-serie-1950-30cm",
                  wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=SALIDA / "03-producto.png", full_page=True)
        print("  03-producto.png")

        # 4. Login
        page.goto(f"{BASE}/login.html", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=SALIDA / "04-login.png", full_page=True)
        print("  04-login.png")

        # 5. Admin (login primero)
        page.fill("#email", "admin@peluchi.es")
        page.fill("#password", "admin1234")
        page.click("#btn-entrar")
        page.wait_for_url(f"{BASE}/admin.html", timeout=10000)
        page.wait_for_selector(".admin-stat", timeout=10000)
        page.wait_for_timeout(400)
        page.screenshot(path=SALIDA / "05-admin.png", full_page=True)
        print("  05-admin.png")

        # 6. Productos del panel admin
        page.click('[data-tab="productos"]')
        page.wait_for_selector(".tabla", timeout=8000)
        page.wait_for_timeout(300)
        page.screenshot(path=SALIDA / "06-admin-productos.png", full_page=True)
        print("  06-admin-productos.png")

        # 7. Carrito con un artículo (añadir desde la tienda)
        page.goto(f"{BASE}/tienda.html", wait_until="networkidle")
        page.locator(".producto-card .anadir-carrito:not([disabled])").first.click()
        page.wait_for_timeout(1000)
        page.goto(f"{BASE}/carrito.html", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=SALIDA / "07-carrito.png", full_page=True)
        print("  07-carrito.png")

        # 8. Móvil (inicio)
        movil = navegador.new_context(viewport={"width": 390, "height": 844},
                                      device_scale_factor=2, is_mobile=True)
        pm = movil.new_page()
        pm.goto(f"{BASE}/", wait_until="networkidle")
        pm.wait_for_timeout(600)
        pm.screenshot(path=SALIDA / "08-inicio-movil.png", full_page=True)
        print("  08-inicio-movil.png")

        navegador.close()
    print(f"\nGuardadas en: {SALIDA}")


if __name__ == "__main__":
    main()
