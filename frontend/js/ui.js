/* ==========================================================================
   Peluchi — Utilidades de interfaz
   Cabecera, pie, tarjetas de producto, toasts y protección de rutas
   ========================================================================== */

import { api, isLoggedIn, getCachedUser, logout, setCachedUser } from "./api.js";

/* --------------------------------------------------------------------------
   Helpers
   -------------------------------------------------------------------------- */
export const fmtEUR = (n) =>
  new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n ?? 0);

export const fmtFecha = (iso) =>
  new Date(iso).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });

export const escapeHTML = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** Paleta pastel determinista por id de producto (sustituye a las imágenes). */
const PASTELES = [
  "linear-gradient(135deg,#ffe5ec,#ffd2dd)",
  "linear-gradient(135deg,#e4f7f0,#d2f1e6)",
  "linear-gradient(135deg,#efe9ff,#e2d9ff)",
  "linear-gradient(135deg,#fff4d6,#ffeab8)",
  "linear-gradient(135deg,#e3f1ff,#d2e7ff)",
  "linear-gradient(135deg,#ffefe0,#ffe2cc)",
  "linear-gradient(135deg,#fde8ff,#f7d2ff)",
  "linear-gradient(135deg,#e8f6ff,#dff2fb)",
];
export const pastel = (id) => PASTELES[Math.abs(id) % PASTELES.length];

export function estrellas(rating, count = null) {
  const r = Math.round(rating ?? 0);
  const stars = "★".repeat(r) + "☆".repeat(5 - r);
  const extra = count !== null ? ` <span>(${count})</span>` : "";
  return `<span class="producto-estrellas" title="${rating ?? 0} de 5">${stars}${extra}</span>`;
}

/* --------------------------------------------------------------------------
   Toasts
   -------------------------------------------------------------------------- */
export function toast(mensaje, tipo = "info") {
  let cont = document.querySelector(".toasts");
  if (!cont) {
    cont = document.createElement("div");
    cont.className = "toasts";
    document.body.appendChild(cont);
  }
  const el = document.createElement("div");
  el.className = `toast ${tipo}`;
  const icono = tipo === "exito" ? "✅" : tipo === "error" ? "⚠️" : "🧸";
  el.innerHTML = `<span>${icono}</span><span>${escapeHTML(mensaje)}</span>`;
  cont.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity .4s";
    setTimeout(() => el.remove(), 400);
  }, 3200);
}

/* --------------------------------------------------------------------------
   Cabecera
   -------------------------------------------------------------------------- */
export async function renderHeader() {
  const cont = document.getElementById("site-header");
  if (!cont) return;

  const user = isLoggedIn() ? getCachedUser() : null;
  const path = location.pathname;
  const params = new URLSearchParams(location.search);

  let categorias = [];
  try {
    categorias = await api.get("/categories", { auth: false });
  } catch {
    /* la cabecera se dibuja aunque falle */
  }

  const navCat = categorias
    .map((c) => {
      const activo = params.get("cat") === c.slug && path.includes("tienda") ? "activo" : "";
      return `<li><a class="${activo}" href="/tienda.html?cat=${c.slug}">${c.emoji} ${escapeHTML(c.name)}</a></li>`;
    })
    .join("");

  const adminLink =
    user?.role === "admin"
      ? `<li><a class="admin-link" href="/admin.html">🛠️ Admin</a></li>`
      : "";

  cont.innerHTML = `
    <div class="topbar">
      <span>🚚 Envío gratis desde 49 €</span><span>📦 Devoluciones en 30 días</span><span>💯 Piezas de coleccionista auténticas</span>
    </div>
    <header class="header">
      <div class="container header-main">
        <button class="hamburger" id="hamburger" aria-label="Menú">☰</button>
        <a href="/" class="logo">
          <span class="logo-emoji">🧸</span>
          <span>Peluchi<small>Peluches de colección</small></span>
        </a>
        <form class="search" id="search-form" role="search">
          <input type="search" name="q" placeholder="Buscar peluches, marcas, SKUs..."
                 value="${escapeHTML(params.get("q") || "")}" aria-label="Buscar" />
          <button type="submit" aria-label="Buscar">🔍</button>
        </form>
        <div class="header-actions">
          ${
            user
              ? `<a class="header-btn" href="/cuenta.html">
                   <span class="icon">${user.avatar_url ? "👤" : "😊"}</span>
                   <span>${escapeHTML((user.full_name || user.email).split(" ")[0])}</span>
                 </a>
                 <button class="header-btn" id="btn-logout">
                   <span class="icon">🚪</span><span>Salir</span>
                 </button>`
              : `<a class="header-btn" href="/login.html">
                   <span class="icon">👤</span><span>Entrar</span>
                 </a>`
          }
          <a class="header-btn" href="/carrito.html">
            <span class="icon">🛒</span><span>Carrito</span>
            <span class="cart-badge" id="cart-badge" style="display:none">0</span>
          </a>
        </div>
      </div>
      <nav class="nav">
        <div class="container">
          <ul class="nav-list" id="nav-list">
            <li><a href="/" class="${path === "/" ? "activo" : ""}">🏠 Inicio</a></li>
            <li><a href="/tienda.html" class="${path.includes("tienda") && !params.get("cat") ? "activo" : ""}">🛍️ Todos</a></li>
            <li><a href="/tienda.html?featured=1">⭐ Destacados</a></li>
            <li><a href="/tienda.html?new=1">✨ Novedades</a></li>
            <li><a href="/tienda.html?sale=1">🔥 Ofertas</a></li>
            ${navCat}
            ${adminLink}
          </ul>
        </div>
      </nav>
    </header>`;

  // Buscador
  document.getElementById("search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = new FormData(e.target).get("q").trim();
    location.href = q ? `/tienda.html?q=${encodeURIComponent(q)}` : "/tienda.html";
  });

  // Menú móvil
  document.getElementById("hamburger").addEventListener("click", () => {
    document.getElementById("nav-list").classList.toggle("abierto");
  });

  // Cerrar sesión
  document.getElementById("btn-logout")?.addEventListener("click", () => {
    logout();
    toast("Has cerrado la sesión", "info");
    setTimeout(() => (location.href = "/"), 400);
  });

  updateCartBadge();
}

