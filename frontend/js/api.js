/* ==========================================================================
   Peluchi — Cliente API
   Gestión de tokens JWT (con auto-refresh) y peticiones a la API REST
   ========================================================================== */

const API = "/api";
const KEY_ACCESS = "peluchi_access";
const KEY_REFRESH = "peluchi_refresh";
const KEY_USER = "peluchi_user";

export function getToken() {
  return localStorage.getItem(KEY_ACCESS);
}

export function getRefreshToken() {
  return localStorage.getItem(KEY_REFRESH);
}

export function setTokens(accessToken, refreshToken) {
  localStorage.setItem(KEY_ACCESS, accessToken);
  if (refreshToken) localStorage.setItem(KEY_REFRESH, refreshToken);
}

export function clearTokens() {
  localStorage.removeItem(KEY_ACCESS);
  localStorage.removeItem(KEY_REFRESH);
  localStorage.removeItem(KEY_USER);
  localStorage.removeItem("peluchi_cart_count");
}

export function getCachedUser() {
  try {
    return JSON.parse(localStorage.getItem(KEY_USER) || "null");
  } catch {
    return null;
  }
}

export function setCachedUser(user) {
  localStorage.setItem(KEY_USER, JSON.stringify(user));
}

export function isLoggedIn() {
  return !!getToken();
}

/** Cierra la sesión limpiando tokens. */
export function logout() {
  clearTokens();
}

/* --------------------------------------------------------------------------
   Refresco de token
   -------------------------------------------------------------------------- */
let refreshPromise = null;

async function tryRefresh() {
  const rt = getRefreshToken();
  if (!rt) return false;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        setCachedUser(data.user);
        return true;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

/* --------------------------------------------------------------------------
   Peticiones
   -------------------------------------------------------------------------- */
class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function parseBody(res) {
  if (res.status === 204) return null;
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * Realiza una petición a la API.
 * @param {string} path - Ruta relativa (ej: "/products?page=1")
 * @param {object} opts - { method, body, form, auth, retry }
 */
async function request(path, opts = {}) {
  const { method = "GET", body, form, auth = true, retry = true } = opts;

  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (form) headers["Content-Type"] = "application/x-www-form-urlencoded";
  else if (body !== undefined) headers["Content-Type"] = "application/json";

  let payload;
  if (form) payload = body;
  else if (body !== undefined) payload = JSON.stringify(body);

  let res;
  try {
    res = await fetch(API + path, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor");
  }

  // Token caducado → intentar refresco y reintentar una vez
  if (res.status === 401 && auth && token && retry && !path.startsWith("/auth/")) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request(path, { ...opts, retry: false });
    }
    clearTokens();
  }

  const data = await parseBody(res);
  if (!res.ok) {
    let detail = data?.detail ?? data ?? "Error inesperado";
    if (Array.isArray(detail)) {
      detail = detail.map((d) => d.msg || JSON.stringify(d)).join(". ");
    }
    throw new ApiError(res.status, detail);
  }
  return data;
}

export const api = {
  get: (path, opts = {}) => request(path, { ...opts, method: "GET" }),
  post: (path, body, opts = {}) => request(path, { ...opts, method: "POST", body }),
  put: (path, body, opts = {}) => request(path, { ...opts, method: "PUT", body }),
  patch: (path, body, opts = {}) => request(path, { ...opts, method: "PATCH", body }),
  del: (path, opts = {}) => request(path, { ...opts, method: "DELETE" }),

  /** Login con email/contraseña (formato OAuth2 de FastAPI). */
  login(email, password) {
    return request("/auth/login", {
      method: "POST",
      form: true,
      auth: false,
      body: new URLSearchParams({ username: email, password }),
    });
  },

  /** Guarda la respuesta de login/registro en localStorage. */
  saveSession(data) {
    setTokens(data.access_token, data.refresh_token);
    setCachedUser(data.user);
    return data.user;
  },

  /** Recarga los datos del usuario actual desde el servidor. */
  async fetchMe() {
    const user = await request("/auth/me");
    setCachedUser(user);
    return user;
  },
};

export { ApiError };
