# Backend Diagnostics

Этот модуль добавляет внутреннюю диагностику для ServiceAI.

## Подготовка окружения
1. Скопируйте `.env.example` в `.env` и задайте значения:
   - `DATABASE_URL` для подключения к Postgres.
   - `DEBUG` и `ENV` — в продакшене ставьте `DEBUG=false` и `ENV=production`.
   - `DB_AUTO_CREATE` — по умолчанию `false`. Включайте `true` только в локальной разработке вместе с `DEBUG=true` и `ENV=development`, чтобы скрипт `create_db.py` мог автоматически создать таблицы. **НЕ ИСПОЛЬЗУЙТЕ В PRODUCTION.**
   - `ADMIN_EMAIL` и `ADMIN_PASSWORD` — опционально для первичного создания администратора; если они не заданы, bootstrap будет пропущен.
   - `CHANNEL_CONFIG_SECRET_KEY` для шифрования конфигов каналов.
   - `INTERNAL_API_KEY` — секретный ключ для доступа к `/diagnostics`.
   - `APP_ENV` — `development` (по умолчанию) или `production`. В режиме production приложение не запускается с debug-опциями.
   - `DEBUG` — `true` включайте только при `APP_ENV=development`, чтобы активировать debug FastAPI/SQLAlchemy. При `APP_ENV=production` значение `true` будет отклонено.
   - CORS:
     - `CORS_ALLOW_ORIGINS` — список доменов через запятую (поддерживаются пробелы). В debug или если переменная не задана, по умолчанию `http://localhost:3000,http://127.0.0.1:3000`.
     - `CORS_ALLOW_CREDENTIALS` — `true`/`false` (по умолчанию `true`).
     - `CORS_ALLOW_METHODS` — список HTTP-методов через запятую (по умолчанию `*`).
     - `CORS_ALLOW_HEADERS` — список заголовков через запятую (по умолчанию `*`).
   - Telegram-авторизация:
     - `AUTH_TELEGRAM_ONLY` — `true`, чтобы отключить парольный вход и смену пароля (по умолчанию `false`).
     - `TELEGRAM_AUTH_BOT_TOKEN` и `TELEGRAM_AUTH_BOT_USERNAME` — токен и username бота, через которого подтверждается вход.
     - `TELEGRAM_WEBHOOK_SECRET` — секрет, требуемый для вызова вебхука.
     - `TELEGRAM_WEBHOOK_PATH` — путь для вебхука (по умолчанию `/auth/telegram/webhook`).
     - `PUBLIC_BASE_URL` — публичный URL сервера для генерации ссылки вебхука.

### Правила и примеры для CORS
- В production (`DEBUG=false`) при `CORS_ALLOW_CREDENTIALS=true` требуется явный список доменов; `*` или пустое значение вызовет ошибку при старте приложения.
- В debug `*` допустим только вместе с `CORS_ALLOW_CREDENTIALS=false`. Без заданного списка автоматически используются локальные origin `http://localhost:3000` и `http://127.0.0.1:3000`.
- Примеры:
  - `CORS_ALLOW_ORIGINS=https://example.com, https://admin.example.com`
  - `CORS_ALLOW_ORIGINS=*` и `CORS_ALLOW_CREDENTIALS=false` (debug)
  - `CORS_ALLOW_METHODS=GET, POST, OPTIONS`
  - `CORS_ALLOW_HEADERS=Authorization, Content-Type`

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

## WebSocket requirements
- Для работы `/ws/*` нужен `uvicorn` с extras `standard` или установленный `websockets`/`wsproto`.
- Команда проверки:
  ```bash
  poetry run python -c "import websockets; print('websockets OK', websockets.__version__)"
  ```
- Симптомы при отсутствии зависимостей: предупреждения `uvicorn` и `404` на `/ws/...`.

## Release checklist
- Установите зависимости backend: `poetry install`.
- Для опциональных AI-фичей установите доп. зависимости: `poetry install --with ai`.
- Если AI-зависимости не установлены или не заданы креды, AI отключается и диалоги переходят в режим оператора.
- Загрузка PDF/DOCX требует `PyMuPDF` и `python-docx` (ставятся через `--with ai`).
- Ограничения знаний: размер файла до 2MB, общая квота 10MB.

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
  1. Установите `DB_AUTO_CREATE=false`, `DEBUG=false`, `ENV=production` в `.env`.
  2. Выполните `alembic -c alembic.ini upgrade head` (через Poetry или активированный venv).
  3. Запустите backend.
