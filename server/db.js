const mysql = require('mysql2');
require('dotenv').config(); // Дозволяє читати файл .env

// Створюємо "пул" (набір) з'єднань.
const pool = mysql.createPool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME
});

// Дозволяємо використовувати async/await 
module.exports = pool.promise();