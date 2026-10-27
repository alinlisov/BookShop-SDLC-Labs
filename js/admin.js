const API_URL = 'http://localhost:3000/api/books';
let allBooks = [];

// 1. ПЕРЕВІРКА АВТОРИЗАЦІЇ
const token = localStorage.getItem('token');
if (!token) {
    window.location.href = 'login.html'; // Якщо немає токена — на вихід
}


function logout() {
    localStorage.removeItem('token');
    window.location.href = 'login.html';
}

document.addEventListener('DOMContentLoaded', () => {
    loadBooks();
    setupForm();
});

// 2. ЗАВАНТАЖЕННЯ (READ)
async function loadBooks() {
    const tableBody = document.getElementById('books-table-body');
    
    try {
        const response = await fetch(API_URL);
        allBooks = await response.json();

        tableBody.innerHTML = '';
        allBooks.forEach(book => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${book.BookID}</td>
                <td>${book.Title}</td>
                <td>${book.Author}</td>
                <td>${book.Price} грн</td>
                <td class="action-cell">
                    <button class="action-btn edit-btn" onclick="startEdit(${book.BookID})">✏️</button>
                    <button class="action-btn delete-btn" onclick="deleteBook(${book.BookID})">🗑️</button>
                </td>
            `;
            tableBody.appendChild(row);
        });

        const countElement = document.querySelector('.stat-card:nth-child(2) p');
        if(countElement) countElement.innerText = allBooks.length;

    } catch (error) {
        console.error('Помилка:', error);
    }
}

// 3. РЕЖИМ РЕДАГУВАННЯ
window.startEdit = (id) => {
    const book = allBooks.find(b => b.BookID === id);
    if (!book) return;

    document.getElementById('book-id').value = book.BookID;
    document.getElementById('book-title').value = book.Title;
    document.getElementById('book-author').value = book.Author;
    document.getElementById('book-price').value = book.Price;
    document.getElementById('book-genre').value = book.GenreID || 1; 

    const submitBtn = document.getElementById('submit-btn');
    submitBtn.innerText = 'Зберегти зміни';
    submitBtn.style.background = '#e63946'; 

    document.getElementById('cancel-btn').style.display = 'inline-block';
    document.querySelector('.crud-form').scrollIntoView({ behavior: 'smooth' });
};

document.getElementById('cancel-btn').addEventListener('click', () => {
    resetForm();
});

function resetForm() {
    const form = document.getElementById('add-book-form');
    form.reset();
    document.getElementById('book-id').value = ''; 
    
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.innerText = 'Додати';
    submitBtn.style.background = ''; 
    document.getElementById('cancel-btn').style.display = 'none';
}

// 4. ОБРОБКА ФОРМИ (CREATE / UPDATE) 
function setupForm() {
    const form = document.getElementById('add-book-form');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const id = document.getElementById('book-id').value;
        const title = document.getElementById('book-title').value;
        const author = document.getElementById('book-author').value;
        const price = document.getElementById('book-price').value;
        const genreId = document.getElementById('book-genre').value;

        const bookData = { title, author, price, genreId };

        try {
            let response;
            
            
            const headers = { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            };

            if (id) {
                // РЕЖИМ РЕДАГУВАННЯ (PUT)
                response = await fetch(`${API_URL}/${id}`, {
                    method: 'PUT',
                    headers: headers, 
                    body: JSON.stringify(bookData)
                });
            } else {
                // РЕЖИМ СТВОРЕННЯ (POST)
                response = await fetch(API_URL, {
                    method: 'POST',
                    headers: headers, 
                    body: JSON.stringify(bookData)
                });
            }

            if (response.ok) {
                alert(id ? 'Книгу оновлено!' : 'Книгу додано!');
                resetForm(); 
                loadBooks(); 
            } else {
                // Якщо токен прострочився або помилка
                const errData = await response.json();
                alert('Помилка: ' + errData.message);
                if (response.status === 401 || response.status === 403) {
                    window.location.href = 'login.html'; // Викидаємо на вхід
                }
            }
        } catch (error) {
            console.error('Помилка:', error);
        }
    });
}

// 5. ВИДАЛЕННЯ (DELETE) 
window.deleteBook = async (id) => {
    if (!confirm('Видалити цю книгу?')) return;
    try {
        const response = await fetch(`${API_URL}/${id}`, { 
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}` 
            }
        });

        if (response.ok) {
            loadBooks();
        } else {
            alert("Не вдалося видалити. Можливо, немає прав.");
        }
    } catch (error) {
        console.error(error);
    }
};