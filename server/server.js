const express = require('express');
const cors = require('cors');
const db = require('./db'); // Підключення до БД
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const SECRET_KEY = process.env.JWT_SECRET || 'super_secret_key_12345';
require('dotenv').config();

const app = express();

// Налаштування
app.use(cors());
app.use(express.json());

// MIDDLEWARE (ОХОРОНЕЦЬ)
function checkAdmin(req, res, next) {
    // 1. Шукаємо токен у заголовку запиту
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.status(401).json({ message: 'Токен відсутній! Увійдіть у систему.' });
    }

    // 2. Перевіряємо, чи токен справжній
    jwt.verify(token, SECRET_KEY, (err, user) => {
        if (err) {
            return res.status(403).json({ message: 'Невірний або прострочений токен' });
        }

        // 3. Перевіряємо роль
        if (user.role !== 'Admin') {
            return res.status(403).json({ message: 'Доступ заборонено! Тільки для Адмінів.' });
        }

        req.user = user;
        next();
    });
}

// АВТОРИЗАЦІЯ

// 1. РЕЄСТРАЦІЯ 
app.post('/auth/register', async (req, res) => {
    const { fullName, email, password, role } = req.body;
    
    // Шифруємо пароль
    const hashPass = await bcrypt.hash(password, 10);

    try {
        await db.query(
            'INSERT INTO Users (FullName, Email, PasswordHash, Role) VALUES (?, ?, ?, ?)',
            [fullName, email, hashPass, role || 'User']
        );
        res.status(201).json({ message: 'Користувача створено!' });
    } catch (error) {
        console.error(error);
        res.status(500).json({ message: 'Помилка реєстрації (можливо, такий Email вже є)' });
    }
});

// 2. ЛОГІН (Вхід)
app.post('/auth/login',  async (req, res) => {
    const { email, password } = req.body;

    try {
        // Шукаємо користувача за email
        const [users] = await db.query('SELECT * FROM Users WHERE Email = ?', [email]);
        if (users.length === 0) {
            return res.status(401).json({ message: 'Користувача не знайдено' });
        }
        const user = users[0];

        // Перевіряємо пароль 
        const isValid = await bcrypt.compare(password, user.PasswordHash);
        if (!isValid) {
            return res.status(401).json({ message: 'Невірний пароль' });
        }

        // Генеруємо ТОКЕН (Пропуск)
        const token = jwt.sign(
            { id: user.UserID, role: user.Role }, 
            SECRET_KEY, 
            { expiresIn: '24h' } 
        );

        res.json({ token, role: user.Role });

    } catch (error) {
        console.error(error);
        res.status(500).json({ message: 'Помилка входу' });
    }
});

// --- API МАРШРУТИ ---

// 1. Отримати всі книги (GET)
app.get('/api/books', async (req, res) => {
    try {
        // Робимо SQL-запит до бази
        const [rows] = await db.query('SELECT * FROM Books');
        // Віддаємо результат як JSON
        res.json(rows);
    } catch (error) {
        console.error('Помилка БД:', error);
        res.status(500).json({ message: 'Помилка сервера' });
    }
});

// 2. Додати книгу (POST) 
app.post('/api/books', checkAdmin, async (req, res) => {
    const { title, author, price, genreId } = req.body;
    try {
        const sql = 'INSERT INTO Books (Title, Author, Price, GenreID) VALUES (?, ?, ?, ?)';
        const [result] = await db.query(sql, [title, author, price, genreId]);
        res.status(201).json({ message: 'Книгу додано!', id: result.insertId });
    } catch (error) {
        console.error(error);
        res.status(500).json({ message: 'Помилка при додаванні' });
    }
});



// 3. PUT - Оновити книгу (UPDATE)

app.put('/api/books/:id', checkAdmin, async (req, res) => {
    const bookId = req.params.id;
    const { title, author, price, genreId, cover } = req.body;

    try {
        const sql = `
            UPDATE Books 
            SET Title = ?, Author = ?, Price = ?, GenreID = ?, CoverImagePath = ? 
            WHERE BookID = ?
        `;
        const [result] = await db.query(sql, [title, author, price, genreId, cover, bookId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ message: 'Книгу не знайдено' });
        }

        res.json({ message: 'Книгу успішно оновлено' });
    } catch (error) {
        console.error(error);
        res.status(500).json({ message: 'Помилка при оновленні' });
    }
});

// 4. DELETE - Видалити книгу (DELETE)

app.delete('/api/books/:id', checkAdmin, async (req, res) => {
    const bookId = req.params.id;

    try {
        const sql = 'DELETE FROM Books WHERE BookID = ?';
        const [result] = await db.query(sql, [bookId]);

        if (result.affectedRows === 0) {
            return res.status(404).json({ message: 'Книгу не знайдено' });
        }

        res.json({ message: `Книгу (ID: ${bookId}) успішно видалено` });
    } catch (error) {
        console.error(error);
        res.status(500).json({ message: 'Помилка при видаленні' });
    }
});

// Запуск
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Сервер працює: http://localhost:${PORT}`);
});