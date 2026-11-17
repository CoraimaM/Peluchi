/* Peluchi — Catálogo con filtros, búsqueda, orden y paginación */

import { api } from "./api.js";
import { initPage, productoCard, bindAddToCartButtons, escapeHTML, toast } from "./ui.js";

const params = new URLSearchParams(location.search);
const estado = {
  q: params.get("q") || "",
  cat: params.get("cat") || "",
  featured: params.get("featured") === "1",
  is_new: params.get("new") === "1",
  on_sale: params.get("sale") === "1",
  min_price: "",
  max_price: "",
  in_stock: false,
  sort: params.get("sort") || "recent",
  page: parseInt(params.get("page") || "1", 10),
};

function construirQuery() {
  const q = new URLSearchParams();
  if (estado.q) q.set("q", estado.q);
  if (estado.cat) q.set("category", estado.cat);
  if (estado.featured) q.set("featured", "true");
  if (estado.is_new) q.set("is_new", "true");
  if (estado.on_sale) q.set("on_sale", "true");
  if (estado.in_stock) q.set("in_stock", "true");
  if (estado.min_price !== "" && !Number.isNaN(+estado.min_price)) q.set("min_price", estado.min_price);
  if (estado.max_price !== "" && !Number.isNaN(+estado.max_price)) q.set("max_price", estado.max_price);
  if (estado.sort) q.set("sort", estado.sort);
  q.set("page", estado.page);
  q.set("per_page", "12");
  return q.toString();
}

function sincronizarURL() {
  const q = new URLSearchParams();
  if (estado.q) q.set("q", estado.q);
  if (estado.cat) q.set("cat", estado.cat);
  if (estado.featured) q.set("featured", "1");
  if (estado.is_new) q.set("new", "1");
  if (estado.on_sale) q.set("sale", "1");
  if (estado.sort && estado.sort !== "recent") q.set("sort", estado.sort);
  if (estado.page > 1) q.set("page", estado.page);
  history.replaceState(null, "", `/tienda.html${q.toString() ? "?" + q : ""}`);
}

async function cargarCategorias() {
  const cont = document.getElementById("filtro-categorias");
  try {
    const cats = await api.get("/categories", { auth: false });
    cont.innerHTML = `
      <label><input type="radio" name="cat" value="" ${!estado.cat ? "checked" : ""} /> Todas</label>
      ${cats
        .map(
          (c) => `<label>
            <input type="radio" name="cat" value="${c.slug}" ${estado.cat === c.slug ? "checked" : ""} />
            ${c.emoji} ${escapeHTML(c.name)} <span style="color:var(--texto-suave)">(${c.product_count})</span>
          </label>`
        )
        .join("")}`;
    cont.querySelectorAll('input[name="cat"]').forEach((input) => {
      input.addEventListener("change", () => {
        estado.cat = input.value;
        estado.page = 1;
        refrescar();
      });
    });
  } catch {
    cont.innerHTML = "<span>No disponible</span>";
  }
}

async function cargarProductos() {
  const grid = document.getElementById("grid-productos");
  grid.innerHTML = '<div class="cargando">Cargando productos...</div>';
  try {
    const data = await api.get(`/products?${construirQuery()}`, { auth: false });

    document.getElementById("resultados-info").textContent =
      data.total === 1 ? "1 producto encontrado" : `${data.total} productos encontrados`;

    // Título según el filtro activo
    const tit = document.getElementById("titulo-tienda");
    const sub = document.getElementById("subtitulo-tienda");
    if (estado.q) {
      tit.textContent = `🔍 Resultados para "${estado.q}"`;
      sub.textContent = "Búsqueda en el catálogo Peluchi";
    } else if (estado.on_sale) {
      tit.textContent = "🔥 Ofertas";
      sub.textContent = "Precios rebajados por tiempo limitado";
    } else if (estado.is_new) {
      tit.textContent = "✨ Novedades";
      sub.textContent = "Lo último en llegar a la tienda";
    } else if (estado.featured) {
      tit.textContent = "⭐ Destacados";
      sub.textContent = "Los favoritos de la comunidad";
    } else {
      tit.textContent = "🛍️ Nuestra tienda";
      sub.textContent = "Todos los peluches de coleccionista";
    }

    grid.innerHTML = data.items.length
      ? data.items.map(productoCard).join("")
      : `<div class="vacio" style="grid-column:1/-1">
           <span class="vacio-emoji">🧸</span>
           <h3>No encontramos peluches con esos filtros</h3>
           <p>Prueba a quitar algún filtro o a buscar otra cosa.</p>
           <button class="btn" id="ver-todo">Ver todo el catálogo</button>
         </div>`;

    grid.querySelector("#ver-todo")?.addEventListener("click", () => (location.href = "/tienda.html"));

    // Paginación
    const pag = document.getElementById("paginacion");
    if (data.pages <= 1) {
      pag.innerHTML = "";
    } else {
      let html = `<button ${data.page <= 1 ? "disabled" : ""} data-page="${data.page - 1}">‹</button>`;
      for (let i = 1; i <= data.pages; i++) {
        html += `<button class="${i === data.page ? "activo" : ""}" data-page="${i}">${i}</button>`;
      }
      html += `<button ${data.page >= data.pages ? "disabled" : ""} data-page="${data.page + 1}">›</button>`;
      pag.innerHTML = html;
      pag.querySelectorAll("button:not(:disabled)").forEach((b) => {
        b.addEventListener("click", () => {
          estado.page = Number(b.dataset.page);
          refrescar();
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      });
    }
  } catch (err) {
    grid.innerHTML = `<div class="vacio" style="grid-column:1/-1">
        <span class="vacio-emoji">⚠️</span><h3>Error al cargar</h3>
        <p>${escapeHTML(err.detail || err.message)}</p></div>`;
  }
}

function refrescar() {
  sincronizarURL();
  cargarProductos();
}

async function main() {
  await initPage();
  bindAddToCartButtons();

  // Sincronizar controles con la URL
  document.getElementById("ordenar").value = estado.sort;
  if (estado.is_new) document.getElementById("f-nuevo").checked = true;
  if (estado.on_sale) document.getElementById("f-oferta").checked = true;

  document.getElementById("ordenar").addEventListener("change", (e) => {
    estado.sort = e.target.value;
    estado.page = 1;
    refrescar();
  });

  const aplicarPrecio = () => {
    estado.min_price = document.getElementById("precio-min").value;
    estado.max_price = document.getElementById("precio-max").value;
    estado.page = 1;
    refrescar();
  };
  document.getElementById("precio-min").addEventListener("change", aplicarPrecio);
  document.getElementById("precio-max").addEventListener("change", aplicarPrecio);

  document.getElementById("f-nuevo").addEventListener("change", (e) => {
    estado.is_new = e.target.checked;
    if (e.target.checked) {
      estado.on_sale = false;
      document.getElementById("f-oferta").checked = false;
    }
    estado.page = 1;
    refrescar();
  });
  document.getElementById("f-oferta").addEventListener("change", (e) => {
    estado.on_sale = e.target.checked;
    if (e.target.checked) {
      estado.is_new = false;
      document.getElementById("f-nuevo").checked = false;
    }
    estado.page = 1;
    refrescar();
  });
  document.getElementById("f-stock").addEventListener("change", (e) => {
    estado.in_stock = e.target.checked;
    estado.page = 1;
    refrescar();
  });

  document.getElementById("limpiar-filtros").addEventListener("click", () => {
    toast("Filtros restablecidos", "info");
    location.href = "/tienda.html";
  });

  await Promise.all([cargarCategorias(), cargarProductos()]);
}

main();