/* --------------------------------------------------------------------------
   Badge del carrito
   -------------------------------------------------------------------------- */
export function setCartCount(n) {
  localStorage.setItem("peluchi_cart_count", String(n ?? 0));
  updateCartBadge();
}

export function updateCartBadge() {
  const badge = document.getElementById("cart-badge");
  if (!badge) return;
  const n = parseInt(localStorage.getItem("peluchi_cart_count") || "0", 10);
  badge.style.display = n > 0 ? "flex" : "none";
  badge.textContent = n > 99 ? "99+" : n;
}

/** Sincroniza el contador del carrito con el servidor. */
export async function syncCartCount() {
  if (!isLoggedIn()) return setCartCount(0);
  try {
    const cart = await api.get("/cart");
    setCartCount(cart.count);
  } catch {
    /* silencio */
  }
}

/* --------------------------------------------------------------------------
   Tarjeta de producto
   -------------------------------------------------------------------------- */
export function productoCard(p) {
  const badges = [
    p.is_new ? '<span class="badge badge-nuevo">Nuevo</span>' : "",
    p.is_on_sale ? '<span class="badge badge-oferta">Oferta</span>' : "",
    p.stock <= 0 ? '<span class="badge badge-agotado">Agotado</span>' : "",
  ].join("");

  const precio = p.is_on_sale
    ? `<span class="precio">${fmtEUR(p.price)}</span>
       <span class="precio-tachado">${fmtEUR(p.compare_price)}</span>`
    : `<span class="precio">${fmtEUR(p.price)}</span>`;

  const img = p.image_url
    ? `<img src="${escapeHTML(p.image_url)}" alt="${escapeHTML(p.name)}" loading="lazy" />`
    : `<span>${p.emoji}</span>`;

  return `
    <article class="producto-card">
      <a href="/producto.html?slug=${encodeURIComponent(p.slug)}" aria-label="${escapeHTML(p.name)}">
        <div class="producto-img" style="background:${pastel(p.id)}">
          <div class="badges">${badges}</div>
          ${img}
        </div>
      </a>
      <div class="producto-datos">
        <span class="producto-cat">${escapeHTML(p.category?.name || "Peluches")}</span>
        <a href="/producto.html?slug=${encodeURIComponent(p.slug)}">
          <h3 class="producto-nombre">${escapeHTML(p.name)}</h3>
        </a>
        ${estrellas(p.rating_avg, p.rating_count)}
        <div class="producto-precio">${precio}</div>
        <button class="btn btn-peque anadir-carrito" data-id="${p.id}" ${p.stock <= 0 ? "disabled" : ""}>
          ${p.stock <= 0 ? "Agotado" : "🛒 Añadir al carrito"}
        </button>
      </div>
    </article>`;
}

