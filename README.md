# CyberTracker backend

REST API на **FastAPI** для киберспорт-арены: турниры, регистрации, QR-проход, аудит, прогноз посещаемости (модуль ИИ). База данных — **PostgreSQL** (SQLAlchemy 2 async, Alembic).

## Требования

- **Python** ≥ 3.14  
- **[uv](https://docs.astral.sh/uv/)** — зависимости и запуск  
- **Docker** + **Docker Compose** — опционально (БД и/или API в контейнерах)

## Быстрый старт (локально, без Docker API)

1. Склонируйте репозиторий и перейдите в корень проекта (каталог с `pyproject.toml`).

2. Создайте окружение и установите зависимости:

   ```bash
   uv sync --all-groups
   ```

3. Скопируйте пример переменных окружения и при необходимости отредактируйте:

   ```bash
   cp .env.example .env
   ```

4. Поднимите только PostgreSQL (если БД не установлена локально):

   ```bash
   docker compose up -d cybertracker_db
   ```

   Дождитесь готовности контейнера (`healthy`). В `.env` для приложения на хосте должны быть `POSTGRES_HOST=localhost` и `POSTGRES_PORT=5432`.

5. Примените миграции Alembic (когда они есть в репозитории):

   ```bash
   uv run alembic upgrade head
   ```

6. Запустите сервер с автоперезагрузкой:

   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

При первом запуске приложение может создать таблицы через `create_all` в `lifespan` — удобно для разработки. Для продакшена ориентируйтесь на миграции Alembic.

## Документация API

| Ресурс        | URL |
|---------------|-----|
| Scalar        | http://127.0.0.1:8000/scalar |
| Swagger UI    | http://127.0.0.1:8000/docs |
| ReDoc         | http://127.0.0.1:8000/redoc |
| OpenAPI JSON  | http://127.0.0.1:8000/openapi.json |

## Конфигурация

Параметры задаются переменными окружения и файлом **`.env`** (см. `.env.example`):

- окружение, логирование, CORS (`ORIGINS` — список origin через запятую);
- JWT и cookie для сессии;
- PostgreSQL (`POSTGRES_*`);
- путь к модели ИИ: `AI_MODEL_PATH` (по умолчанию `models/attendance_model.joblib`);
- TTL QR: `QR_TOKEN_TTL_SECONDS`.

Логика загрузки настроек — в `app/config.py` (в т.ч. сборка URL БД через **yarl**).

## Docker: продакшен-стек

API и PostgreSQL вместе:

```bash
cp .env.example .env   # задайте JWT_SECRET_KEY и пароль БД
docker compose up -d --build
```

- Сервисы: **`cybertracker_db`**, **`cybertracker_api`**.  
- В контейнере API переменная **`POSTGRES_HOST`** выставлена на имя сервиса БД (`cybertracker_db`).  
- Порт API на хосте: **`API_PORT`** (по умолчанию 8000).  
- Образ API собирается из **`Dockerfile`** (Debian slim + `uv`, без сборки sklearn из исходников).

Остановка:

```bash
docker compose down
```

## Docker: разработка (hot reload)

Используется второй файл поверх основного — монтируются `app/`, `models/`, `alembic/`, включается **`uvicorn --reload`**.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

В фоне: добавьте `-d`. Остановка:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

В **`docker-compose.dev.yml`** для **`cybertracker_db`** проброшен порт PostgreSQL на хост (`POSTGRES_PORT`, по умолчанию 5432).

## Модуль ИИ (прогноз посещаемости)

- Обучение модели и сохранение артефакта `joblib`:

  ```bash
  uv run python scripts/train_attendance_model.py
  ```

- Исходные данные для обучения: `data/training/attendance_training.csv`.  
- Путь к сохранённой модели задаётся в **`AI_MODEL_PATH`** (в Docker образ копируется каталог **`models/`**).

## Миграции Alembic

Создание ревизии (после изменений моделей):

```bash
uv run alembic revision --autogenerate -m "описание"
uv run alembic upgrade head
```

## Линтинг и проверка типов

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

Форматирование кода:

```bash
uv run ruff format .
```
