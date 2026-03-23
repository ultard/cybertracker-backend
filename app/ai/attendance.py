from __future__ import annotations

from datetime import datetime

import numpy as np

from app.ai.features import build_feature_row
from app.ai.model import load_model


def _heuristic_attendance(
    *,
    discipline_id: int,
    tournament_type: str,
    event_datetime: datetime,
    prize_pool: float,
    registered_count: int,
) -> float:
    """Запасной вариант, если файл обученной модели ещё не собран (joblib отсутствует)."""
    row = build_feature_row(
        discipline_id=discipline_id,
        tournament_type=tournament_type,  # type: ignore[arg-type]
        event_datetime=event_datetime,
        prize_pool=prize_pool,
        registered_count=registered_count,
    )
    offline = float(row[1])
    reg = float(row[7])
    lp = float(row[6])
    dow = int(row[3])
    weekend = 1.12 if dow >= 5 else 1.0
    raw = 0.58 * reg + 0.06 * float(discipline_id) + 4.0 * offline + 0.42 * lp
    raw *= weekend
    return max(0.0, raw)


def predict_attendance(
    *,
    discipline_id: int,
    tournament_type: str,
    event_datetime: datetime,
    prize_pool: float,
    registered_count: int,
) -> tuple[int, dict]:
    """
    Возвращает прогноз явки и словарь метрик модели (MAE, RMSE, R² на валидации при обучении).

    При отсутствии артефакта модели используется эвристика, метрики — None.
    """
    X = build_feature_row(
        discipline_id=discipline_id,
        tournament_type=tournament_type,  # type: ignore[arg-type]
        event_datetime=event_datetime,
        prize_pool=prize_pool,
        registered_count=registered_count,
    ).reshape(1, -1)
    artifact = load_model()
    if artifact is not None:
        pipeline = artifact["pipeline"]
        pred = float(np.asarray(pipeline.predict(X), dtype=np.float64).ravel()[0])
        metrics = artifact.get("metrics") or {}
        out_metrics: dict = {
            "mae": metrics.get("mae"),
            "rmse": metrics.get("rmse"),
            "r2": metrics.get("r2"),
        }
    else:
        pred = _heuristic_attendance(
            discipline_id=discipline_id,
            tournament_type=tournament_type,
            event_datetime=event_datetime,
            prize_pool=prize_pool,
            registered_count=registered_count,
        )
        out_metrics = {
            "mae": None,
            "rmse": None,
            "r2": None,
            "note": (
                "Модель не найдена; использована эвристика. "
                "Запустите scripts/train_attendance_model.py"
            ),
        }
    pred_int = max(0, int(round(pred)))
    return pred_int, out_metrics


def recommendations(*, predicted: int, max_participants: int, prize_pool: float) -> list[str]:
    """Короткие рекомендации по прогнозу (бизнес-процесс 3 из ТЗ)."""
    cap = max(max_participants, 1)
    ratio = predicted / cap
    recs: list[str] = []
    if ratio < 0.35:
        recs.append(
            "Прогноз явки заметно ниже лимита участников. Имеет смысл усилить продвижение "
            "или рассмотреть рост призового фонда на 10–20 %."
        )
    if ratio > 0.92:
        recs.append(
            "Ожидается высокая загрузка относительно лимита. Подготовьте дополнительные слоты "
            "или персонал на регистрации и входе."
        )
    if prize_pool < 15000 and predicted > 25:
        recs.append(
            "При скромном призовом фонде прогноз явки высокий — "
            "проверьте вместимость площадки и очереди."
        )
    if not recs:
        recs.append(
            "Параметры турнира согласованы с прогнозом явки. "
            "Продолжайте отслеживать регистрации."
        )
    return recs
