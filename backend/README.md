# Backend Diagnostics

Этот модуль добавляет внутреннюю диагностику для ServiceAI.

## Подготовка окружения
1. Скопируйте `.env.example` в `.env` и задайте значения:
   - `DATABASE_URL` для подключения к Postgres.
   - `CHANNEL_CONFIG_SECRET_KEY` для шифрования конфигов каналов.
   - `INTERNAL_API_KEY` — секретный ключ для доступа к `/diagnostics`.

## Запуск backend
```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Запуск диагностики
Форматы режимов: `fast`, `deep`, `full`. Пример вызова CLI:
```bash
cd backend
python -m app.diagnostics --base-url http://localhost:8000 --mode deep --account-id 12 --since 24h
```
Опционально добавьте `--internal-key`, если ключ не задан в окружении. Флаг `--verbose` выводит детали проверок.
