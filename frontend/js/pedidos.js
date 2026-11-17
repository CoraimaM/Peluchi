/* Peluchi — Lista de pedidos del usuario */

import { api, isLoggedIn } from "./api.js";
import { initPage, fmtEUR, fmtFecha, escapeHTML } from "./ui.js";

const ESTADOS = {
  pending: ["Pendiente", "estado-pending"],
  paid: ["Pagado", "estado-paid"],
  shipped: ["Enviado", "estado-shipped"],
  delivered: ["Entregado", "estado-delivered"],
  cancelled: ["Cancelado", "estado-cancelled"],
};

const cont = document.getElementById("contenido");

function filaPedido(o, expandido) {
  const [texto, clase] = ESTADOS[o.status] || [o.status, "estado-pending"];
  const detalle = expandido
    ? `<tr class="detalle-pedido">
         <td colspan="6" style="background:var(--crema)">
           <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px">
             <div>
               <strong style="font-family:var(--fuente-titulo)">🧾 Artículos</strong>
               ${o.items
                 .map(
                   (it) =>
                     `<div style="font-size:.9rem;margin-top:6px">${it.product_emoji}
                       ${escapeHTML(it.product_name)} ×${it.quantity} —
                       <strong>${fmtEUR(it.unit_price * it.quantity)}</strong></div>`
                 )
                 .join("")}
             </div>
             <div>
               <strong style="font-family:var(--fuente-titulo)">🚚 Envío</strong>
               <div style="font-size:.9rem;margin-top:6px">
                 ${escapeHTML(o.ship_name)}<br/>
                 ${escapeHTML(o.ship_address)}<br/>
                 ${escapeHTML(o.ship_postal_code)} ${escapeHTML(o.ship_city)}<br/>
                 📞 ${escapeHTML(o.ship_phone)}
               </div>
             </div>
             <div>
               <strong style="font-family:var(--fuente-titulo)">💳 Pago</strong>
               <div style="font-size:.9rem;margin-top:6px">
                 ${({ card: "Tarjeta", paypal: "PayPal", cod: "Contra reembolso" })[o.payment_method] || o.payment_method}<br/>
                 Subtotal: ${fmtEUR(o.subtotal)}<br/>
                 Envío: ${o.shipping_cost === 0 ? "Gratis" : fmtEUR(o.shipping_cost)}<br/>
                 <strong>Total: ${fmtEUR(o.total)}</strong>
               </div>
             </div>
           </div>
         </td>
       </tr>`
    : "";
  return `
    <tr class="fila-pedido" data-id="${o.id}" style="cursor:pointer">
      <td><strong>#${o.id}</strong></td>
      <td>${fmtFecha(o.created_at)}</td>
      <td>${o.items.length} artículo${o.items.length > 1 ? "s" : ""}</td>
      <td><strong>${fmtEUR(o.total)}</strong></td>
      <td><span class="estado ${clase}">${texto}</span></td>
      <td><button class="icon-btn gris">${expandido ? "▲ Ocultar" : "▼ Detalles"}</button></td>
    </tr>
    ${detalle}`;
}

async function cargar() {
  const pedidos = await api.get("/orders");
  if (!pedidos.length) {
    cont.innerHTML = `
      <div class="vacio">
        <span class="vacio-emoji">📦</span>
        <h3>Todavía no has hecho ningún pedido</h3>
        <p>Cuando compres algo, aparecerá aquí con su estado.</p>
        <a class="btn" href="/tienda.html">Empezar a comprar</a>
      </div>`;
    return;
  }

  const abiertos = new Set();
  cont.innerHTML = `
    <div class="tabla-wrap">
      <table class="tabla">
        <thead>
          <tr>
            <th>Pedido</th><th>Fecha</th><th>Artículos</th>
            <th>Total</th><th>Estado</th><th></th>
          </tr>
        </thead>
        <tbody id="tabla-pedidos">
          ${pedidos.map((o) => filaPedido(o, false)).join("")}
        </tbody>
      </table>
    </div>
    <p class="texto-center mt-2" style="color:var(--texto-suave);font-size:.88rem">
      ¿Necesitas ayuda con un pedido? Escríbenos a <strong>hola@peluchi.es</strong>
    </p>`;

  document.getElementById("tabla-pedidos").addEventListener("click", (e) => {
    const fila = e.target.closest(".fila-pedido");
    if (!fila) return;
    const id = Number(fila.dataset.id);
    if (abiertos.has(id)) abiertos.delete(id);
    else abiertos.add(id);
    const tbody = document.getElementById("tabla-pedidos");
    tbody.innerHTML = pedidos.map((o) => filaPedido(o, abiertos.has(o.id))).join("");
  });
}

(async () => {
  await initPage();
  if (!isLoggedIn()) {
    location.href = "/login.html?next=/pedidos.html";
    return;
  }
  try {
    await cargar();
  } catch (err) {
    cont.innerHTML = `<div class="vacio"><span class="vacio-emoji">⚠️</span>
      <h3>Error al cargar pedidos</h3><p>${escapeHTML(err.detail || err.message)}</p></div>`;
  }
})();
