"""Прогноз посещаемости по обученной XGBoost-модели (см. notebooks/train.ipynb)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

import pandas as pd
from xgboost import XGBRegressor

from app.config import get_settings

_MODEL_LOCK = Lock()
_model: XGBRegressor | None = None

FEATURE_ORDER = (
    "discipline_name",
    "tournament_type",
    "hour",
    "day_of_week",
    "month",
    "prize_pool",
    "registered_count",
)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _model_path() -> Path:
    settings = get_settings()
    p = Path(settings.ai_model_path)
    if p.is_absolute():
        return p
    return _backend_root() / p


def _get_model() -> XGBRegressor:
    global _model
    with _MODEL_LOCK:
        if _model is None:
            path = _model_path()
            if not path.is_file():
                msg = f"Файл модели не найден: {path}"
                raise FileNotFoundError(msg)
            booster = XGBRegressor()
            booster.load_model(str(path))
            _model = booster
        return _model


def _features_frame(
    *,
    discipline_name: str,
    tournament_type: str,
    event_datetime: datetime,
    prize_pool: float,
    registered_count: int,
) -> pd.DataFrame:
    dt = event_datetime
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    row = {
        "discipline_name": discipline_name,
        "tournament_type": tournament_type,
        "hour": dt.hour,
        "day_of_week": dt.weekday(),
        "month": dt.month,
        "prize_pool": prize_pool,
        "registered_count": registered_count,
    }
    X = pd.DataFrame([row], columns=list(FEATURE_ORDER))
    X["discipline_name"] = X["discipline_name"].astype("category")
    X["tournament_type"] = X["tournament_type"].astype("category")
    return X


def predict_attendance(
    *,
    discipline_name: str,
    tournament_type: str,
    event_datetime: datetime,
    prize_pool: float,
    registered_count: int,
) -> tuple[int, dict[str, float | None]]:
    """Возвращает прогноз числа посетителей и словарь метрик (пустой при инференсе без разметки)."""
    X = _features_frame(
        discipline_name=discipline_name,
        tournament_type=tournament_type,
        event_datetime=event_datetime,
        prize_pool=prize_pool,
        registered_count=registered_count,
    )
    raw = float(_get_model().predict(X)[0])
    predicted = max(0, int(round(raw)))
    return predicted, {}


def recommendations(
    *,
    predicted: int,
    max_participants: int,
    prize_pool: float,
) -> list[str]:
    """Краткие рекомендации на основе прогноза и лимитов турнира."""
    recs: list[str] = []
    if predicted > max_participants:
        recs.append(
            "Прогноз превышает лимит участников; стоит пересмотреть вместимость или формат."
        )
    elif predicted < max(1, max_participants) * 0.25:
        recs.append(
            "Ожидается низкая заполняемость; можно усилить продвижение или гибкость регистрации."
        )
    if prize_pool > 0 and predicted < max_participants * 0.4:
        recs.append("При умеренном интересе призовой пул можно сопоставить с ожидаемой аудиторией.")
    if not recs:
        recs.append("Параметры турнира согласованы с прогнозом посещаемости.")
    return recs
