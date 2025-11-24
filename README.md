# ServiceAI

Черновой каркас для backend ServiceAI на FastAPI. Внутри `backend/app` разложены основные модули (bots, channels, dialogs, ai), черновые модели и роутеры, а также вспомогательные утилиты. Docker-файлы расположены в каталоге `docker/`.

Запуск dev-окружения (потребуется Docker):

```bash
docker compose -f docker/docker-compose.yml up --build
```

Основные точки входа:
- `backend/app/main.py` — FastAPI приложение со сборкой роутеров.
- `backend/pyproject.toml` — зависимости Poetry для backend.
- `docker/Dockerfile.backend` — сборка API-сервиса.

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

- `NEXT_PUBLIC_API_BASE_URL` — базовый URL API (например, `http://localhost:8000`).
