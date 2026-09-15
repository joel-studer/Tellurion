"""FUTURE-ONLY canonical forecast adapter (no training in V14).

One interface; ranked frameworks; install nothing until V15 challenger
samples exist. Frameworks never define truth — the identical-sample
harness does.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

RANKING = (
    ("kronos", "PRIMARY CHALLENGER CANDIDATE",
     "MIT code+open weights; prediction horizons fit reaction-profile questions"),
    ("sktime", "SECONDARY CHALLENGER",
     "BSD-3; sklearn-native classical/ML pool; light"),
    ("darts", "SECONDARY CHALLENGER",
     "Apache-2.0; deep + probabilistic models; heavier"),
    ("statsforecast", "MODEL-SPECIFIC EXPERIMENT",
     "Apache-2.0; fast classical baselines (AutoARIMA/ETS/CES)"),
    ("gluonts", "REFERENCE_ONLY",
     "Apache-2.0; heavier than darts/sktime for our need"),
)


class ForecastModelAdapter(ABC):
    framework: str = "UNKNOWN"

    @abstractmethod
    def fit(self, frame: Any, horizon: int) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def predict(self, frame: Any, horizon: int) -> Dict[str, Any]:
        raise NotImplementedError


class FixtureForecast(ForecastModelAdapter):
    framework = "fixture"

    def fit(self, frame: Any, horizon: int) -> Dict[str, Any]:
        return {"framework": "fixture", "horizon": horizon, "status": "FIT-RECORDED"}

    def predict(self, frame: Any, horizon: int) -> Dict[str, Any]:
        n = len(frame) if hasattr(frame, "__len__") else 0
        return {"framework": "fixture", "horizon": horizon, "n": n,
                "preds": [0.0] * horizon, "basis": "FIXTURE (no model)"}


def ranking() -> list[tuple]:
    return list(RANKING)
