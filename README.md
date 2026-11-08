# Літера - BookShop

Навчальний інтегрований вебзастосунок інтернет-магазину книжок з дисципліни **«Життєвий цикл розробки програмного забезпечення»** (лабораторна №5 - «Інтеграція компонентів та управління залежностями»).

Репозиторій: https://github.com/alinlisov/BookShop-SDLC-Labs

## Можливості

- Каталог книжок із назвами, авторами, жанрами, цінами й інформацією про наявність; пошук і фільтрація у вебінтерфейсі.
- Реєстрація та вхід користувача; перевірка форм і повідомлення про помилки.
- Розмежування ролей користувача й адміністратора на сервері.
- Оформлення гостьових та авторизованих замовлень; сервер обчислює підсумкову ціну за записами PostgreSQL.
- Особистий кабінет з історією власних замовлень.
- Відгуки авторизованих користувачів зі збереженням у PostgreSQL.
- Адміністрування каталогу, замовлень і відгуків (за наявності прав).
- Адаптивний інтерфейс «Літера» на HTML/CSS/JavaScript.

## Технології

| Рівень | Технології |
| --- | --- |
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python 3.11, FastAPI, Uvicorn |
| ORM/БД | SQLAlchemy, PostgreSQL, psycopg |
| Схеми даних | Pydantic, email-validator |
| Захист даних | argon2-cffi, cryptography (AES-256-GCM), PyJWT |
| Тестування | pytest, FastAPI TestClient, локальна перевірка `verify_bookshop.py` |
| Контроль версій | Git, GitHub Desktop |

## Структура

```text
BookShop-SDLC-Labs/
├── backend/
│   ├── app/
│   │   ├── routers/        # auth, books, orders, reviews
│   │   ├── main.py         # FastAPI та підключення маршрутів
│   │   ├── web_pages.py    # Дозволені HTML-сторінки
│   │   ├── database.py     # PostgreSQL / SQLAlchemy
│   │   ├── models.py       # ORM-моделі
│   │   ├── schemas.py      # Перевірка даних
│   │   ├── security.py     # Хешування й шифрування
│   │   ├── auth_tokens.py  # JWT та сесії
│   │   └── seed.py         # Демонстраційні книжки
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── css/
├── js/
├── covers/
├── tools/
│   └── verify_bookshop.py
├── index.html
├── register.html
├── login.html
├── profile.html
├── admin.html
├── business.html
├── README.md
└── .gitignore
```

## Локальне встановлення (Windows, PowerShell)

**Передумови:** Python 3.11, PostgreSQL із базою `bookshop`, GitHub Desktop або Git. Запускайте команди з папки `BookShop-SDLC-Labs`.

```powershell
cd "D:\кпі\ЖЦРПЗ\BookShop-SDLC-Labs"
cd backend

# Якщо .venv вже існує та працює - не створюйте повторно.
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Якщо середовище вже створене й працює, достатньо виконати команду встановлення залежностей.

### Налаштування `.env`

Створіть `backend/.env` за зразком `backend/.env.example` (без завантаження в GitHub). Приклад форми:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bookshop
DATA_ENCRYPTION_KEY=YOUR_GENERATED_KEY
EMAIL_LOOKUP_KEY=YOUR_GENERATED_KEY
AUTH_SIGNING_KEY=YOUR_GENERATED_KEY
```

Для нового середовища генератори ключів (під час першого налаштування):

```powershell
.\.venv\Scripts\python.exe -m app.generate_keys
.\.venv\Scripts\python.exe -m app.generate_auth_key
```

### Запуск

```powershell
# У папці backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Відкрийте вручну:

- Магазин: http://127.0.0.1:8001/
- Swagger UI: http://127.0.0.1:8001/docs
- API перевірка: http://127.0.0.1:8001/api/health
- Каталог API: http://127.0.0.1:8001/api/books

У разі порожнього каталогу можна виконати `python -m app.seed` із віртуального середовища, переконавшись, що вказано правильну базу PostgreSQL. Не запускайте `main.py` безпосередньо - використовуйте `uvicorn`.

### Тести

```powershell
# У папці backend
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
```

Для перевірки **вже запущеного** сервера з кореня проєкту:

```powershell
.\backend\.venv\Scripts\python.exe .\tools\verify_bookshop.py --url http://127.0.0.1:8001
```

Скрипт виконує лише запити читання; записує результат у `qa_results/check_bookshop.md`. Для повного доказу інтеграції додатково потрібне ручне тестування реєстрації, входу, замовлень, відгуків, ролей та мобільного інтерфейсу. 
## Основні REST API

| Метод | Маршрут | Призначення |
| --- | --- | --- |
| GET | `/api/health` | Стан сервера |
| GET | `/api/books` | Каталог і пошук |
| GET | `/api/books/{book_id}` | Окрема книжка |
| POST | `/api/auth/register` | Реєстрація |
| POST | `/api/auth/login` | Вхід |
| GET | `/api/auth/me` | Дані поточного користувача |
| POST | `/api/auth/logout` | Завершення сесії |
| POST | `/api/orders` | Створення замовлення |
| GET | `/api/orders/mine` | Замовлення користувача |
| GET/POST | `/api/books/{book_id}/reviews` | Відгуки |
| GET/PATCH/POST/DELETE | `/api/admin/...` | Захищене адміністрування |

## Вимоги та обмеження

Функціональні вимоги FR-1–FR-5 і нефункціональні NFR-1–NFR-4 визначені в лабораторній №1. Матриця перевірки та межі підтвердження розміщені в `docs/REQUIREMENTS_CHECKLIST.md`.  

