/* Peluchi — Ficha de producto + reseñas + relacionados */

import { api, isLoggedIn } from "./api.js";
import {
  initPage, productoCard, bindAddToCartButtons, fmtEUR, fmtFecha,
  escapeHTML, pastel, estrellas, toast, setCartCount,
} from "./ui.js";

const slug = new URLSearchParams(location.search).get("slug");
let producto = null;

async function cargarProducto() {
  if (!slug) throw { detail: "Falta el parámetro ?slug=" };
  producto = await api.get(`/products/${encodeURIComponent(slug)}`, { auth: false });
}

function pintar() {
  const p = producto;

  document.title = `${p.name} — Peluchi 🧸`;
  document.getElementById("miga-categoria").textContent = p.category?.name || "Peluches";
  document.getElementById("ficha-cat").textContent = p.category?.name || "";
  document.getElementById("ficha-nombre").textContent = p.name;
  document.getElementById("ficha-sku").textContent = `Ref. ${p.sku} · ${p.brand}`;
  document.getElementById("ficha-estrellas").innerHTML = estrellas(p.rating_avg, p.rating_count);

  const img = document.getElementById("ficha-img");
  img.style.background = pastel(p.id);
  img.innerHTML = p.image_url
    ? `<img src="${escapeHTML(p.image_url)}" alt="${escapeHTML(p.name)}" />`
    : `<span>${p.emoji}</span>`;

  document.getElementById("ficha-precio").innerHTML = p.is_on_sale
    ? `<span class="precio">${fmtEUR(p.price)}</span>
       <span class="precio-tachado">${fmtEUR(p.compare_price)}</span>
       <span class="badge badge-oferta">-${Math.round((1 - p.price / p.compare_price) * 100)} %</span>`
    : `<span class="precio">${fmtEUR(p.price)}</span>`;

  document.getElementById("ficha-desc").textContent = p.description;

  document.getElementById("ficha-meta").innerHTML = `
    <div><span>Tamaño</span><strong>${p.size_cm ? p.size_cm + " cm" : "Variable"}</strong></div>
    <div><span>Material</span><strong>${escapeHTML(p.material)}</strong></div>
    <div><span>Marca</span><strong>${escapeHTML(p.brand)}</strong></div>
    <div><span>Stock</span><strong>${p.stock > 0 ? p.stock + " uds." : "Agotado"}</strong></div>`;

  document.getElementById("stock-info").innerHTML =
    p.stock <= 0
      ? '<span class="stock-bajo">Agotado</span>'
      : p.stock <= 5
        ? `<span class="stock-bajo">¡Solo quedan ${p.stock}!</span>`
        : '<span class="stock-ok">✓ En stock</span>';

  const btn = document.getElementById("btn-comprar");
  if (p.stock <= 0) {
    btn.disabled = true;
    btn.textContent = "Agotado";
  }

  // Cantidad
  const input = document.getElementById("cantidad");
  const max = Math.min(p.stock || 1, 99);
  document.getElementById("menos").addEventListener("click", () => {
    input.value = Math.max(1, Number(input.value) - 1);
  });
  document.getElementById("mas").addEventListener("click", () => {
    input.value = Math.min(max, Number(input.value) + 1);
  });

  btn.addEventListener("click", async () => {
    if (!isLoggedIn()) {
      toast("Inicia sesión para comprar", "error");
      setTimeout(() => (location.href = `/login.html?next=${encodeURIComponent(location.pathname + location.search)}`), 900);
      return;
    }
    btn.disabled = true;
    try {
      const cart = await api.post("/cart", { product_id: p.id, quantity: Number(input.value) });
      setCartCount(cart.count);
      toast(`Añadido: ${input.value} × ${p.name} 🛒`, "exito");
    } catch (err) {
      toast(err.detail || err.message, "error");
    } finally {
      btn.disabled = p.stock <= 0;
    }
  });
}

async function cargarResenas() {
  const cont = document.getElementById("lista-resenas");
  try {
    const resenas = await api.get(`/products/${encodeURIComponent(slug)}/reviews`, { auth: false });
    document.getElementById("resumen-resenas").textContent = resenas.length
      ? `${resenas.length} reseña${resenas.length > 1 ? "s" : ""} de clientes verificados`
      : "Sé el primero en reseñar este peluche";
    cont.innerHTML = resenas.length
      ? resenas
          .map(
            (r) => `
          <article class="resena">
            <div class="resena-cab">
              <strong>${escapeHTML(r.user_name)}</strong>
              <span class="resena-estrellas">${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)}</span>
            </div>
            <div class="resena-fecha">${fmtFecha(r.created_at)}</div>
            ${r.comment ? `<p>${escapeHTML(r.comment)}</p>` : "<p>Sin comentario</p>"}
          </article>`
          )
          .join("")
      : `<div class="vacio" style="grid-column:1/-1"><span class="vacio-emoji">💭</span>
           <h3>Todavía no hay reseñas</h3><p>¡Sé la primera persona en opinar!</p></div>`;
  } catch {
    cont.innerHTML = "";
  }
}

function bindFormResena() {
  const aviso = document.getElementById("aviso-resena");
  if (!isLoggedIn()) {
    document.getElementById("form-resena").innerHTML = `
      <div class="aviso">Para reseñar necesitas <a href="/login.html" style="text-decoration:underline">iniciar sesión</a>.</div>`;
    return;
  }
  document.getElementById("resena-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api.post(`/products/${encodeURIComponent(slug)}/reviews`, {
        rating: Number(document.getElementById("rating").value),
        comment: document.getElementById("comentario").value.trim(),
      });
      toast("¡Reseña publicada! 💖", "exito");
      await Promise.all([cargarResenas(), cargarProducto()]);
      pintar();
      aviso.innerHTML = "";
      e.target.reset();
    } catch (err) {
      aviso.innerHTML = `<div class="aviso">${escapeHTML(err.detail || err.message)}</div>`;
    }
  });
}

async function cargarRelacionados() {
  if (!producto?.category) return;
  try {
    const data = await api.get(
      `/products?category=${producto.category.slug}&per_page=8`, { auth: false });
    const otros = data.items.filter((x) => x.id !== producto.id).slice(0, 4);
    document.getElementById("relacionados").innerHTML = otros.map(productoCard).join("");
  } catch {
    /* silencio */
  }
}

(async () => {
  await initPage();
  bindAddToCartButtons();
  try {
    await cargarProducto();
    document.getElementById("carga-producto").classList.add("oculto");
    document.getElementById("contenido").classList.remove("oculto");
    pintar();
    await Promise.all([cargarResenas(), cargarRelacionados()]);
    bindFormResena();
  } catch (err) {
    document.getElementById("carga-producto").innerHTML = `
      <div class="vacio">
        <span class="vacio-emoji">🔍</span>
        <h3>Producto no encontrado</h3>
        <p>${escapeHTML(err.detail || err.message || "Error inesperado")}</p>
        <a class="btn" href="/tienda.html">Volver a la tienda</a>
      </div>`;
  }
})();
