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
