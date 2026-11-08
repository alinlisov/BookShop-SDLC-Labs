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
