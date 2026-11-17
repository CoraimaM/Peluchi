/* Peluchi — Carrito de compra */

import { api, isLoggedIn } from "./api.js";
import {
  initPage, fmtEUR, escapeHTML, pastel, toast, setCartCount,
} from "./ui.js";

const cont = document.getElementById("contenido");

async function cargar() {
  const cart = await api.get("/cart");
  setCartCount(cart.count);
  document.getElementById("sub-carrito").textContent =
    cart.count === 0
      ? "Tu carrito está esperando algo tierno"
      : `${cart.count} artículo${cart.count > 1 ? "s" : ""} en tu carrito`;

  if (!cart.items.length) {
    cont.innerHTML = `
      <div class="vacio">
        <span class="vacio-emoji">🛒</span>
        <h3>Tu carrito está vacío</h3>
        <p>¡Los peluches no se compran solos! Explora el catálogo.</p>
        <a class="btn" href="/tienda.html">Ver la tienda</a>
      </div>`;
    return;
  }

  const envioGratis = cart.subtotal >= 49 || cart.count === 0;
  const faltaParaEnvio = Math.max(0, 49 - cart.subtotal);

  cont.innerHTML = `
    <div class="carrito-layout">
      <div class="carrito-lista">
        ${cart.items
          .map(
            (it) => `
          <article class="carrito-item">
            <a href="/producto.html?slug=${encodeURIComponent(it.product.slug)}">
              <div class="carrito-item-img" style="background:${pastel(it.product.id)}">${it.product.emoji}</div>
            </a>
            <div class="carrito-item-info">
              <span class="cat">${escapeHTML(it.product.category?.name || "")}</span>
              <h3><a href="/producto.html?slug=${encodeURIComponent(it.product.slug)}">${escapeHTML(it.product.name)}</a></h3>
              <span class="precio">${fmtEUR(it.product.price)}</span>
              <div style="font-size:.82rem;color:var(--texto-suave)">Ref. ${escapeHTML(it.product.sku)}</div>
            </div>
            <div class="carrito-item-der">
              <div class="cantidad-selector" style="margin:0">
                <div class="control">
                  <button data-accion="menos" data-id="${it.id}" data-max="${it.product.stock}">−</button>
                  <input type="number" value="${it.quantity}" readonly />
                  <button data-accion="mas" data-id="${it.id}" data-max="${it.product.stock}">+</button>
                </div>
              </div>
              <strong style="font-family:var(--fuente-titulo);font-size:1.1rem">${fmtEUR(it.line_total)}</strong>
              <button class="borrar" data-accion="borrar" data-id="${it.id}">🗑 Eliminar</button>
            </div>
          </article>`
          )
          .join("")}
      </div>

      <aside class="resumen">
        <h2>Resumen del pedido</h2>
        <div class="resumen-linea"><span>Subtotal</span><strong>${fmtEUR(cart.subtotal)}</strong></div>
        <div class="resumen-linea">
          <span>Envío</span>
          <strong>${cart.shipping === 0 ? "Gratis ✓" : fmtEUR(cart.shipping)}</strong>
        </div>
        ${
          envioGratis
            ? `<div class="envio-gratis">🎉 ¡Tienes envío gratis!</div>`
            : `<div class="envio-gratis" style="background:var(--pastel-amarillo);color:#9a6b00">
                 🚚 Te faltan ${fmtEUR(faltaParaEnvio)} para el envío gratis</div>`
        }
        <div class="resumen-linea total"><span>Total</span><span>${fmtEUR(cart.total)}</span></div>
        <a class="btn btn-ancho mt-2" href="/checkout.html">Tramitar pedido →</a>
        <a class="btn btn-ancho btn-secundario mt-2" href="/tienda.html">Seguir comprando</a>
        <button class="btn btn-ancho btn-peligro mt-2" id="vaciar">Vaciar carrito</button>
      </aside>
    </div>`;

  cont.querySelectorAll("[data-accion]").forEach((el) => {
    el.addEventListener("click", async () => {
      const id = Number(el.dataset.id);
      const accion = el.dataset.accion;
      try {
        let nuevo;
        const actual = cart.items.find((i) => i.id === id);
        if (accion === "borrar") {
          nuevo = await api.del(`/cart/${id}`);
          toast("Artículo eliminado", "info");
        } else {
          const delta = accion === "mas" ? 1 : -1;
          const max = Number(el.dataset.max || 99);
          const qty = Math.min(max, Math.max(1, actual.quantity + delta));
          nuevo = await api.put(`/cart/${id}`, { quantity: qty });
        }
        setCartCount(nuevo.count);
        await cargar();
      } catch (err) {
        toast(err.detail || err.message, "error");
      }
    });
  });

  document.getElementById("vaciar")?.addEventListener("click", async () => {
    if (!confirm("¿Seguro que quieres vaciar el carrito?")) return;
    try {
      const nuevo = await api.del("/cart");
      setCartCount(nuevo.count);
      toast("Carrito vaciado", "info");
      await cargar();
    } catch (err) {
      toast(err.detail || err.message, "error");
    }
  });
}

(async () => {
  await initPage();
  if (!isLoggedIn()) {
    location.href = "/login.html?next=/carrito.html";
    return;
  }
  try {
    await cargar();
  } catch (err) {
    cont.innerHTML = `<div class="vacio"><span class="vacio-emoji">⚠️</span>
      <h3>Error al cargar el carrito</h3><p>${escapeHTML(err.detail || err.message)}</p></div>`;
  }
})();
