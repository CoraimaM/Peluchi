/* Peluchi — Panel de administración */

import { api } from "./api.js";
import {
  initPage, requireAdmin, fmtEUR, fmtFecha, escapeHTML, toast,
} from "./ui.js";

const cont = document.getElementById("contenido");
let categorias = [];
let pestanaActual = "dashboard";

const PESTANAS = {
  dashboard: "📊 Dashboard",
  productos: "🧸 Productos",
  pedidos: "📦 Pedidos",
  usuarios: "👥 Usuarios",
};

const ESTADOS = {
  pending: "Pendiente", paid: "Pagado", shipped: "Enviado",
  delivered: "Entregado", cancelled: "Cancelado",
};

/* --------------------------------------------------------------------------
   Navegación
   -------------------------------------------------------------------------- */
function pintarMenu() {
  const viejo = cont.querySelector(".admin-layout > nav");
  if (viejo) viejo.remove();
  const nav = document.createElement("nav");
  nav.className = "cuenta-menu";
  nav.innerHTML = Object.entries(PESTANAS)
    .map(([k, v]) => `<button class="${k === pestanaActual ? "activo" : ""}" data-tab="${k}">${v}</button>`)
    .join("");
  cont.prepend(nav);
  nav.querySelectorAll("[data-tab]").forEach((b) =>
    b.addEventListener("click", () => cambiarPestana(b.dataset.tab))
  );
}

async function cambiarPestana(tab) {
  pestanaActual = tab;
  pintarMenu();
  const panel = document.getElementById("panel-admin");
  panel.innerHTML = '<div class="cargando">Cargando...</div>';
  try {
    if (tab === "dashboard") await pintaDashboard(panel);
    else if (tab === "productos") await pintaProductos(panel);
    else if (tab === "pedidos") await pintaPedidos(panel);
    else if (tab === "usuarios") await pintaUsuarios(panel);
  } catch (err) {
    panel.innerHTML = `<div class="aviso">${escapeHTML(err.detail || err.message)}</div>`;
  }
}

/* --------------------------------------------------------------------------
   Dashboard
   -------------------------------------------------------------------------- */
async function pintaDashboard(panel) {
  const s = await api.get("/admin/stats");
  panel.innerHTML = `
    <div class="admin-stats">
      <div class="admin-stat"><div class="valor">${fmtEUR(s.revenue)}</div>
        <div class="etiqueta">Ingresos</div></div>
      <div class="admin-stat"><div class="valor">${s.orders}</div>
        <div class="etiqueta">Pedidos</div></div>
      <div class="admin-stat"><div class="valor">${s.users}</div>
        <div class="etiqueta">Usuarios</div></div>
      <div class="admin-stat"><div class="valor">${s.products}</div>
        <div class="etiqueta">Productos</div></div>
      <div class="admin-stat" style="border-color:var(--aviso)">
        <div class="valor">${s.pending_orders}</div>
        <div class="etiqueta">Pendientes</div></div>
      <div class="admin-stat" style="border-color:var(--rosa)">
        <div class="valor">${s.low_stock_products}</div>
        <div class="etiqueta">Stock bajo (≤5)</div></div>
    </div>

    <div class="panel">
      <h2>🕐 Últimos pedidos</h2>
      ${
        s.recent_orders.length
          ? `<div class="tabla-wrap">
              <table class="tabla">
                <thead><tr><th>#</th><th>Cliente</th><th>Fecha</th><th>Total</th><th>Estado</th></tr></thead>
                <tbody>
                  ${s.recent_orders
                    .map(
                      (o) => `<tr>
                        <td><strong>${o.id}</strong></td>
                        <td>${escapeHTML(o.ship_name)}</td>
                        <td>${fmtFecha(o.created_at)}</td>
                        <td>${fmtEUR(o.total)}</td>
                        <td><span class="estado estado-${o.status}">${ESTADOS[o.status]}</span></td>
                      </tr>`
                    )
                    .join("")}
                </tbody>
              </table>
            </div>`
          : '<p style="color:var(--texto-suave)">Todavía no hay pedidos.</p>'
      }
    </div>`;
}

/* --------------------------------------------------------------------------
   Productos
   -------------------------------------------------------------------------- */
