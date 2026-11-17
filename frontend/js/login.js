/* Peluchi — Login (email/contraseña + OAuth de GitHub) */

import { api, isLoggedIn, setTokens, setCachedUser } from "./api.js";
import { initPage, toast, escapeHTML } from "./ui.js";

const aviso = document.getElementById("aviso");

function mostrarError(msg) {
  aviso.innerHTML = `<div class="aviso">${escapeHTML(msg)}</div>`;
}

function destinoPostLogin() {
  const next = new URLSearchParams(location.search).get("next");
  if (next && next.startsWith("/")) return next;
  const user = JSON.parse(localStorage.getItem("peluchi_user") || "{}");
  return user.role === "admin" ? "/admin.html" : "/";
}

/** Callback de GitHub: los tokens llegan en el fragmento #access_token=... */
async function procesarHashOAuth() {
  if (!location.hash.includes("access_token")) return false;
  const params = new URLSearchParams(location.hash.slice(1));
  const access = params.get("access_token");
  const refresh = params.get("refresh_token");
  if (!access) return false;

  setTokens(access, refresh);
  try {
    const user = await api.fetchMe();
    setCachedUser(user);
    history.replaceState(null, "", location.pathname);
    toast(`¡Hola, ${user.full_name || user.email}! 🐙`, "exito");
    setTimeout(() => (location.href = destinoPostLogin()), 700);
    return true;
  } catch {
    toast("No se pudo completar el login con GitHub", "error");
    return false;
  }
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

  const yaDentro = isLoggedIn();
  const procesandoOAuth = await procesarHashOAuth();
  if (yaDentro && !procesandoOAuth && !location.hash.includes("access_token")) {
    location.href = destinoPostLogin();
    return;
  }

  await configurarBotonGitHub();

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    aviso.innerHTML = "";
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const btn = document.getElementById("btn-entrar");
    btn.disabled = true;
    btn.textContent = "Entrando...";

    try {
      const data = await api.login(email, password);
      api.saveSession(data);
      toast(`¡Bienvenido/a, ${data.user.full_name || data.user.email}! 🎉`, "exito");
      setTimeout(() => (location.href = destinoPostLogin()), 600);
    } catch (err) {
      mostrarError(err.detail || err.message);
      btn.disabled = false;
      btn.textContent = "Entrar";
    }
  });
}

main();
