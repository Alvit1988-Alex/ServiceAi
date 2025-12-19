# Backend Diagnostics

Этот модуль добавляет внутреннюю диагностику для ServiceAI.

## Подготовка окружения
1. Скопируйте `.env.example` в `.env` и задайте значения:
   - `DATABASE_URL` для подключения к Postgres.
   - `DB_AUTO_CREATE` — оставьте `true` для локальной разработки, чтобы скрипт `create_db.py` мог автоматически создать таблицы. В проде установите `false`, чтобы использовать только миграции.
   - `ADMIN_EMAIL` и `ADMIN_PASSWORD` — опционально для первичного создания администратора; если они не заданы, bootstrap будет пропущен.
   - `CHANNEL_CONFIG_SECRET_KEY` для шифрования конфигов каналов.
   - `INTERNAL_API_KEY` — секретный ключ для доступа к `/diagnostics`.

## Запуск backend
Команды следует выполнять из каталога `backend/`.

**Вариант A: Poetry**
```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Вариант B: venv/pip**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install .
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Миграции базы данных (Alembic)
Файлы конфигурации находятся в `backend/alembic.ini` и `backend/alembic/`. Убедитесь, что `DATABASE_URL` указывает на нужную базу.

- Создать новую миграцию (автогенерация):
  ```bash
  cd backend
  poetry run alembic -c alembic.ini revision --autogenerate -m "описание изменений"
  ```
  ```bash
  cd backend
  source .venv/bin/activate  # если используете venv/pip
  alembic -c alembic.ini revision --autogenerate -m "описание изменений"
  ```
- Применить миграции на пустую базу:
  ```bash
  cd backend
  poetry run alembic -c alembic.ini upgrade head
  ```
  ```bash
  cd backend
  source .venv/bin/activate  # если используете venv/pip
  alembic -c alembic.ini upgrade head
  ```
- Пометить существующую базу, созданную через `create_all`, без применения DDL:
  ```bash
  cd backend
  poetry run alembic -c alembic.ini stamp head
  ```
  ```bash
  cd backend
  source .venv/bin/activate  # если используете venv/pip
  alembic -c alembic.ini stamp head
  ```

## Миграции: новая БД vs существующая
- **Новая установка (пустая БД)**:
  1. Установите `DB_AUTO_CREATE=false` в `.env`.
  2. Выполните `alembic -c alembic.ini upgrade head` (через Poetry или активированный venv).
  3. Запустите backend.
- **Уже работающая БД, созданная через create_all**:
  1. Установите `DB_AUTO_CREATE=false` в `.env`.
  2. Выполните `alembic -c alembic.ini stamp head` (через Poetry или активированный venv).
  3. Запустите backend.
- **Будущие изменения схемы**: создавайте миграции через `alembic -c alembic.ini revision --autogenerate -m "...описание..."`, затем применяйте `upgrade head`.

### Подсказки
- Если автогенерация не видит таблицы, убедитесь, что все модели импортируются в `alembic/env.py`.
- Проверьте, что переменная `DATABASE_URL` указывает на ту же БД, которую использует backend.

## Запуск диагностики
Форматы режимов: `fast`, `deep`, `full`. Пример вызова CLI:
```bash
cd backend
python -m app.diagnostics --base-url http://localhost:8000 --mode deep --account-id 12 --since 24h
```
Опционально добавьте `--internal-key`, если ключ не задан в окружении. Флаг `--verbose` выводит детали проверок.
CLI использует системный `curl`, убедитесь, что он доступен в `PATH` (в Windows 10+ он предустановлен).