async function pintaProductos(panel, busqueda = "") {
  const q = busqueda ? `?q=${encodeURIComponent(busqueda)}` : "";
  const data = await api.get(`/admin/products${q}`);
  if (!categorias.length) categorias = await api.get("/categories", { auth: false });

  panel.innerHTML = `
    <div class="panel-cab">
      <h2>🧸 Productos (${data.total})</h2>
      <div style="display:flex;gap:10px">
        <input class="mini-input" id="buscar-prod" placeholder="Buscar nombre o SKU..."
               value="${escapeHTML(busqueda)}" />
        <button class="btn btn-peque" id="nuevo-producto">＋ Nuevo producto</button>
      </div>
    </div>
    <div class="tabla-wrap">
      <table class="tabla">
        <thead>
          <tr><th></th><th>Producto</th><th>SKU</th><th>Precio</th><th>Stock</th>
              <th>Categoría</th><th>Estado</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          ${data.items
            .map(
              (p) => `<tr>
                <td style="font-size:1.6rem">${p.emoji}</td>
                <td>
                  <strong>${escapeHTML(p.name)}</strong><br/>
                  <small style="color:var(--texto-suave)">
                    ${p.is_featured ? "⭐ " : ""}${p.is_new ? "✨ " : ""}
                    ${p.is_on_sale ? "🔥 Oferta" : ""}
                  </small>
                </td>
                <td><small>${escapeHTML(p.sku)}</small></td>
                <td><strong>${fmtEUR(p.price)}</strong>
                    ${p.is_on_sale ? `<br/><small class="precio-tachado">${fmtEUR(p.compare_price)}</small>` : ""}</td>
                <td>
                  <span class="estado ${p.stock <= 0 ? "estado-cancelled" : p.stock <= 5 ? "estado-pending" : "estado-delivered"}">
                    ${p.stock}
                  </span>
                </td>
                <td>${escapeHTML(p.category?.name || "—")}</td>
                <td>${p.is_active ? '<span class="estado estado-delivered">Visible</span>'
                                  : '<span class="estado estado-cancelled">Oculto</span>'}</td>
                <td class="acciones">
                  <button class="icon-btn" data-editar="${p.id}">✏️</button>
                  <button class="icon-btn gris" data-ocultar="${p.id}" data-valor="${p.is_active}">
                    ${p.is_active ? "🙈" : "👁"}
                  </button>
                  <button class="icon-btn gris" data-borrar="${p.id}">🗑</button>
                </td>
              </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>
    ${data.pages > 1 ? `<p class="texto-center mt-2" style="color:var(--texto-suave)">Página ${data.page} de ${data.pages}</p>` : ""}`;

  let temporizador;
  document.getElementById("buscar-prod").addEventListener("input", (e) => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => pintaProductos(panel, e.target.value.trim()), 450);
  });

  document.getElementById("nuevo-producto").addEventListener("click", () => modalProducto());

  panel.querySelectorAll("[data-editar]").forEach((b) =>
    b.addEventListener("click", async () => {
      const prod = await api.get(`/products/${b.dataset.editar}`, { auth: false });
      modalProducto(prod);
    })
  );

  panel.querySelectorAll("[data-ocultar]").forEach((b) =>
    b.addEventListener("click", async () => {
      try {
        await api.put(`/admin/products/${b.dataset.ocultar}`, {
          is_active: b.dataset.valor !== "true",
        });
        toast("Visibilidad actualizada", "exito");
        await pintaProductos(panel, busqueda);
      } catch (err) {
        toast(err.detail || err.message, "error");
      }
    })
  );

  panel.querySelectorAll("[data-borrar]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (!confirm("¿Eliminar este producto definitivamente?")) return;
      try {
        await api.del(`/admin/products/${b.dataset.borrar}`);
        toast("Producto eliminado", "info");
        await pintaProductos(panel, busqueda);
      } catch (err) {
        toast(err.detail || err.message, "error");
      }
    })
  );
}

function modalProducto(p = null) {
  const esNuevo = !p;
  const fondo = document.createElement("div");
  fondo.className = "modal-fondo";
  fondo.innerHTML = `
    <div class="modal">
      <h2>${esNuevo ? "＋ Nuevo producto" : `✏️ Editar: ${escapeHTML(p.name)}`}</h2>
      <form id="form-producto">
        <div id="aviso-modal"></div>
        <div class="campo">
          <label>Nombre *</label>
          <input type="text" id="m-nombre" required value="${escapeHTML(p?.name || "")}" maxlength="160" />
        </div>
        <div class="form-row">
          <div class="campo">
            <label>Precio € *</label>
            <input type="number" id="m-precio" required min="0.01" step="0.01" value="${p?.price ?? ""}" />
          </div>
          <div class="campo">
            <label>Precio tachado €</label>
            <input type="number" id="m-precio-tachado" min="0.01" step="0.01" value="${p?.compare_price ?? ""}" />
          </div>
        </div>
        <div class="form-row">
          <div class="campo">
            <label>Stock *</label>
            <input type="number" id="m-stock" required min="0" value="${p?.stock ?? 0}" />
          </div>
          <div class="campo">
            <label>Tamaño (cm)</label>
            <input type="number" id="m-tamano" min="1" value="${p?.size_cm ?? ""}" />
          </div>
        </div>
        <div class="form-row">
          <div class="campo">
            <label>Categoría *</label>
            <select id="m-categoria" required>
              ${categorias
                .map(
                  (c) =>
                    `<option value="${c.id}" ${p?.category_id === c.id ? "selected" : ""}>
                      ${c.emoji} ${escapeHTML(c.name)}</option>`
                )
                .join("")}
            </select>
          </div>
          <div class="campo">
            <label>Emoji *</label>
            <input type="text" id="m-emoji" value="${escapeHTML(p?.emoji || "🧸")}" maxlength="4" />
          </div>
        </div>
        <div class="campo">
          <label>Descripción</label>
          <textarea id="m-descripcion" rows="3">${escapeHTML(p?.description || "")}</textarea>
        </div>
        <div class="filtros-opciones">
          <label><input type="checkbox" id="m-destacado" ${p?.is_featured ? "checked" : ""} /> ⭐ Destacado</label>
          <label><input type="checkbox" id="m-nuevo" ${p?.is_new ? "checked" : ""} /> ✨ Novedad</label>
          <label><input type="checkbox" id="m-visible" ${p ? (p.is_active ? "checked" : "") : "checked"} /> 👁 Visible en tienda</label>
        </div>
        <div class="modal-acciones">
          <button type="button" class="btn btn-secundario" id="cancelar">Cancelar</button>
          <button type="submit" class="btn">${esNuevo ? "Crear" : "Guardar"}</button>
        </div>
      </form>
    </div>`;
  document.body.appendChild(fondo);

  const cerrar = () => fondo.remove();
  fondo.addEventListener("click", (e) => {
    if (e.target === fondo) cerrar();
  });
  document.getElementById("cancelar").addEventListener("click", cerrar);

  document.getElementById("form-producto").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById("m-nombre").value.trim(),
      price: Number(document.getElementById("m-precio").value),
      compare_price: document.getElementById("m-precio-tachado").value
        ? Number(document.getElementById("m-precio-tachado").value)
        : null,
      stock: Number(document.getElementById("m-stock").value),
      size_cm: document.getElementById("m-tamano").value
        ? Number(document.getElementById("m-tamano").value)
        : null,
      category_id: Number(document.getElementById("m-categoria").value),
      emoji: document.getElementById("m-emoji").value.trim() || "🧸",
      description: document.getElementById("m-descripcion").value.trim(),
      is_featured: document.getElementById("m-destacado").checked,
      is_new: document.getElementById("m-nuevo").checked,
      is_active: document.getElementById("m-visible").checked,
    };
    try {
      if (esNuevo) {
        await api.post("/admin/products", payload);
        toast("Producto creado ✅", "exito");
      } else {
        await api.put(`/admin/products/${p.id}`, payload);
        toast("Producto actualizado ✅", "exito");
      }
      cerrar();
      await pintaProductos(document.getElementById("panel-admin"));
    } catch (err) {
      document.getElementById("aviso-modal").innerHTML =
        `<div class="aviso">${escapeHTML(err.detail || err.message)}</div>`;
    }
  });
}

/* --------------------------------------------------------------------------
   Pedidos
   -------------------------------------------------------------------------- */
async function pintaPedidos(panel) {
  const pedidos = await api.get("/admin/orders");
  panel.innerHTML = `
    <div class="panel-cab"><h2>📦 Pedidos (${pedidos.length})</h2></div>
    ${
      pedidos.length
        ? `<div class="tabla-wrap">
            <table class="tabla">
              <thead><tr><th>#</th><th>Cliente</th><th>Destino</th><th>Fecha</th>
                         <th>Total</th><th>Estado</th><th>Cambiar a</th></tr></thead>
              <tbody>
                ${pedidos
                  .map(
                    (o) => `<tr>
                      <td><strong>${o.id}</strong></td>
                      <td>${escapeHTML(o.ship_name)}<br/>
                          <small style="color:var(--texto-suave)">${escapeHTML(o.ship_phone)}</small></td>
                      <td><small>${escapeHTML(o.ship_address)}<br/>
                          ${escapeHTML(o.ship_postal_code)} ${escapeHTML(o.ship_city)}</small></td>
                      <td>${fmtFecha(o.created_at)}</td>
                      <td><strong>${fmtEUR(o.total)}</strong></td>
                      <td><span class="estado estado-${o.status}">${ESTADOS[o.status]}</span></td>
                      <td>
                        <select class="mini-input" data-pedido="${o.id}" style="padding:7px 10px">
                          ${Object.entries(ESTADOS)
                            .map(
                              ([k, v]) =>
                                `<option value="${k}" ${k === o.status ? "selected" : ""}>${v}</option>`
                            )
                            .join("")}
                        </select>
                      </td>
                    </tr>`
                  )
                  .join("")}
              </tbody>
            </table>
          </div>`
        : '<div class="vacio"><span class="vacio-emoji">📦</span><h3>No hay pedidos aún</h3></div>'
    }`;

  panel.querySelectorAll("[data-pedido]").forEach((sel) =>
    sel.addEventListener("change", async () => {
      try {
        await api.patch(`/admin/orders/${sel.dataset.pedido}`, { status: sel.value });
        toast(`Pedido #${sel.dataset.pedido} → ${ESTADOS[sel.value]}`, "exito");
        await pintaPedidos(panel);
      } catch (err) {
        toast(err.detail || err.message, "error");
      }
    })
  );
}

