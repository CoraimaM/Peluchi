/* Peluchi — Checkout: datos de envío + confirmación del pedido */

import { api, isLoggedIn } from "./api.js";
import { initPage, fmtEUR, escapeHTML, toast } from "./ui.js";

const cont = document.getElementById("contenido");
let cart = null;

async function cargar() {
  cart = await api.get("/cart");
  if (!cart.items.length) {
    cont.innerHTML = `
      <div class="vacio">
        <span class="vacio-emoji">🛒</span>
        <h3>No hay nada que pagar</h3>
        <p>Añade algún peluche al carrito primero.</p>
        <a class="btn" href="/tienda.html">Ir a la tienda</a>
      </div>`;
    return null;
  }

  cont.innerHTML = `
    <div class="carrito-layout">
      <form class="form-card" id="checkout-form" novalidate>
        <h2 style="margin-bottom:18px">📦 Datos de envío</h2>
        <div id="aviso"></div>

        <div class="campo">
          <label for="nombre">Nombre completo *</label>
          <input type="text" id="nombre" required maxlength="120" autocomplete="name" />
        </div>
        <div class="campo">
          <label for="direccion">Dirección *</label>
          <input type="text" id="direccion" placeholder="Calle, número, piso..." required
                 maxlength="255" autocomplete="street-address" />
        </div>
        <div class="form-row">
          <div class="campo">
            <label for="cp">Código postal *</label>
            <input type="text" id="cp" placeholder="28001" required maxlength="10"
                   autocomplete="postal-code" />
          </div>
          <div class="campo">
            <label for="ciudad">Ciudad *</label>
            <input type="text" id="ciudad" required maxlength="100" autocomplete="address-level2" />
          </div>
        </div>
        <div class="campo">
          <label for="telefono">Teléfono *</label>
          <input type="tel" id="telefono" placeholder="600 123 456" required maxlength="20"
                 autocomplete="tel" />
        </div>

        <h2 style="margin:22px 0 14px">💳 Método de pago</h2>
        <div class="filtros-opciones">
          <label><input type="radio" name="pago" value="card" checked /> 💳 Tarjeta (demo)</label>
          <label><input type="radio" name="pago" value="paypal" /> 🅿️ PayPal (demo)</label>
          <label><input type="radio" name="pago" value="cod" /> 💵 Contra reembolso</label>
        </div>
        <div class="campo-hint" style="margin-top:6px">
          Modo demostración: no se realiza ningún cargo real.
        </div>

        <button class="btn btn-ancho mt-2" type="submit" id="btn-pagar">
          Confirmar pedido · ${fmtEUR(cart.total)}
        </button>
      </form>

      <aside class="resumen">
        <h2>Tu pedido</h2>
        ${cart.items
          .map(
            (it) => `
          <div class="resumen-linea">
            <span>${it.product.emoji} ${escapeHTML(it.product.name)}
              <span style="color:var(--texto-suave)">×${it.quantity}</span></span>
            <strong>${fmtEUR(it.line_total)}</strong>
          </div>`
          )
          .join("")}
        <div class="resumen-linea"><span>Subtotal</span><strong>${fmtEUR(cart.subtotal)}</strong></div>
        <div class="resumen-linea">
          <span>Envío</span><strong>${cart.shipping === 0 ? "Gratis ✓" : fmtEUR(cart.shipping)}</strong>
        </div>
        <div class="resumen-linea total"><span>Total</span><span>${fmtEUR(cart.total)}</span></div>
        <a class="btn btn-ancho btn-secundario mt-2" href="/carrito.html">← Volver al carrito</a>
      </aside>
    </div>`;

  // Prellenar con el perfil del usuario
  try {
    const me = await api.get("/auth/me");
    document.getElementById("nombre").value = me.full_name || "";
  } catch {
    /* opcional */
  }

  document.getElementById("checkout-form").addEventListener("submit", pagar);
}

async function pagar(e) {
  e.preventDefault();
  const aviso = document.getElementById("aviso");
  aviso.innerHTML = "";

  const payload = {
    shipping: {
      name: document.getElementById("nombre").value.trim(),
      address: document.getElementById("direccion").value.trim(),
      city: document.getElementById("ciudad").value.trim(),
      postal_code: document.getElementById("cp").value.trim(),
      phone: document.getElementById("telefono").value.trim(),
    },
    payment_method: document.querySelector('input[name="pago"]:checked').value,
  };

  for (const [k, v] of Object.entries(payload.shipping)) {
    if (!v) {
      aviso.innerHTML = '<div class="aviso">Completa todos los campos de envío.</div>';
      return;
    }
  }

  const btn = document.getElementById("btn-pagar");
  btn.disabled = true;
  btn.textContent = "Procesando...";

  try {
    const order = await api.post("/orders", payload);
    localStorage.removeItem("peluchi_cart_count");
    cont.innerHTML = `
      <div class="vacio" style="max-width:560px;margin:0 auto">
        <span class="vacio-emoji">🎉</span>
        <h3>¡Pedido #${order.id} confirmado!</h3>
        <p>Gracias por tu compra. Total: <strong>${fmtEUR(order.total)}</strong><br/>
           Te enviaremos una actualización a tu email.</p>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
          <a class="btn" href="/pedidos.html">Ver mis pedidos</a>
          <a class="btn btn-secundario" href="/tienda.html">Seguir comprando</a>
        </div>
      </div>`;
    toast("¡Pedido realizado con éxito! 🎉", "exito");
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    aviso.innerHTML = `<div class="aviso">${escapeHTML(err.detail || err.message)}</div>`;
    btn.disabled = false;
    btn.textContent = `Confirmar pedido · ${fmtEUR(cart.total)}`;
  }
}

(async () => {
  await initPage();
  if (!isLoggedIn()) {
    location.href = "/login.html?next=/checkout.html";
    return;
  }
  try {
    await cargar();
  } catch (err) {
    cont.innerHTML = `<div class="vacio"><span class="vacio-emoji">⚠️</span>
      <h3>Error</h3><p>${escapeHTML(err.detail || err.message)}</p></div>`;
  }
})();
