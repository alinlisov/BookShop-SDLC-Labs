"use strict";

(() => {
  // After deploying FastAPI on Render, replace the placeholder with YOUR https URL.
  const CLOUD_API_ORIGIN = "https://REPLACE_WITH_YOUR_RENDER_SERVICE.onrender.com";
  const onGithubPages = location.hostname === "alinlisov.github.io";
  const TOKEN_KEY = "bookshop_access_token";
  const token = () => sessionStorage.getItem(TOKEN_KEY);
  const setToken = (value) => sessionStorage.setItem(TOKEN_KEY, value);
  const clearToken = () => sessionStorage.removeItem(TOKEN_KEY);

  async function request(path, { method = "GET", body, authenticated = false } = {}) {
    if (!path.startsWith("/api/")) throw new Error("Некоректний шлях API");
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (authenticated && token()) headers.Authorization = `Bearer ${token()}`;
    if (onGithubPages && CLOUD_API_ORIGIN.includes("REPLACE_WITH_YOUR_RENDER_SERVICE")) {
      throw new Error("У js/api.js потрібно вказати HTTPS-адресу свого API на Render");
    }
    const apiUrl = onGithubPages ? `${CLOUD_API_ORIGIN}${path}` : path;
    const controller = new AbortController();
    // Free Render services may take longer to wake up after idling.
    const timeout = setTimeout(() => controller.abort(), onGithubPages ? 90000 : 15000);
    let response;
    try {
      response = await fetch(apiUrl, {
        method, headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
        cache: "no-store"
      });
    } catch (error) {
      if (error.name === "AbortError") throw new Error("Сервер не відповів за відведений час");
      throw new Error("Не вдалося зв'язатися із сервером. Перевір запуск FastAPI.");
    } finally {
      clearTimeout(timeout);
    }
    const data = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401 && authenticated) clearToken();
      let detail = data?.detail ?? "Помилка запиту";
      if (Array.isArray(detail)) detail = detail.map(item => item.msg).join("; ");
      throw new Error(`${response.status}: ${detail}`);
    }
    return data;
  }

  async function logout() {
    if (token()) {
      try { await request("/api/auth/logout", { method: "POST", authenticated: true }); }
      catch (err) { console.warn("Неможливо завершити сесію на сервері:", err.message); }
    }
    clearToken();
    location.href = "login.html";
  }

  window.BookShopAPI = Object.freeze({ request, token, setToken, clearToken, logout });
})();
