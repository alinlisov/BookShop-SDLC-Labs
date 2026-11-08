
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, ProxyHandler


@dataclass
class Check:
    name: str
    status: str
    note: str
    ms: int | None


class Checker:
    def __init__(self, base: str, timeout: float, threshold: float):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.threshold = threshold
        self.checks: list[Check] = []
        self.client = build_opener(ProxyHandler({}))

    def fetch(self, path: str) -> tuple[int, bytes, str, int]:
        request = Request(self.base + path, headers={"Accept": "application/json, text/html, text/css, application/javascript"})
        start = time.perf_counter()
        try:
            with self.client.open(request, timeout=self.timeout) as response:
                code, body = response.status, response.read(512_000)
                content_type = response.headers.get("Content-Type", "")
        except HTTPError as exc:
            code = exc.code
            body = exc.read(8192)
            content_type = exc.headers.get("Content-Type", "")
        ms = int((time.perf_counter() - start) * 1000)
        return code, body, content_type, ms

    def run(self, name: str, path: str, want: int, *, contains: str | None = None,
            json_kind: type | None = None, optional: bool = False,
            expected_json: dict | None = None) -> tuple[int, object | None]:
        try:
            code, body, content_type, ms = self.fetch(path)
            payload = None
            if json_kind is not None:
                try:
                    payload = json.loads(body.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    payload = None
            good = (code == want and (contains is None or contains.lower() in body.decode("utf-8", errors="replace").lower())
                    and (json_kind is None or isinstance(payload, json_kind))
                    and (expected_json is None or (isinstance(payload, dict) and all(payload.get(k) == v for k, v in expected_json.items()))))
            if good:
                status = "OK"
            elif optional and code == 404:
                status = "УВАГА"
            else:
                status = "ПОМИЛКА"
            timing = f"{ms} мс"
            if ms > self.threshold * 1000 and good:
                status = "УВАГА"
                timing += "; понад орієнтир 2 с (одиничний вимір)"
            note = f"HTTP {code}; {timing}"
            if status == "УВАГА" and code == 404:
                note += "; ресурс відсутній у поточній версії"
            if status == "ПОМИЛКА":
                note += f"; очікувався HTTP {want} та коректний формат"
            self.checks.append(Check(name, status, note, ms))
            print(f"[{status}] {name} — {note}")
            return code, payload
        except (URLError, TimeoutError, OSError) as exc:
            msg = type(exc).__name__
            self.checks.append(Check(name, "ПОМИЛКА", f"Немає відповіді ({msg}); перевірте сервер/порт", None))
            print(f"[ПОМИЛКА] {name} — сервер не відповів ({msg})")
            return 0, None

    def write_report(self, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        ok = sum(c.status == "OK" for c in self.checks)
        warn = sum(c.status == "УВАГА" for c in self.checks)
        fail = sum(c.status == "ПОМИЛКА" for c in self.checks)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = ["# Перевірка інтегрованої системи BookShop (ЛР №5)", "",
                f"Дата локальної перевірки: **{stamp}**  ",
                f"Адреса: `{self.base}`  ",
                f"Підсумок: **успішно — {ok}, попередження — {warn}, помилки — {fail}**", "",
                "| Перевірка | Стан | Фактичний результат |", "|---|---|---|"]
        rows += [f"| {c.name} | {c.status} | {c.note} |" for c in self.checks]
        rows += ["", "## Межі перевірки", "",
                 "Це лише безпечна перевірка **читання даних і доступності**. Програма не створює користувачів, замовлень чи відгуків та не змінює PostgreSQL.",
                 "Окремо вручну перевірте: реєстрацію, вхід, вихід, замовлення, відгуки, історію замовлень, права адміністратора та збереження даних.",
                 "Час відповіді — одноразове локальне вимірювання. Воно **не доводить** виконання вимоги 2 с для всіх користувачів, підтримку 100 одночасних користувачів або доступність 99,5 %.",
                 "Локальний HTTP не підтверджує HTTPS; для цієї вимоги потрібне розгортання з TLS.",
                 "Не вставляйте у звіт токени, ключі `.env`, паролі або справжні персональні дані.", ""]
        output.write_text("\n".join(rows), encoding="utf-8")
        print(f"\nЗвіт збережено: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ЛР5: безпечна перевірка локального FastAPI + frontend")
    parser.add_argument("--url", default="http://127.0.0.1:8001", help="Базова URL-адреса локального сайту")
    parser.add_argument("--timeout", type=float, default=4, help="Тайм-аут кожного запиту в секундах")
    parser.add_argument("--out", default="qa_results/check_bookshop.md", help="Шлях до звіту Markdown")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("127.0.0.1", "localhost"):
        parser.error("Для безпеки дозволено лише локальний сервер localhost або 127.0.0.1")
    if args.timeout <= 0 or args.timeout > 30:
        parser.error("--timeout має бути від 0 до 30 секунд")
    checker = Checker(args.url, args.timeout, 2.0)
    code, _ = checker.run("Перевірка API /api/health", "/api/health", 200,
                           json_kind=dict, expected_json={"status": "ok"})
    if code == 0:
        checker.write_report(Path(args.out))
        print("\nСервер не відповідає. Перевірте команду uvicorn і порт 8001.")
        return 1
    checker.run("Головна сторінка", "/", 200, contains="<html")
    checker.run("Swagger UI", "/docs", 200, contains="swagger")
    code, books = checker.run("Каталог із PostgreSQL", "/api/books", 200, json_kind=list)
    checker.run("Пошук за назвою", "/api/books?search=check-no-such-title-847234", 200, json_kind=list)
    if isinstance(books, list) and books:
        first = books[0]
        if isinstance(first, dict) and isinstance(first.get("id"), int) and isinstance(first.get("title"), str):
            book_id = first["id"]
            checker.run("Детальна картка книжки", f"/api/books/{book_id}", 200, json_kind=dict)
            checker.run("Пошук існуючої книжки", "/api/books?search=" + quote(first["title"][:14]), 200,
                        json_kind=list)
            checker.run("Відгуки вибраної книжки", f"/api/books/{book_id}/reviews", 200, json_kind=list)
    else:
        checker.checks.append(Check("Книжки в базі", "УВАГА", "Каталог порожній; перевірте seed та PostgreSQL", None))
        print("[УВАГА] Каталог порожній — перевірте seed і PostgreSQL")
    checker.run("Сторінка реєстрації", "/register.html", 200, contains="<form")
    checker.run("Сторінка входу", "/login.html", 200, contains="<form")
    checker.run("Сторінка профілю (HTML)", "/profile.html", 200, contains="<html")
    checker.run("Сторінка адміністратора (HTML)", "/admin.html", 200, contains="<html")
    checker.run("JS-модуль API", "/js/api.js", 200)
    checker.run("Сучасні стилі", "/css/bookshop-modern.css", 200)
    checker.run("JS-каталог", "/js/modern-main.js", 200)
    checker.run("Профіль без токена захищено", "/api/auth/me", 401, json_kind=dict)
    checker.run("Особисті замовлення без токена захищено", "/api/orders/mine", 401, json_kind=dict)
    checker.run("Адмін-замовлення без токена захищено", "/api/admin/orders", 401, json_kind=dict)
    checker.run("Конфігурація БД недоступна", "/backend/.env", 404)
    checker.run("Початковий код сервера недоступний", "/backend/app/main.py", 404)
    checker.run("Файл .gitignore недоступний", "/.gitignore", 404)
    checker.write_report(Path(args.out))
    failures = sum(c.status == "ПОМИЛКА" for c in checker.checks)
    warnings = sum(c.status == "УВАГА" for c in checker.checks)
    print(f"\nПідсумок: помилки={failures}, попередження={warnings}; це НЕ повний аудит безпеки чи навантаження.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
