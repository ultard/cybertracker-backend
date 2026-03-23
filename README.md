# CyberTracker backend

REST API на FastAPI.

## Установка (UV)

```bash
cd backend
uv sync --all-groups
```

Запуск:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Документация API:

- **Scalar** (интерактивная): [http://127.0.0.1:8000/scalar](http://127.0.0.1:8000/scalar)
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

Конфигурация в `app/config.py`: секции (окружение, сервер, JWT, cookie, БД, Redis), `LogLevel`, сборка URL через **yarl** (`db_url` → `database_url`, `redis_url`), CORS из строки **`origins`** (через запятую) и свойство **`parse_origins`**. Пример переменных — `.env.example`.

## PostgreSQL и миграции (Alembic)

```bash
docker compose up -d db
# дождаться healthcheck, затем:
uv run alembic revision --autogenerate -m "initial"
uv run alembic upgrade head
```

При первом запуске приложение также может создать таблицы через `create_all` в `lifespan` (удобно для разработки). Для продакшена ориентируйтесь на миграции.

## Линтинг и типы

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
```
