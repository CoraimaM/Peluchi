/* Peluchi — Página de inicio */

import { api } from "./api.js";
import { initPage, productoCard, bindAddToCartButtons, escapeHTML } from "./ui.js";

function pintarProductos(el, items) {
  if (!el) return;
  el.innerHTML = items.length
    ? items.map(productoCard).join("")
    : `<div class="vacio"><span class="vacio-emoji">🔍</span>
         <h3>No hay productos aún</h3><p>Pronto llegará algo bonito.</p></div>`;
}

async function cargar() {
  const [cats, destacados, novedades, ofertas] = await Promise.all([
    api.get("/categories", { auth: false }).catch(() => []),
    api.get("/products?featured=1&per_page=8", { auth: false }).catch(() => ({ items: [] })),
    api.get("/products?is_new=1&per_page=8", { auth: false }).catch(() => ({ items: [] })),
    api.get("/products?on_sale=1&per_page=8&sort=price_asc", { auth: false }).catch(() => ({ items: [] })),
  ]);

  const gridCats = document.getElementById("categorias");
  if (gridCats) {
    gridCats.innerHTML = cats.length
      ? cats
          .map(
            (c) => `
          <a class="cat-card" href="/tienda.html?cat=${c.slug}">
            <span class="cat-emoji">${c.emoji}</span>
            <strong>${escapeHTML(c.name)}</strong>
            <span>${c.product_count} productos</span>
          </a>`
          )
          .join("")
      : `<div class="vacio"><p>No hay categorías.</p></div>`;
  }

  pintarProductos(document.getElementById("destacados"), destacados.items || []);
  pintarProductos(document.getElementById("novedades"), novedades.items || []);
  pintarProductos(document.getElementById("ofertas"), ofertas.items || []);
}

(async () => {
  await initPage();
  bindAddToCartButtons();
  await cargar();
})();
