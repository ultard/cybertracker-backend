"""Юнит-тесты рекомендаций по посещаемости (без загрузки ML-модели)."""

from datetime import UTC, datetime

import pandas as pd
from app.ai.attendance import FEATURE_ORDER, _features_frame, recommendations


def test_features_frame_extracts_time_fields():
    dt = datetime(2026, 5, 19, 15, 30, tzinfo=UTC)
    frame = _features_frame(
        discipline_name="Dota 2",
        tournament_type="online",
        event_datetime=dt,
        prize_pool=1000.0,
        registered_count=32,
    )
    assert list(frame.columns) == list(FEATURE_ORDER)
    assert frame.iloc[0]["hour"] == 15
    assert frame.iloc[0]["day_of_week"] == dt.weekday()
    assert frame.iloc[0]["month"] == 5


def test_recommendations_when_over_capacity():
    recs = recommendations(predicted=120, max_participants=100, prize_pool=5000)
    assert any("лимит" in r.lower() for r in recs)


def test_recommendations_when_low_fill():
    recs = recommendations(predicted=5, max_participants=100, prize_pool=0)
    assert any("низкая" in r.lower() for r in recs)


def test_recommendations_balanced_case():
    recs = recommendations(predicted=50, max_participants=100, prize_pool=0)
    assert len(recs) == 1
    assert "согласованы" in recs[0].lower()


def test_recommendations_prize_pool_hint():
    recs = recommendations(predicted=10, max_participants=100, prize_pool=50000)
    assert any("призовой" in r.lower() for r in recs)


def test_features_frame_category_dtypes():
    frame = _features_frame(
        discipline_name="Valorant",
        tournament_type="offline",
        event_datetime=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        prize_pool=0,
        registered_count=0,
    )
    assert isinstance(frame["discipline_name"].dtype, pd.CategoricalDtype)
