# ServiceAI

Черновой каркас для backend ServiceAI на FastAPI. Внутри `backend/app` разложены основные модули (bots, channels, dialogs, ai), черновые модели и роутеры, а также вспомогательные утилиты. Docker-файлы расположены в каталоге `docker/`.

Запуск dev-окружения (потребуется Docker):

```bash
docker compose -f docker/docker-compose.yml up --build
```

Перед запуском убедитесь, что Postgres доступен на `localhost:5432` (или укажите правильный порт в `DATABASE_URL`).
Если база недоступна, backend теперь завершит запуск с понятной ошибкой, вместо того чтобы падать 500 при авторизации.

Основные точки входа:
- `backend/app/main.py` — FastAPI приложение со сборкой роутеров.
- `backend/pyproject.toml` — зависимости Poetry для backend.
- `docker/Dockerfile.backend` — сборка API-сервиса.
- Поддерживается вход через Telegram: установите `AUTH_TELEGRAM_ONLY=true`, чтобы отключить парольный вход. При значении `false` Telegram-авторизация работает совместно с логином по email/паролю.

## Диагностика

Backend предоставляет служебный эндпоинт `/diagnostics` для проверки состояния приложения и зависимостей.
Тот же набор проверок можно выполнить из CLI:

```bash
cd backend
python -m app.diagnostics
```

Необходимые переменные окружения:

- `PUBLIC_BASE_URL` — публичный базовый URL сервиса (например, `https://app.example.com`).
- `INTERNAL_API_KEY` — ключ доступа для внутренних запросов (укажите ваш ключ; не храните реальные значения в репозитории).

## Frontend

В каталоге `frontend` находится Next.js-приложение. Перед запуском установите зависимости и подготовьте переменные окружения:

```bash
cd frontend
npm install
cp .env.example .env.local
```

Команды разработки и сборки:

- `npm run dev` — запуск dev-сервера.
- `npm run build` — сборка production-версии.
- `npm run start` — запуск собранного приложения.
- `npm run lint` — линтинг кода.

Необходимые переменные окружения (смотрите `frontend/.env.example`):

- `NEXT_PUBLIC_API_BASE_URL` — базовый URL API (например, dev: `http://localhost:8000`, prod: `https://api.example.com`).
- `NEXT_PUBLIC_ENABLE_WIDGET_INTEGRATION` — включает генерацию кода webchat-виджета (dev: `true`, prod по умолчанию `false`).

## Nginx reverse proxy (production)

Iframe `/embed/webchat/*` всегда обращается к `/api/...`, поэтому без reverse proxy на уровне Nginx будет отображаться “Ошибка подключения”. Используйте готовый конфиг `deploy/nginx/serviceai.conf`:

```bash
sudo cp deploy/nginx/serviceai.conf /etc/nginx/sites-available/serviceai.conf
sudo ln -s /etc/nginx/sites-available/serviceai.conf /etc/nginx/sites-enabled/serviceai.conf
sudo nginx -t
sudo systemctl reload nginx
```

Проверка (если нет health-эндпоинта, используйте `/api/`):

```bash
curl -I https://DOMAIN/
curl -I https://DOMAIN/api/health
```
