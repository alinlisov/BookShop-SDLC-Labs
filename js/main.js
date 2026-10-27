document.addEventListener("DOMContentLoaded", () => {
  
  // Автоматичне підставлення книги у форму
  
  document.querySelectorAll('.order-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const bookName = btn.getAttribute('data-book');
        const bookSelect = document.getElementById('book');

        for (let option of bookSelect.options) {
          if (option.text.includes(bookName)) {
            bookSelect.value = option.value;
            break;
          }
        }
        document.querySelector('form').scrollIntoView({behavior: 'smooth'});
      });
    });

  
  // Створення коментарів
  
  const form = document.getElementById("comment-form");
  const commentList = document.getElementById("comment-list");

  form.addEventListener("submit", function(event) {
    event.preventDefault();

    const name = document.getElementById("comment-name").value.trim();
    const text = document.getElementById("comment-text").value.trim();
    const date = new Date().toLocaleDateString("uk-UA");

    if (name && text) {
      const newComment = document.createElement("article");
      newComment.classList.add("comment");

      newComment.innerHTML = `
        <h3>${name}</h3>
        <p>${text}</p>
        <small>${date}</small>
      `;

      commentList.prepend(newComment);
      form.reset(); // очищає форму
    }
  });

  
  // Пошук книг
  
  // Отримуємо елементи
  const searchInput = document.querySelector('.search-input');
  const searchBtn = document.querySelector('.search-btn');
  const bookCards = document.querySelectorAll('.book-card');

  // Функція для фільтрації
  function searchBooks() {
    const searchTerm = searchInput.value.toLowerCase().trim();
    bookCards.forEach(card => {
      const bookTitle = card.querySelector('h3').textContent.toLowerCase();
      if (bookTitle.includes(searchTerm)) {
        card.style.display = 'block'; // показуємо
      } else {
        card.style.display = 'none'; // ховаємо
      }
    });
  }

  searchBtn.addEventListener('click', searchBooks);
  
  searchInput.addEventListener('input', searchBooks);

  
  // Приховування/показ блоку
 
 function toggleReviewForm() {
  const form = document.getElementById("reviewFormWrapper");
  form.style.display = (form.style.display === "none") ? "block" : "none";
}
window.toggleReviewForm = toggleReviewForm; // Додає у глобальну область

  // Розгортання жанрів
 
  document.querySelectorAll('.genre-header').forEach(btn => {
  btn.addEventListener('click', () => {
    const card = btn.parentElement;
    card.classList.toggle('active');
  });
});
});


// Адреса сервера
const API_URL = 'http://localhost:3000/api/books';

// Функція, яка запускається при завантаженні сторінки
document.addEventListener('DOMContentLoaded', loadBooks);

async function loadBooks() {
    const container = document.getElementById('books-container');

    try {
        // 1. Робимо запит до сервера
        const response = await fetch(API_URL);
        
        // 2. Перетворюємо відповідь у JSON (масив об'єктів)
        const books = await response.json();

        // 3. Проходимося по кожній книзі і створюємо HTML
        books.forEach(book => {
            // Створюємо картку
            const card = document.createElement('section');
            card.classList.add('book-card');

            // Наповнюємо картку даними з БД
            
            card.innerHTML = `
                <img src="${book.CoverImagePath || 'covers/no-image.jpg'}" alt="${book.Title}">
                <section class="book-info">
                    <h3>${book.Title}</h3>
                    <p>${book.Author}</p>
                    <p class="book-price">${book.Price} грн</p>
                </section>
                <button class="order-btn" data-id="${book.BookID}">Замовити</button>
            `;

            // Додаємо картку на сторінку
            container.appendChild(card);
        });

    } catch (error) {
        console.error('Помилка:', error);
        container.innerHTML = '<p>Не вдалося завантажити книги. Сервер не відповідає.</p>';
    }
}