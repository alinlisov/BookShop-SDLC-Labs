"use strict";
document.addEventListener("DOMContentLoaded", async () => {
  if (!BookShopAPI.token()) { location.replace("login.html"); return; }
  document.querySelectorAll(".logout-btn").forEach(el => el.addEventListener("click", (e) => {
    e.preventDefault(); BookShopAPI.logout();
  }));
  const tbody = document.getElementById("orders-table-body");
  try {
    const [user, orders, books] = await Promise.all([
      BookShopAPI.request("/api/auth/me", { authenticated: true }),
      BookShopAPI.request("/api/orders/mine", { authenticated: true }),
      BookShopAPI.request("/api/books")
    ]);
    const welcome = document.querySelector(".welcome-user");
    if (welcome) welcome.textContent = `Вітаємо, ${user.full_name}!`;
    const emailBox = document.querySelector(".profile-info p");
    if (emailBox) emailBox.textContent = user.email;

    // FR-4.3: show and securely edit the signed-in customer's saved address.
    const addressInfo = document.getElementById("saved-address");
    const regionInput = document.getElementById("profile-region");
    const streetInput = document.getElementById("profile-street");
    const addressStatus = document.getElementById("profile-address-status");
    const form = document.getElementById("profile-address-form");
    function showAddress(address) {
      if (addressInfo) addressInfo.textContent = address || "Адресу ще не збережено";
    }
    showAddress(user.address);
    if (regionInput && streetInput && user.address) {
      const options = Array.from(regionInput.options).filter(option => option.value)
        .sort((a, b) => b.value.length - a.value.length);
      const region = options.find(option => user.address.startsWith(option.value + ", "));
      if (region) {
        regionInput.value = region.value;
        streetInput.value = user.address.slice(region.value.length + 2);
      } else {
        // Legacy address: show it intact; require user to choose a region before saving.
        streetInput.value = user.address;
      }
    }
    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const submit = form.querySelector('button[type="submit"]');
      if (submit) submit.disabled = true;
      if (addressStatus) addressStatus.textContent = "Зберігаємо адресу...";
      try {
        const address = `${regionInput.value}, ${streetInput.value.trim()}`;
        const updated = await BookShopAPI.request("/api/auth/me/address", {
          method: "PATCH", authenticated: true, body: { address }
        });
        showAddress(updated.address);
        if (addressStatus) addressStatus.textContent = "Адресу успішно збережено.";
      } catch (error) {
        if (addressStatus) addressStatus.textContent = `Не вдалося зберегти адресу: ${error.message}`;
      } finally {
        if (submit) submit.disabled = false;
      }
    });
    const names = new Map(books.map(b => [b.id, b.title]));
    tbody.replaceChildren();
    if (!orders.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td"); td.colSpan = 5; td.textContent = "Замовлень поки немає";
      tr.append(td); tbody.append(tr);
    }
    for (const order of orders) {
      const tr = document.createElement("tr");
      const titles = order.items.map(item => `${names.get(item.book_id) ?? `Книжка #${item.book_id}`} × ${item.quantity}`).join(", ");
      const values = [`#${order.id}`, titles, `${order.total_amount} грн`, order.status,
        new Date(order.created_at).toLocaleDateString("uk-UA")];
      for (const value of values) { const td = document.createElement("td"); td.textContent = value; tr.append(td); }
      tbody.append(tr);
    }
  } catch (error) {
    if (!BookShopAPI.token()) { location.replace("login.html"); return; }
    if (tbody) { tbody.replaceChildren(); const tr = tbody.insertRow(); const td = tr.insertCell(); td.colSpan = 5; td.textContent = error.message; }
  }
});