/** Delegación global: cualquier botón .anadir-carrito añade al carrito. */
export function bindAddToCartButtons(root = document) {
  root.addEventListener("click", async (e) => {
    const btn = e.target.closest(".anadir-carrito");
    if (!btn || btn.disabled) return;
    e.preventDefault();
    if (!isLoggedIn()) {
      toast("Inicia sesión para añadir al carrito", "error");
      setTimeout(() => (location.href = "/login.html?next=" + encodeURIComponent(location.pathname + location.search)), 900);
      return;
    }
    const original = btn.textContent;
    btn.disabled = true;
    try {
      const cart = await api.post("/cart", { product_id: Number(btn.dataset.id), quantity: 1 });
      setCartCount(cart.count);
      toast("Añadido al carrito 🛒", "exito");
      btn.textContent = "✓ Añadido";
      setTimeout(() => {
        btn.textContent = original;
        btn.disabled = false;
      }, 1300);
    } catch (err) {
      toast(err.detail || err.message, "error");
      btn.disabled = false;
    }
  });
}

/* --------------------------------------------------------------------------
   Pie de página
   -------------------------------------------------------------------------- */
export async function renderFooter() {
  const cont = document.getElementById("site-footer");
  if (!cont) return;

  let categorias = [];
  try {
    categorias = await api.get("/categories", { auth: false });
  } catch {
    /* ok */
  }

  cont.innerHTML = `
    <footer class="footer">
      <div class="footer-newsletter">
        <div class="container">
          <div>
            <h3>¡Únete a la familia Peluchi! 🧸</h3>
            <p>Novedades, ediciones limitadas y ofertas exclusivas en tu correo.</p>
          </div>
          <form class="newsletter-form" id="newsletter">
            <input type="email" placeholder="Tu email..." required aria-label="Email" />
            <button class="btn btn-claro" type="submit">Suscribirme</button>
          </form>
        </div>
      </div>
      <div class="container">
        <div class="footer-grid">
          <div>
            <div class="logo"><span class="logo-emoji">🧸</span> Peluchi</div>
            <p>Tu tienda de peluches de coleccionista. Piezas cuidadosamente seleccionadas,
               desde clásicos atemporales hasta ediciones limitadas numeradas.</p>
            <div class="redes">
              <a href="#" title="Instagram" aria-label="Instagram">📷</a>
              <a href="#" title="TikTok" aria-label="TikTok">🎵</a>
              <a href="#" title="Facebook" aria-label="Facebook">👥</a>
              <a href="#" title="YouTube" aria-label="YouTube">▶️</a>
            </div>
          </div>
          <div>
            <h4>Tienda</h4>
            <ul>
              <li><a href="/tienda.html">Todos los productos</a></li>
              <li><a href="/tienda.html?new=1">Novedades</a></li>
              <li><a href="/tienda.html?sale=1">Ofertas</a></li>
              <li><a href="/tienda.html?featured=1">Destacados</a></li>
            </ul>
          </div>
          <div>
            <h4>Categorías</h4>
            <ul>
              ${categorias
                .slice(0, 6)
                .map((c) => `<li><a href="/tienda.html?cat=${c.slug}">${c.emoji} ${escapeHTML(c.name)}</a></li>`)
                .join("")}
            </ul>
          </div>
          <div>
            <h4>Mi cuenta</h4>
            <ul>
              <li><a href="/login.html">Iniciar sesión</a></li>
              <li><a href="/registro.html">Crear cuenta</a></li>
              <li><a href="/cuenta.html">Mi cuenta</a></li>
              <li><a href="/pedidos.html">Mis pedidos</a></li>
              <li><a href="/carrito.html">Carrito</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        © ${new Date().getFullYear()} Peluchi — Tienda de peluches de coleccionista ·
        Proyecto demo con FastAPI + PostgreSQL · <a href="/docs" style="text-decoration:underline">API Docs</a>
      </div>
    </footer>`;

  document.getElementById("newsletter").addEventListener("submit", (e) => {
    e.preventDefault();
    e.target.reset();
    toast("¡Gracias por suscribirte! 💌", "exito");
  });
}

/* --------------------------------------------------------------------------
   Protección de rutas
   -------------------------------------------------------------------------- */
/** Devuelve el usuario o redirige a login. */
export async function requireAuth() {
  if (!isLoggedIn()) {
    const next = encodeURIComponent(location.pathname + location.search);
    location.href = `/login.html?next=${next}`;
    return null;
  }
  try {
    return await api.fetchMe();
  } catch {
    location.href = "/login.html";
    return null;
  }
}

/** Devuelve el usuario admin o redirige. */
export async function requireAdmin() {
  const user = await requireAuth();
  if (!user) return null;
  if (user.role !== "admin") {
    toast("Se requieren permisos de administrador", "error");
    setTimeout(() => (location.href = "/"), 1200);
    return null;
  }
  return user;
}

/* --------------------------------------------------------------------------
   Arranque común de cada página
   -------------------------------------------------------------------------- */
export async function initPage() {
  await renderHeader();
  await renderFooter();
}
