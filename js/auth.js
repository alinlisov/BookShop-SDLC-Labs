"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".login-form");
  if (!form) return;
  const message = form.querySelector(".form-message");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = form.querySelector("button[type=submit]");
    submit.disabled = true;
    try {
      const email = document.querySelector("#user-email").value.trim();
      const password = document.querySelector("#user-pass").value;
      const session = await BookShopAPI.request("/api/auth/login", { method: "POST", body: { email, password } });
      BookShopAPI.setToken(session.access_token);
      const profile = await BookShopAPI.request("/api/auth/me", { authenticated: true });
      location.href = profile.is_admin ? "admin.html" : "profile.html";
    } catch (error) {
      if (message) message.textContent = error.message;
      else alert(error.message);
    } finally {
      submit.disabled = false;
    }
  });
});
