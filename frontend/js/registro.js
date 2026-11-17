/* Peluchi — Registro de cuenta */

import { api, isLoggedIn, setTokens, setCachedUser } from "./api.js";
import { initPage, toast, escapeHTML } from "./ui.js";

const aviso = document.getElementById("aviso");

function mostrarError(msg) {
  aviso.innerHTML = `<div class="aviso">${escapeHTML(msg)}</div>`;
}

async function configurarBotonGitHub() {
  const btn = document.getElementById("btn-github");
  try {
    const providers = await api.get("/auth/providers", { auth: false });
    if (providers.github?.enabled) {
      btn.addEventListener("click", () => (location.href = providers.github.url));
    } else {
      btn.disabled = true;
      btn.title = "OAuth de GitHub no configurado (falta GITHUB_CLIENT_ID en .env)";
      btn.innerHTML = `<span style="font-size:1.2rem">🐙</span> GitHub (sin configurar)`;
    }
  } catch {
    btn.disabled = true;
  }
}

async function main() {
  await initPage();
  if (isLoggedIn()) {
    location.href = "/cuenta.html";
    return;
  }
  await configurarBotonGitHub();

  document.getElementById("registro-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    aviso.innerHTML = "";

    const nombre = document.getElementById("nombre").value.trim();
    const email = document.getElementById("email").value.trim();
    const pass = document.getElementById("password").value;
    const pass2 = document.getElementById("password2").value;

    if (!nombre) return mostrarError("Escribe tu nombre completo.");
    if (!email) return mostrarError("Escribe tu email.");
    if (pass.length < 6) return mostrarError("La contraseña debe tener al menos 6 caracteres.");
    if (pass !== pass2) return mostrarError("Las contraseñas no coinciden.");

    const btn = document.getElementById("btn-crear");
    btn.disabled = true;
    btn.textContent = "Creando cuenta...";

    try {
      const data = await api.post("/auth/register", {
        email, password: pass, full_name: nombre,
      }, { auth: false });
      api.saveSession(data);
      toast("¡Cuenta creada! 🎉", "exito");
      setTimeout(() => (location.href = "/"), 700);
    } catch (err) {
      mostrarError(err.detail || err.message);
      btn.disabled = false;
      btn.textContent = "Crear cuenta";
    }
  });
}

main();
