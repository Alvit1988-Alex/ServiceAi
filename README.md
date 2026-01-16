# ServiceAI Backend

Backend-часть проекта ServiceAI.
Отвечает за API, аутентификацию, Telegram-вход, работу с БД и диагностику.

---

## Требования

- Python 3.10+
- PostgreSQL 14+
- nginx (для продакшена)
- Telegram Bot Token

---

## Переменные окружения

Минимально необходимые переменные:

    ENV=production
    DEBUG=false

    DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/serviceai

    PUBLIC_BASE_URL=https://example.com

    TELEGRAM_AUTH_BOT_TOKEN=123456:ABCDEF...
    TELEGRAM_WEBHOOK_SECRET=long_random_secret
    TELEGRAM_WEBHOOK_PATH=/auth/telegram/webhook

Важно:
- PUBLIC_BASE_URL — публичный домен, через который Telegram обращается к backend (обычно домен nginx, не localhost).
- TELEGRAM_WEBHOOK_PATH НЕ должен проксироваться через Next.js. В nginx этот путь должен идти в backend напрямую.

---

## Установка зависимостей

Через Poetry:

    cd backend
    poetry install

Через venv / pip:

    cd backend
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

---

## Запуск backend

Development:

    cd backend
    ENV=development DEBUG=true python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Production (обычно за nginx, слушаем только localhost):

    cd backend
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

---

## Миграции БД

Новая установка (пустая БД):
1) В .env установите:
       DB_AUTO_CREATE=false
       DEBUG=false
       ENV=production

2) Примените миграции:
       alembic -c alembic.ini upgrade head

3) Запустите backend.

Уже существующая БД (создана через create_all):
1) В .env установите:
       DB_AUTO_CREATE=false
       DEBUG=false
       ENV=production

2) Пометьте схему как актуальную:
       alembic -c alembic.ini stamp head

Будущие изменения схемы:
    alembic -c alembic.ini revision --autogenerate -m "описание"
    alembic -c alembic.ini upgrade head

Подсказки:
- Если автогенерация не видит таблицы — убедитесь, что модели импортируются в alembic/env.py
- Проверьте, что DATABASE_URL указывает на ту же БД, что использует backend

---

## Telegram Webhook

Итоговый URL вебхука формируется так:

    https://<PUBLIC_BASE_URL>${TELEGRAM_WEBHOOK_PATH}?secret=${TELEGRAM_WEBHOOK_SECRET}

Пример:

    https://dostup.tgkod.ru/auth/telegram/webhook?secret=XXXXXXXX

Установка вебхука:

    curl -X POST "https://api.telegram.org/bot${TELEGRAM_AUTH_BOT_TOKEN}/setWebhook" \
      -d "url=https://<PUBLIC_BASE_URL>${TELEGRAM_WEBHOOK_PATH}?secret=${TELEGRAM_WEBHOOK_SECRET}"

Проверка webhook после настройки nginx (nginx должен проксировать /auth/telegram/webhook напрямую в backend):

    curl -i -X POST "https://<PUBLIC_BASE_URL>${TELEGRAM_WEBHOOK_PATH}?secret=${TELEGRAM_WEBHOOK_SECRET}" \
      -H "Content-Type: application/json" \
      --data '{"message":{"text":"/start login_test","chat":{"id":1},"from":{"id":1}}}'

Ожидаемый ответ backend (пример):

    {"ok":true,"message":"Login token invalid"}

Если Telegram показывает в getWebhookInfo:
    "Wrong response from the webhook: 404 Not Found"
— значит webhook попадает не в backend (обычно в Next.js или не настроен location в nginx).

---

## nginx (критично для Telegram)

Требование:
- /auth/telegram/webhook должен попадать в backend (127.0.0.1:8000), а НЕ в Next.js (127.0.0.1:3000)

Пример serviceai.conf (ключевые location):

    location = /auth/telegram/webhook {
        proxy_pass http://127.0.0.1:8000/auth/telegram/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ^~ /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

---

## Режимы разработки и продакшена

- Рекомендуемый режим: ENV=production и DEBUG=false
- В продакшене backend обычно слушает только 127.0.0.1 и доступен снаружи через nginx

---

## Диагностика

Пример вызова:

    cd backend
    python -m app.diagnostics --base-url http://localhost:8000 --mode deep --account-id 12 --since 24h

Режимы:
- fast
- deep
- full

Опции:
- --internal-key (если ключ не задан в окружении)
- --verbose (подробный вывод)

CLI использует httpx, curl не требуется.
