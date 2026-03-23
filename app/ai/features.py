from __future__ import annotations

from datetime import UTC, datetime
from math import log1p
from typing import Literal

import numpy as np
from numpy.typing import NDArray

TournamentTypeStr = Literal["online", "offline"]


def season_from_month(month: int) -> int:
    """0 — зима, 1 — весна, 2 — лето, 3 — осень."""
    if month in (12, 1, 2):
        return 0
    if month in (3, 4, 5):
        return 1
    if month in (6, 7, 8):
        return 2
    return 3


def build_feature_row(
    *,
    discipline_id: int,
    tournament_type: TournamentTypeStr,
    event_datetime: datetime,
    prize_pool: float,
    registered_count: int,
) -> NDArray[np.float64]:
    """Один объект: дисциплина, тип (online/offline), дата/время, приз, регистрации."""
    if event_datetime.tzinfo is not None:
        dt = event_datetime.astimezone(UTC).replace(tzinfo=None)
    else:
        dt = event_datetime
    hour = dt.hour
    dow = dt.weekday()
    month = dt.month
    season = season_from_month(month)
    offline = 1.0 if tournament_type == "offline" else 0.0
    return np.array(
        [
            float(discipline_id),
            offline,
            float(hour),
            float(dow),
            float(month),
            float(season),
            log1p(max(prize_pool, 0.0)),
            float(registered_count),
        ],
        dtype=np.float64,
    )


def build_feature_matrix(rows: list[NDArray[np.float64]]) -> NDArray[np.float64]:
    return np.vstack(rows)
