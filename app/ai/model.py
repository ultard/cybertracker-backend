from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from app.config import get_settings


class ModelArtifact(dict[str, Any]):
    """Ожидаемые ключи: pipeline, metrics (mae, rmse, r2)."""


@lru_cache
def get_model_path() -> Path:
    settings = get_settings()
    path = Path(settings.ai_model_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def clear_model_cache() -> None:
    get_model_path.cache_clear()
    load_model.cache_clear()


@lru_cache
def load_model() -> ModelArtifact | None:
    path = get_model_path()
    if not path.is_file():
        return None
    data = joblib.load(path)
    if not isinstance(data, dict) or "pipeline" not in data:
        return None
    return ModelArtifact(data)
