"""Feature engineering interface and modular skeleton.

Concrete domain features (rolling card velocity, Haversine distance, category ratios)
can be plugged into `FeaturePipeline` once EDA hypotheses and parameter choices are finalized.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd

FeatureStep = Callable[[pd.DataFrame], pd.DataFrame]


@dataclass
class FeaturePipeline:
    """Composable feature engineering pipeline that applies registered transforms in order."""

    steps: list[tuple[str, FeatureStep]] = field(default_factory=list)

    def add_step(self, name: str, func: FeatureStep) -> FeaturePipeline:
        """Register a named transformation function."""
        self.steps.append((name, func))
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all registered feature engineering steps sequentially."""
        out = df.copy()
        for _, func in self.steps:
            out = func(out)
        return out
