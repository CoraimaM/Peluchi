/* Peluchi — Mi cuenta: datos personales, contraseña y estadísticas */

import { api, isLoggedIn } from "./api.js";
import { initPage, fmtEUR, fmtFecha, escapeHTML, toast } from "./ui.js";

const cont = document.getElementById("contenido");
let user = null;
let stats = null;

const PESTANAS = {
  perfil: "👤 Perfil",
  password: "🔒 Contraseña",
  compras: "📦 Mis pedidos",
};

function pintar(activa = "perfil") {
  const iniciales = (user.full_name || user.email)
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  cont.innerHTML = `
    <nav class="cuenta-menu">
      ${Object.entries(PESTANAS)
        .map(
          ([k, v]) =>
            `<button class="${k === activa ? "activo" : ""}" data-tab="${k}">${v}</button>`
        )
        .join("")}
      ${user.role === "admin" ? `<button data-tab="admin">🛠️ Administración</button>` : ""}
      <button data-tab="salir" style="color:var(--rojo)">🚪 Cerrar sesión</button>
    </nav>

    <section class="panel" id="panel-cuenta">${contenidoPestana(activa)}</section>`;

  cont.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      if (tab === "salir") {
        localStorage.removeItem("peluchi_access");
        localStorage.removeItem("peluchi_refresh");
        localStorage.removeItem("peluchi_user");
        localStorage.removeItem("peluchi_cart_count");
        toast("Sesión cerrada", "info");
        setTimeout(() => (location.href = "/"), 500);
        return;
      }
      if (tab === "admin") {
        location.href = "/admin.html";
        return;
      }
      if (tab === "compras") {
        location.href = "/pedidos.html";
        return;
      }
      pintar(tab);
    });
  });

  bindForms();
}

function contenidoPestana(tab) {
  if (tab === "password") {
    if (user.provider === "github" && !user.hashed_password) {
      return `
        <h2>🔒 Contraseña</h2>
        <div class="aviso" style="background:var(--pastel-azul);border-color:#c9e4ff;color:#1565c0">
          Tu cuenta se crea a través de <strong>GitHub</strong>, por lo que no tiene contraseña propia.
        </div>`;
    }
    return `
      <h2>🔒 Cambiar contraseña</h2>
      <form id="form-password" style="max-width:440px">
        <div id="aviso-password"></div>
        <div class="campo">
          <label>Contraseña actual</label>
          <input type="password" id="pass-actual" required autocomplete="current-password" />
        </div>
        <div class="campo">
          <label>Nueva contraseña</label>
          <input type="password" id="pass-nueva" required minlength="6" autocomplete="new-password" />
          <div class="campo-hint">Mínimo 6 caracteres.</div>
        </div>
        <div class="campo">
          <label>Repite la nueva contraseña</label>
          <input type="password" id="pass-nueva2" required autocomplete="new-password" />
        </div>
        <button class="btn" type="submit">Actualizar contraseña</button>
      </form>`;
  }

  // Perfil por defecto
  return `
    <div class="stats-grid">
      <div class="stat-card"><div class="valor">${stats.orders}</div><div class="etiqueta">Pedidos</div></div>
      <div class="stat-card"><div class="valor">${fmtEUR(stats.spent)}</div><div class="etiqueta">Gastado</div></div>
      <div class="stat-card"><div class="valor">${stats.reviews}</div><div class="etiqueta">Reseñas</div></div>
      <div class="stat-card"><div class="valor">${fmtFecha(stats.member_since)}</div><div class="etiqueta">Cliente desde</div></div>
    </div>

    <div style="display:flex;align-items:center;gap:20px;margin-bottom:22px">
      <div class="perfil-avatar">${escapeHTML(inicialesDe(user))}</div>
      <div>
        <h2 style="margin-bottom:4px">${escapeHTML(user.full_name || "Sin nombre")}</h2>
        <div style="color:var(--texto-suave)">
          ${escapeHTML(user.email)} ·
          <span class="estado ${user.role === "admin" ? "estado-shipped" : "estado-paid"}">
            ${user.role === "admin" ? "Administrador" : "Cliente"}
          </span>
          ${user.provider === "github" ? '<span class="estado estado-delivered" style="margin-left:6px">GitHub ✓</span>' : ""}
        </div>
      </div>
    </div>

    <form id="form-perfil">
      <div id="aviso-perfil"></div>
      <div class="form-row">
        <div class="campo">
          <label>Nombre completo</label>
          <input type="text" id="perfil-nombre" value="${escapeHTML(user.full_name)}" maxlength="120" />
        </div>
        <div class="campo">
          <label>Email</label>
          <input type="email" id="perfil-email" value="${escapeHTML(user.email)}" />
        </div>
      </div>
      <button class="btn" type="submit">Guardar cambios</button>
      <a class="btn btn-secundario" href="/pedidos.html">Ver mis pedidos</a>
    </form>`;
}

function inicialesDe(u) {
  return (
    (u.full_name || u.email)
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "U"
  );
}

function bindForms() {
  document.getElementById("form-perfil")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      user = await api.put("/users/me", {
        full_name: document.getElementById("perfil-nombre").value.trim(),
        email: document.getElementById("perfil-email").value.trim(),
      });
      localStorage.setItem("peluchi_user", JSON.stringify(user));
      toast("Perfil actualizado ✅", "exito");
      pintar("perfil");
    } catch (err) {
      document.getElementById("aviso-perfil").innerHTML =
        `<div class="aviso">${escapeHTML(err.detail || err.message)}</div>`;
    }
  });

  document.getElementById("form-password")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const actual = document.getElementById("pass-actual").value;
    const nueva = document.getElementById("pass-nueva").value;
    const nueva2 = document.getElementById("pass-nueva2").value;
    const aviso = document.getElementById("aviso-password");
    if (nueva !== nueva2) {
      aviso.innerHTML = '<div class="aviso">Las contraseñas no coinciden.</div>';
      return;
    }
    try {
      await api.put("/users/me/password", { current_password: actual, new_password: nueva });
      toast("Contraseña actualizada 🔒", "exito");
      pintar("password");
    } catch (err) {
      aviso.innerHTML = `<div class="aviso">${escapeHTML(err.detail || err.message)}</div>`;
    }
  });
}

(async () => {
  await initPage();
  if (!isLoggedIn()) {
    location.href = "/login.html?next=/cuenta.html";
    return;
  }
  try {
    [user, stats] = await Promise.all([api.fetchMe(), api.get("/users/me/stats")]);
    document.getElementById("sub-cuenta").textContent = `Hola, ${user.full_name || user.email}`;
    pintar("perfil");
  } catch (err) {
    cont.innerHTML = `<div class="vacio" style="grid-column:1/-1">
      <span class="vacio-emoji">⚠️</span><h3>Error al cargar la cuenta</h3>
      <p>${escapeHTML(err.detail || err.message)}</p></div>`;
  }
})();