/* --------------------------------------------------------------------------
   Usuarios
   -------------------------------------------------------------------------- */
async function pintaUsuarios(panel) {
  const usuarios = await api.get("/admin/users");
  panel.innerHTML = `
    <div class="panel-cab"><h2>👥 Usuarios (${usuarios.length})</h2></div>
    <div class="tabla-wrap">
      <table class="tabla">
        <thead><tr><th>Usuario</th><th>Email</th><th>Origen</th><th>Alta</th>
                   <th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>
          ${usuarios
            .map(
              (u) => `<tr>
                <td><strong>${escapeHTML(u.full_name || "—")}</strong></td>
                <td><small>${escapeHTML(u.email)}</small></td>
                <td>${u.provider === "github" ? "🐙 GitHub" : "📧 Email"}</td>
                <td><small>${fmtFecha(u.created_at)}</small></td>
                <td>
                  <span class="estado ${u.role === "admin" ? "estado-shipped" : "estado-paid"}">
                    ${u.role === "admin" ? "Admin" : "Cliente"}
                  </span>
                </td>
                <td>${u.is_active ? '<span class="estado estado-delivered">Activo</span>'
                                  : '<span class="estado estado-cancelled">Suspendido</span>'}</td>
                <td class="acciones">
                  <button class="icon-btn" data-rol="${u.id}" data-valor="${u.role}">
                    ${u.role === "admin" ? "⬇ Quitar admin" : "⬆ Hacer admin"}
                  </button>
                  <button class="icon-btn gris" data-activo="${u.id}" data-valor="${u.is_active}">
                    ${u.is_active ? "🚫 Suspender" : "✅ Activar"}
                  </button>
                </td>
              </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;

  panel.querySelectorAll("[data-rol]").forEach((b) =>
    b.addEventListener("click", async () => {
      const nuevo = b.dataset.valor === "admin" ? "user" : "admin";
      try {
        await api.patch(`/admin/users/${b.dataset.rol}`, { role: nuevo });
        toast("Rol actualizado", "exito");
        await pintaUsuarios(panel);
      } catch (err) {
        toast(err.detail || err.message, "error");
      }
    })
  );

  panel.querySelectorAll("[data-activo]").forEach((b) =>
    b.addEventListener("click", async () => {
      const nuevo = b.dataset.valor !== "true";
      try {
        await api.patch(`/admin/users/${b.dataset.activo}`, { is_active: nuevo });
        toast("Estado actualizado", "exito");
        await pintaUsuarios(panel);
      } catch (err) {
        toast(err.detail || err.message, "error");
      }
    })
  );
}

/* --------------------------------------------------------------------------
   Arranque
   -------------------------------------------------------------------------- */
(async () => {
  await initPage();
  const user = await requireAdmin();
  if (!user) return;
  cont.innerHTML = `<nav class="cuenta-menu"></nav>
                    <section class="panel" id="panel-admin">
                      <div class="cargando">Cargando panel...</div>
                    </section>`;
  pintarMenu();
  await cambiarPestana("dashboard");
})();
