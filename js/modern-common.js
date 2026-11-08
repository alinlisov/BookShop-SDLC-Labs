"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector("#primary-navigation");
  toggle?.addEventListener("click", () => {
    const open = nav?.classList.toggle("is-open") ?? false;
    toggle.setAttribute("aria-expanded", String(open));
  });
  nav?.querySelectorAll("a").forEach(a => a.addEventListener("click", () => {
    nav.classList.remove("is-open");
    toggle?.setAttribute("aria-expanded", "false");
  }));

  const api = window.BookShopAPI;
  if (!api || !api.token()) return;
  const guest = document.querySelector(".guest-actions");
  if (!guest) return;
  guest.replaceChildren();
  const profile = document.createElement("a");
  profile.className = "login-btn";
  profile.href = "profile.html";
  profile.textContent = "Мій профіль";
  const logout = document.createElement("button");
  logout.type = "button";
  logout.className = "register-btn";
  logout.textContent = "Вийти";
  logout.addEventListener("click", () => api.logout());
  guest.append(profile, logout);
  api.request("/api/auth/me", { authenticated: true }).then(me => {
    if (me.is_admin) profile.href = "admin.html";
  }).catch(() => {
    guest.replaceChildren();
    const link = document.createElement("a"); link.href = "login.html";
    link.className = "login-btn"; link.textContent = "Увійти";
    const signup = document.createElement("a"); signup.href = "register.html";
    signup.className = "register-btn"; signup.textContent = "Реєстрація";
    guest.append(link, signup);
  });
});
