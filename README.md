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

## Структура кода

Код в основном в `app/` и разнесён по слоям: **роутеры (HTTP) → зависимости (auth/roles/db) → репозитории (работа с БД) → модели/схемы**.

- **`app/main.py`**: точка входа FastAPI — middleware, CORS, rate limit, подключение `api_router`, lifespan (инициализация таблиц и сиды).
- **`app/config.py`**: настройки из `.env` (JWT, БД, CORS, AI-модель и т.д.).
- **`app/routers/`**: HTTP-эндпоинты, валидация входа/выхода и права доступа.
  - **`app/routers/__init__.py`**: сборка общего `api_router` и подключение под-роутеров (`/auth`, `/users`, `/tournaments`, `/qr`, `/predict` и т.д.).
- **`app/deps.py`**: зависимости FastAPI (`get_db`, `get_current_user`, `require_roles`) — общий механизм авторизации/ролей для роутеров.
- **`app/repositories/`**: слой доступа к данным (SQLAlchemy запросы, пагинация, поиск, CRUD).
  - **`app/repositories/base.py`**: базовые методы (получение по id, пагинация).
- **`app/models/`**: SQLAlchemy модели (таблицы) и перечисления (`enums.py`).
- **`app/schemas/`**: Pydantic-схемы запросов/ответов.
- **`app/db/`**: инфраструктура БД.
  - **`app/db/session.py`**: engine + `AsyncSession` фабрика и выдача сессии.
  - **`app/db/base.py`**: декларативная база моделей.
  - **`app/db/seed.py`**: идемпотентные сиды (роли, дисциплины, admin).
- **`app/core/`**: общие сервисы/утилиты.
  - **`app/core/security.py`**: хеширование паролей, JWT access/refresh, decode/verify.
  - **`app/core/audit_service.py`**: запись событий в аудит.
  - **`app/core/limiter.py`**: rate limiter (SlowAPI).
- **`app/ai/attendance.py`**: инференс XGBoost-модели и генерация рекомендаций (используется роутом `/api/predict/...`).
- **`app/openapi.py`**: теги и описания для документации Scalar/OpenAPI/Swagger.
- **`alembic/`**: миграции схемы БД.

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

### Как обучалась модель

- Ноутбук: `notebooks/train.ipynb`.
- Данные: `data/training/attendance_synthetic.csv`.
- Разбиение: **train/test 80/20** (`train_test_split`).
- Модель: **XGBoost**, подбор гиперпараметров **Optuna** с целевой функцией **MAE** на валидационной части.
- Итоговая модель дообучается на train+val логике из ноутбука и сохраняется в **`models/xgboost_attendance.ubj`** (`save_model`).

### По каким метрикам судить о качестве

На отложенной **test**-выборке в ноутбуке считаются:

| Метрика | Смысл |
|--------|--------|
| **MAE** | Средняя абсолютная ошибка (в тех же единицах, что и посещаемость); **основной** ориентир при подборе гиперпараметров. |
| **RMSE** | Штрафует большие ошибки сильнее, чем MAE. |
| **R²** | Доля объяснённой дисперсии (1 — идеально на выборке; сравнивать только на test, не на train). |

Практически: смотреть прежде всего **MAE и RMSE** на test; **R²** — как дополнительный индикатив. Для «годности» ориентируйтесь на допустимую для предметной области среднюю ошибку (например, ±N человек относительно типичных значений целевой переменной).

### Как использовать модель в API

1. Положите файл модели в `models/` (или укажите свой путь).
2. В **`.env`** задайте **`AI_MODEL_PATH`** — относительно корня backend, например `models/xgboost_attendance.ubj`.
3. Инференс: **POST** `/api/predict/tournament/{tournament_id}`. Бэкенд подставляет признаки из турнира и возвращает прогноз и текстовые рекомендации.

Переобучение: снова выполните ячейки в `train.ipynb` и перезапишите `models/xgboost_attendance.ubj`, затем перезапустите API (или смените `AI_MODEL_PATH` на новый файл).

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
