"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const api = BookShopAPI;
  const container = document.querySelector("#books-container");
  const bookSelect = document.querySelector("#book");
  const reviewBook = document.querySelector("#review-book");
  const orderForm = document.querySelector("#order-form");
  const commentForm = document.querySelector("#comment-form");
  const reviews = document.querySelector("#comment-list");
  const search = document.querySelector(".search-input");
  let books = [];

  function message(text, target = container) {
    if (!target) return;
    const p = document.createElement("p");
    p.className = "bookshop-notice";
    p.textContent = text;
    target.replaceChildren(p);
  }

  function coverPath(path) {
    if (!path) return null;
    const relative = String(path).replace(/^\/+/, "");
    if (!relative.startsWith("covers/") || relative.includes("..") || !/^covers\/[\w\-/\.а-яА-ЯіїєґІЇЄҐ ]+$/u.test(relative)) return null;
    return `/${relative}`;
  }

  function selectForOrder(id) {
    bookSelect.value = String(id);
    orderForm.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function drawBooks(filter = "") {
    container.replaceChildren();
    const needle = filter.toLocaleLowerCase("uk").trim();
    const visible = books.filter(book => `${book.title} ${book.author}`.toLocaleLowerCase("uk").includes(needle));
    if (!visible.length) { message("За вашим запитом книжок не знайдено."); return; }
    for (const book of visible) {
      const card = document.createElement("section"); card.className = "book-card";
      const cover = coverPath(book.cover);
      if (cover) {
        const img = document.createElement("img"); img.src = cover; img.alt = `Обкладинка: ${book.title}`;
        img.addEventListener("error", () => { img.replaceWith(makePlaceholder()); });
        card.append(img);
      } else card.append(makePlaceholder());
      const info = document.createElement("section"); info.className = "book-info";
      const h3 = document.createElement("h3"); h3.textContent = book.title;
      const author = document.createElement("p"); author.textContent = book.author;
      const price = document.createElement("p"); price.className = "book-price"; price.textContent = `${book.price} грн`;
      info.append(h3, author, price); card.append(info);
      const button = document.createElement("button"); button.className = "order-btn";
      button.textContent = book.is_available ? "Замовити" : "Немає в наявності";
      button.disabled = !book.is_available;
      button.addEventListener("click", () => selectForOrder(book.id));
      card.append(button); container.append(card);
    }
  }

  function makePlaceholder() {
    const d = document.createElement("div"); d.className = "book-cover-placeholder";
    d.textContent = "📚"; d.setAttribute("aria-label", "Обкладинка відсутня"); return d;
  }

  function fillSelect(select, items, emptyText = null) {
    select.replaceChildren();
    if (emptyText) { const opt = new Option(emptyText, ""); select.add(opt); }
    for (const book of items) select.add(new Option(`${book.title} — ${book.price} грн`, String(book.id)));
  }

  async function loadReviews() {
    if (!reviews || !reviewBook) return;
    const id = reviewBook.value;
    if (!id) { message("Оберіть книжку, щоб переглянути відгуки.", reviews); return; }
    try {
      const list = await api.request(`/api/books/${encodeURIComponent(id)}/reviews`);
      reviews.replaceChildren();
      if (!list.length) { message("До цієї книжки ще немає відгуків.", reviews); return; }
      for (const entry of list) {
        const article = document.createElement("article"); article.className = "review-entry";
        const author = document.createElement("h3"); author.textContent = entry.author_name;
        const body = document.createElement("p"); body.textContent = entry.comment_text;
        const date = document.createElement("small"); date.textContent = new Date(entry.created_at).toLocaleDateString("uk-UA");
        article.append(author, body, date); reviews.append(article);
      }
    } catch (error) { message(error.message, reviews); }
  }

  async function loadBooks() {
    try {
      books = await api.request("/api/books");
      drawBooks(search?.value ?? "");
      const available = books.filter(b => b.is_available);
      fillSelect(bookSelect, available, "-- Оберіть книжку --");
      fillSelect(reviewBook, books, "-- Оберіть книжку для відгуків --");
      if (books.length) {
        reviewBook.value = String(books[0].id);
        await loadReviews();
      }
    } catch (error) { message(error.message); }
  }

  search?.addEventListener("input", () => drawBooks(search.value));
  document.querySelector(".search-btn")?.addEventListener("click", () => drawBooks(search?.value || ""));
  document.querySelector(".cart-btn")?.addEventListener("click", () => orderForm.scrollIntoView({ behavior: "smooth" }));
  document.querySelectorAll(".genre-header").forEach(button => button.addEventListener("click", () => button.closest(".genre-card")?.classList.toggle("active")));
  reviewBook?.addEventListener("change", loadReviews);

  window.toggleReviewForm = () => {
    const wrapper = document.querySelector("#reviewFormWrapper");
    if (wrapper) wrapper.style.display = wrapper.style.display === "none" ? "block" : "none";
  };

  const commentName = document.querySelector("#comment-name");
  if (commentName) { commentName.required = false; commentName.closest("label")?.remove(); commentName.hidden = true; }
  commentForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!api.token()) { alert("Щоб залишити відгук, спочатку увійдіть у свій акаунт."); location.href = "login.html"; return; }
    const selected = reviewBook.value;
    if (!selected) { alert("Оберіть книжку"); return; }
    try {
      await api.request(`/api/books/${encodeURIComponent(selected)}/reviews`, {
        method: "POST", authenticated: true,
        body: { comment_text: document.querySelector("#comment-text").value.trim() }
      });
      document.querySelector("#comment-text").value = "";
      await loadReviews();
      alert("Відгук збережено в PostgreSQL.");
    } catch (error) { alert(error.message); }
  });

  orderForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = orderForm.querySelector("button[type=submit]");
    submit.disabled = true;
    try {
      const id = Number(bookSelect.value);
      if (!id) throw new Error("Оберіть книжку");
      const region = document.querySelector("#region").value.trim();
      const city = document.querySelector("#address").value.trim();
      const order = await api.request("/api/orders", {
        method: "POST", authenticated: Boolean(api.token()),
        body: {
          full_name: document.querySelector("#name").value.trim(),
          email: document.querySelector("#email").value.trim(),
          phone: document.querySelector("#phone").value.trim(),
          address: `${region}, ${city}`,
          items: [{ book_id: id, quantity: Number(document.querySelector("#qty").value) }]
        }
      });
      alert(`Замовлення №${order.id} створено. Сума: ${order.total_amount} грн.`);
      document.querySelector("#qty").value = "1";
    } catch (error) { alert(error.message); }
    finally { submit.disabled = false; }
  });

  if (api.token()) {
    const guest = document.querySelector(".guest-actions");
    if (guest) { const link = document.createElement("a"); link.href = "profile.html"; link.className = "login-btn"; link.textContent = "Мій профіль"; guest.append(link); }
  }
  async function fillUserData() {
    if (!api.token()) return;
    try {
      const me = await api.request("/api/auth/me", { authenticated: true });
      document.querySelector("#name").value = me.full_name;
      document.querySelector("#email").value = me.email;
      document.querySelector("#phone").value = me.phone || "";
    } catch (error) { console.info("Немає чинної сесії:", error.message); }
  }
  loadBooks(); fillUserData();
});