- **Уже работающая БД, созданная через create_all**:
  1. Установите `DB_AUTO_CREATE=false`, `DEBUG=false`, `ENV=production` в `.env`.
  2. Выполните `alembic -c alembic.ini stamp head` (через Poetry или активированный venv).
  3. Запустите backend.
- **Будущие изменения схемы**: создавайте миграции через `alembic -c alembic.ini revision --autogenerate -m "...описание..."`, затем применяйте `upgrade head`.

### Подсказки
- Если автогенерация не видит таблицы, убедитесь, что все модели импортируются в `alembic/env.py`.
- Проверьте, что переменная `DATABASE_URL` указывает на ту же БД, которую использует backend.

## Telegram webhook
- Путь вебхука определяется `TELEGRAM_WEBHOOK_PATH` (по умолчанию `/auth/telegram/webhook`). Итоговый URL:\
  `https://<PUBLIC_BASE_URL>${TELEGRAM_WEBHOOK_PATH}?secret=${TELEGRAM_WEBHOOK_SECRET}`
- Nginx должен проксировать `${TELEGRAM_WEBHOOK_PATH}` и весь `/auth/` напрямую в backend, не через Next.js.
- Пример установки вебхука для бота:
  ```bash
  curl -X POST "https://api.telegram.org/bot${TELEGRAM_AUTH_BOT_TOKEN}/setWebhook" \
    -d "url=https://<PUBLIC_BASE_URL>${TELEGRAM_WEBHOOK_PATH}?secret=${TELEGRAM_WEBHOOK_SECRET}"
  ```
- Проверка вебхука после настройки nginx (URL без `/api`):
  ```bash
  curl -i -X POST "https://<PUBLIC_BASE_URL>${TELEGRAM_WEBHOOK_PATH}?secret=${TELEGRAM_WEBHOOK_SECRET}" \
    -H "Content-Type: application/json" \
    --data '{"message":{"text":"/start login_test","chat":{"id":1},"from":{"id":1}}}'
  ```
  Ответ `Login token invalid` означает: маршрут доступен, секрет совпал, но токен тестовый.

## Режимы разработки и продакшена
- По умолчанию конфигурация безопасна для продакшена: `APP_ENV=development` и `DEBUG=false` не включают verbose/debug middleware и SQL-логирование.
- Чтобы включить dev-режим с дополнительными логами и hot-reload, задайте `APP_ENV=development` и `DEBUG=true` перед запуском `uvicorn`.
- Для продакшена используйте `APP_ENV=production` (оставляя `DEBUG=false`) — при таком значении попытка запустить приложение с `DEBUG=true` приведёт к ошибке и не позволит нечаянно включить debug.

## Запуск диагностики
Форматы режимов: `fast`, `deep`, `full`. Пример вызова CLI:
```bash
cd backend
python -m app.diagnostics --base-url http://localhost:8000 --mode deep --account-id 12 --since 24h
```
Опционально добавьте `--internal-key`, если ключ не задан в окружении. Флаг `--verbose` выводит детали проверок.
CLI использует встроенный HTTP-клиент на базе `httpx`, дополнительный `curl` не требуется (Windows и Linux работают «из коробки»).

## Интеграция Bitrix24 (OAuth + Open Lines)
1. Создайте локальное приложение в Bitrix24 и укажите redirect URL на backend:
   - `https://<backend-domain>/integrations/bitrix24/oauth/callback`
2. Заполните env:
   - `BITRIX24_APP_CLIENT_ID`
   - `BITRIX24_APP_CLIENT_SECRET`
   - `BITRIX24_APP_REDIRECT_URL`
   - `BITRIX24_APP_SCOPES` (минимум: `imopenlines,im,crm`)
   - `BITRIX24_CONNECT_STATE_SECRET`
3. В Bitrix24 включите Open Lines / Connectors и привяжите приложение.
4. В UI откройте `Интеграции`, выберите бота, введите портал (`mycompany.bitrix24.ru`) и нажмите `Подключить`.
5. После подключения входящие сообщения отправляются в Open Lines, ответы операторов из Bitrix24 принимаются endpoint `POST /integrations/bitrix24/events` и пересылаются пользователю в исходный канал.
