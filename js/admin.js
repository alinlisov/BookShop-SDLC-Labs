"use strict";
document.addEventListener("DOMContentLoaded", async () => {
  const api = BookShopAPI;
  if (!api.token()) { location.replace("login.html"); return; }
  document.querySelectorAll(".logout-btn").forEach(link => link.addEventListener("click", event => {
    event.preventDefault(); api.logout();
  }));
  const messageBox = document.querySelector("#admin-notice");
  const bookBody = document.querySelector("#books-table-body");
  const orderBody = document.querySelector("#admin-orders-body");
  const form = document.querySelector("#add-book-form");
  let books = [];
  let orders = [];
  const setMessage = text => { if (messageBox) messageBox.textContent = text; };

  try { await api.request("/api/auth/admin-check", { authenticated: true }); }
  catch (error) { alert("Доступ до панелі дозволений тільки адміністратору. " + error.message); location.replace("profile.html"); return; }

  const td = (tr, value) => { const cell = document.createElement("td"); cell.textContent = String(value); tr.append(cell); return cell; };
  function resetForm() {
    form.reset(); document.querySelector("#book-id").value = "";
    document.querySelector("#submit-btn").textContent = "Додати";
    document.querySelector("#cancel-btn").style.display = "none";
  }
  document.querySelector("#cancel-btn")?.addEventListener("click", resetForm);

  function startEdit(book) {
    document.querySelector("#book-id").value = book.id;
    document.querySelector("#book-title").value = book.title;
    document.querySelector("#book-author").value = book.author;
    document.querySelector("#book-price").value = book.price;
    document.querySelector("#book-genre").value = book.genre;
    document.querySelector("#book-available").checked = book.is_available;
    document.querySelector("#submit-btn").textContent = "Зберегти";
    document.querySelector("#cancel-btn").style.display = "inline-block";
    form.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  async function deleteBook(id) {
    if (!confirm(`Видалити книжку №${id}? Якщо є замовлення/відгуки, сервер заборонить видалення.`)) return;
    try { await api.request(`/api/admin/books/${id}`, { method: "DELETE", authenticated: true }); await loadBooks(); }
    catch (err) { setMessage(err.message); }
  }
  function renderBooks() {
    bookBody.replaceChildren();
    for (const book of books) {
      const tr = document.createElement("tr");
      td(tr, book.id); td(tr, book.title); td(tr, book.author); td(tr, `${book.price} грн`);
      const actions = td(tr, "");
      const edit = document.createElement("button"); edit.type = "button"; edit.textContent = "️ Змінити";
      edit.addEventListener("click", () => startEdit(book));
      const del = document.createElement("button"); del.type = "button"; del.textContent = " Видалити";
      del.addEventListener("click", () => deleteBook(book.id));
      actions.append(edit, del); bookBody.append(tr);
    }
    const booksMetric = document.querySelector(".stat-card:nth-child(2) p");
    if (booksMetric) booksMetric.textContent = books.length;
  }
  async function loadBooks() {
    books = await api.request("/api/books"); renderBooks();
  }
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const id = document.querySelector("#book-id").value;
    const payload = {
      title: document.querySelector("#book-title").value.trim(),
      author: document.querySelector("#book-author").value.trim(),
      genre: document.querySelector("#book-genre").value.trim(),
      price: document.querySelector("#book-price").value,
      is_available: document.querySelector("#book-available").checked
    };
    try {
      await api.request(id ? `/api/admin/books/${id}` : "/api/admin/books", {
        method: id ? "PATCH" : "POST", authenticated: true, body: payload
      });
      resetForm(); await loadBooks(); setMessage(id ? "Книжку оновлено" : "Книжку додано");
    } catch (error) { setMessage(error.message); }
  });

  function renderOrders() {
    orderBody.replaceChildren();
    for (const order of orders) {
      const tr = document.createElement("tr");
      td(tr, `#${order.id}`); td(tr, order.customer_name); td(tr, `${order.total_amount} грн`);
      td(tr, order.status);
      const action = td(tr, "");
      const select = document.createElement("select");
      for (const state of ["processing", "approved", "rejected", "cancelled"]) select.add(new Option(state, state));
      const button = document.createElement("button"); button.type = "button"; button.textContent = "Змінити статус";
      const finished = ["approved", "rejected", "cancelled"].includes(order.status);
      select.disabled = finished; button.disabled = finished;
      button.addEventListener("click", async () => {
        try {
          await api.request(`/api/admin/orders/${order.id}/status`, {
            method: "PATCH", authenticated: true, body: { status: select.value }
          });
          await loadOrders(); setMessage(`Статус замовлення #${order.id} оновлено`);
        } catch (error) { setMessage(error.message); }
      });
      action.append(select, button); orderBody.append(tr);
    }
    const newCount = document.querySelector(".stat-card:first-child p");
    if (newCount) newCount.textContent = orders.filter(o => o.status === "new").length;
  }
  async function loadOrders() { orders = await api.request("/api/admin/orders", { authenticated: true }); renderOrders(); }

  const usersMetric = document.querySelector(".stat-card:nth-child(3) p");
  if (usersMetric) usersMetric.textContent = "—"; // No users-count API exists in stage 3.
  try { await Promise.all([loadBooks(), loadOrders()]); }
  catch (error) { setMessage(error.message); }
});
