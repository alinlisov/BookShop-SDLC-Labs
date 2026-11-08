"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".register-form");
  if (!form) return;
  const message = form.querySelector(".form-message");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = form.querySelector("button[type=submit]");
    submit.disabled = true;
    try {
      const body = {
        full_name: document.querySelector("#reg-name").value.trim(),
        email: document.querySelector("#reg-email").value.trim(),
        phone: document.querySelector("#reg-phone").value.trim(),
        password: document.querySelector("#reg-pass").value,
        password_confirmation: document.querySelector("#reg-pass-confirm").value
      };
      await BookShopAPI.request("/api/auth/register", { method: "POST", body });
      alert("Реєстрація успішна! Тепер увійдіть у свій акаунт.");
      location.href = "login.html";
    } catch (error) {
      if (message) message.textContent = error.message;
      else alert(error.message);
    } finally {
      submit.disabled = false;
    }
  });
});
