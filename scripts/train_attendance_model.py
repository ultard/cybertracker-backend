#!/usr/bin/env python3
"""
Обучение модели прогноза явки (RandomForest, scikit-learn) и сохранение joblib.

Исходные данные по умолчанию: data/training/attendance_training.csv
Результат: models/attendance_model.joblib (путь можно переопределить через AI_MODEL_PATH / --out).

Запуск из корня репозитория:
  python scripts/train_attendance_model.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from math import sqrt
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.features import build_feature_row  # noqa: E402


def load_dataset(csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    X_rows: list[np.ndarray] = []
    y_vals: list[float] = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = datetime.fromisoformat(row["event_datetime"].replace("Z", "+00:00"))
            x = build_feature_row(
                discipline_id=int(row["discipline_id"]),
                tournament_type=row["tournament_type"],  # type: ignore[arg-type]
                event_datetime=dt,
                prize_pool=float(row["prize_pool"]),
                registered_count=int(row["registered_count"]),
            )
            X_rows.append(x)
            y_vals.append(float(row["actual_attendance"]))
    X = np.vstack(X_rows)
    y = np.asarray(y_vals, dtype=np.float64)
    return X, y


def main() -> None:
    parser = argparse.ArgumentParser(description="Обучение модели посещаемости турниров")
    parser.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "data" / "training" / "attendance_training.csv",
        help="CSV с колонками discipline_id, tournament_type, event_datetime, ...",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "models" / "attendance_model.joblib",
        help="Куда сохранить joblib",
    )
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.csv.is_file():
        raise SystemExit(f"Файл данных не найден: {args.csv}")

    X, y = load_dataset(args.csv)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed
    )

    pipeline = Pipeline(
        steps=[
            (
                "model",
                RandomForestRegressor(
                    n_estimators=200,
                    max_depth=12,
                    min_samples_leaf=2,
                    random_state=args.seed,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "pipeline": pipeline,
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
        "feature_names": [
            "discipline_id",
            "is_offline",
            "hour",
            "day_of_week",
            "month",
            "season",
            "log1p_prize_pool",
            "registered_count",
        ],
    }
    joblib.dump(artifact, args.out)
    print(f"Сохранено: {args.out}")
    print(f"Валидация: MAE={mae:.4f} RMSE={rmse:.4f} R²={r2:.4f} (test_size={args.test_size})")


if __name__ == "__main__":
    main()
