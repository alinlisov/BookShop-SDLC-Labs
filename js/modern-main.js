"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const api = window.BookShopAPI;
  if (!api) return;
  const $ = sel => document.querySelector(sel);
  const grid = $("#books-container");
  const bookSelect = $("#book");
  const reviewSelect = $("#review-book");
  const genreSelect = $("#genre-filter");
  const sortSelect = $("#sort-select");
  const search = $(".search-input");
  const orderForm = $("#order-form");
  const commentForm = $("#comment-form");
  const reviewList = $("#comment-list");
  const money = new Intl.NumberFormat("uk-UA", { maximumFractionDigits: 2, minimumFractionDigits: 0 });
  let books = [];

  function setStatus(selector, text, kind = "") {
    const node = $(selector);
    if (!node) return;
    node.textContent = text;
    node.className = `form-status ${kind}`;
  }
  function humanPrice(value) { return `${money.format(Number(value) || 0)} грн`; }
  function safeCover(url) {
    if (!url) return null;
    const path = String(url).replace(/^\/+/, "");
    if (!path.startsWith("covers/") || path.includes("..") || !/^covers\/[\p{L}\p{N}_\-./ ]+$/u.test(path)) return null;
    return "/" + path;
  }
  function placeholder(book) {
    const div = document.createElement("div");
    div.className = "book-cover-placeholder";
    div.textContent = book.title;
    div.setAttribute("role", "img");
    div.setAttribute("aria-label", `Обкладинка книги «${book.title}» відсутня`);
    return div;
  }
  function cover(book) {
    const wrap = document.createElement("div");
    wrap.className = "book-cover";
    const path = safeCover(book.cover);
    if (path) {
      const image = document.createElement("img");
      image.src = path;
      image.loading = "lazy";
      image.alt = `Обкладинка книги «${book.title}»`;
      image.addEventListener("error", () => image.replaceWith(placeholder(book)), { once: true });
      wrap.append(image);
    } else wrap.append(placeholder(book));
    const badge = document.createElement("span");
    badge.className = `book-badge${book.is_available ? "" : " out"}`;
    badge.textContent = book.is_available ? "У наявності" : "Немає в наявності";
    wrap.append(badge);
    return wrap;
  }
  function filterBooks() {
    const term = (search?.value ?? "").toLocaleLowerCase("uk").trim();
    const genre = genreSelect?.value ?? "";
    let chosen = books.filter(b =>
      (!genre || b.genre === genre) &&
      (!term || `${b.title} ${b.author} ${b.genre}`.toLocaleLowerCase("uk").includes(term)));
    switch (sortSelect?.value) {
      case "price-low": chosen.sort((a, b) => Number(a.price) - Number(b.price)); break;
      case "price-high": chosen.sort((a, b) => Number(b.price) - Number(a.price)); break;
      case "title": chosen.sort((a, b) => a.title.localeCompare(b.title, "uk")); break;
    }
    return chosen;
  }
  function selectOrder(bookId) {
    if (!bookSelect) return;
    bookSelect.value = String(bookId);
    updateTotal();
    $("#order")?.scrollIntoView({ behavior: "smooth", block: "start" });
    setStatus("#order-status", "Книжку вибрано. Заповніть дані та підтвердьте замовлення.");
  }
  function renderBooks() {
    if (!grid) return;
    grid.replaceChildren();
    const visible = filterBooks();
    const count = $("#book-count");
    if (count) count.textContent = `Знайдено книжок: ${visible.length}`;
    if (!visible.length) {
      const msg = document.createElement("p"); msg.className = "empty-state";
      msg.textContent = "За цими параметрами книжок не знайдено. Спробуйте інший запит або жанр.";
      grid.append(msg); return;
    }
    for (const b of visible) {
      const item = document.createElement("article"); item.className = "book-card";
      const info = document.createElement("div"); info.className = "book-info";
      const genre = document.createElement("span"); genre.className = "book-genre"; genre.textContent = b.genre;
      const title = document.createElement("h3"); title.textContent = b.title;
      const author = document.createElement("p"); author.className = "book-author"; author.textContent = b.author;
      const price = document.createElement("p"); price.className = "book-price"; price.textContent = humanPrice(b.price);
      info.append(genre, title, author, price);
      const action = document.createElement("button"); action.type = "button";
      action.className = "order-btn";
      action.textContent = b.is_available ? "Обрати книгу →" : "Немає в наявності";
      action.disabled = !b.is_available;
      action.addEventListener("click", () => selectOrder(b.id));
      item.append(cover(b), info, action); grid.append(item);
    }
  }
  function fillBookSelect(select, arr, label) {
    if (!select) return;
    select.replaceChildren(new Option(label, ""));
    for (const b of arr) select.add(new Option(`${b.title} — ${humanPrice(b.price)}`, String(b.id)));
  }
  function updateTotal() {
    const current = books.find(b => String(b.id) === bookSelect?.value);
    const qty = Math.min(20, Math.max(0, Number($("#qty")?.value || 0)));
    const total = $("#order-total");
    if (total) total.textContent = humanPrice(current ? Number(current.price) * qty : 0);
  }
  async function loadBooks() {
    try {
      const result = await api.request("/api/books");
      books = Array.isArray(result) ? result : [];
      if (genreSelect) {
        const genres = [...new Set(books.map(b => b.genre).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"uk"));
        genreSelect.replaceChildren(new Option("Усі жанри", ""));
        genres.forEach(genre => genreSelect.add(new Option(genre, genre)));
      }
      fillBookSelect(bookSelect, books.filter(b => b.is_available), "— Оберіть книжку —");
      fillBookSelect(reviewSelect, books, "— Оберіть книжку —");
      renderBooks(); updateTotal();
      if (books.length && reviewSelect) {
        reviewSelect.value = String(books[0].id);
        await loadReviews();
      }
    } catch (error) {
      if (grid) { grid.replaceChildren(); const p = document.createElement("p"); p.className = "empty-state"; p.textContent = error.message; grid.append(p); }
      const count = $("#book-count"); if (count) count.textContent = "Помилка завантаження";
    }
  }
  async function loadReviews() {
    if (!reviewList || !reviewSelect) return;
    reviewList.replaceChildren();
    if (!reviewSelect.value) { reviewList.textContent = "Оберіть книжку для перегляду відгуків."; return; }
    try {
      const list = await api.request(`/api/books/${encodeURIComponent(reviewSelect.value)}/reviews`);
      if (!list.length) { reviewList.textContent = "Для цієї книги ще немає відгуків. Будьте першими!"; return; }
      for (const entry of list) {
        const article = document.createElement("article"); article.className = "review-entry";
        const author = document.createElement("h3"); author.textContent = entry.author_name;
        const text = document.createElement("p"); text.textContent = entry.comment_text;
        const date = document.createElement("small"); date.textContent = new Date(entry.created_at).toLocaleDateString("uk-UA");
        article.append(author, text, date); reviewList.append(article);
      }
    } catch (error) { reviewList.textContent = error.message; }
  }
  search?.addEventListener("input", renderBooks);
  $(".search-btn")?.addEventListener("click", renderBooks);
  genreSelect?.addEventListener("change", renderBooks);
  sortSelect?.addEventListener("change", renderBooks);
  bookSelect?.addEventListener("change", updateTotal);
  $("#qty")?.addEventListener("input", updateTotal);
  reviewSelect?.addEventListener("change", loadReviews);
  $(".cart-btn")?.addEventListener("click", () => $("#order")?.scrollIntoView({ behavior: "smooth" }));

  document.querySelectorAll(".genre-header").forEach(button => button.addEventListener("click", () => {
    const details = button.parentElement.querySelector(".genre-details");
    const expanded = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!expanded));
    button.parentElement.classList.toggle("active", !expanded);
    if (details) details.hidden = expanded;
  }));
  const reviewToggle = $("#review-toggle");
  reviewToggle?.addEventListener("click", () => {
    const form = $("#reviewFormWrapper"); if (!form) return;
    const open = form.hidden;
    form.hidden = !open;
    reviewToggle.setAttribute("aria-expanded", String(open));
    if (open) $("#comment-text")?.focus();
  });

  orderForm?.addEventListener("submit", async event => {
    event.preventDefault();
    if (!orderForm.reportValidity()) return;
    const submit = orderForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    setStatus("#order-status", "Зберігаємо замовлення...");
    try {
      const id = Number(bookSelect.value);
      if (!id) throw new Error("Оберіть книжку");
      const region = $("#region").value.trim();
      const address = $("#address").value.trim();
      const result = await api.request("/api/orders", {
        method: "POST", authenticated: Boolean(api.token()),
        body: { full_name: $("#name").value.trim(), email: $("#email").value.trim(),
          phone: $("#phone").value.trim(), address: `${region}, ${address}`,
          items: [{ book_id: id, quantity: Number($("#qty").value) }] }
      });
      orderForm.reset(); updateTotal();
      setStatus("#order-status", `Замовлення №${result.id} відправлено! Сума: ${humanPrice(result.total_amount)}.`, "ok");
    } catch (error) { setStatus("#order-status", error.message, "error"); }
    finally { submit.disabled = false; }
  });

  commentForm?.addEventListener("submit", async event => {
    event.preventDefault();
    if (!api.token()) {
      setStatus("#review-status", "Спочатку увійдіть у свій акаунт, щоб залишити відгук.", "error");
      return;
    }
    if (!commentForm.reportValidity()) return;
    const id = reviewSelect?.value;
    if (!id) { setStatus("#review-status", "Оберіть книжку для відгуку.", "error"); return; }
    const submit = commentForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    try {
      await api.request(`/api/books/${encodeURIComponent(id)}/reviews`, {
        method: "POST", authenticated: true, body: { comment_text: $("#comment-text").value.trim() }
      });
      commentForm.reset();
      setStatus("#review-status", "Ваш відгук опубліковано!", "ok");
      await loadReviews();
    } catch (error) { setStatus("#review-status", error.message, "error"); }
    finally { submit.disabled = false; }
  });

  async function prefillCustomer() {
    if (!api.token()) return;
    try {
      const user = await api.request("/api/auth/me", { authenticated: true });
      $("#name").value = user.full_name || "";
      $("#email").value = user.email || "";
      $("#phone").value = user.phone || "";
    } catch (error) { console.info("Сесія недоступна:", error.message); }
  }
  loadBooks(); prefillCustomer();
});
