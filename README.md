# CyberTracker backend

REST API на **FastAPI** для киберспорт-арены: турниры, регистрации, QR-проход, аудит, прогноз посещаемости (модуль ИИ). База данных — **PostgreSQL** (SQLAlchemy 2 async, Alembic).

## Требования

- **Python** ≥ 3.14  
- **[uv](https://docs.astral.sh/uv/)** 
- **Docker** + **Docker Compose**

## Документация API

| Ресурс        | URL |
|---------------|-----|
| Scalar        | http://127.0.0.1:8000/scalar |
| Swagger UI    | http://127.0.0.1:8000/docs |
| ReDoc         | http://127.0.0.1:8000/redoc |
| OpenAPI JSON  | http://127.0.0.1:8000/openapi.json |

## Конфигурация

Параметры задаются переменными окружения и файлом **`.env`** (см. `.env.example`)

## Docker: продакшен-стек

```bash
docker compose up -d --build
```

Остановка:

```bash
docker compose down
```

## Docker: разработка

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

Остановка:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

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
