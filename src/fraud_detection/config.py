"""Configuration loader and project path management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"


@dataclass(frozen=True)
class ProjectConfig:
    name: str = "transaction-fraud-detection-platform"
    dataset: str = "sparkov_credit_card_fraud"
    seed: int = 42


@dataclass(frozen=True)
class PathsConfig:
    raw_data: Path = PROJECT_ROOT / "data" / "raw"
    interim_data: Path = PROJECT_ROOT / "data" / "interim"
    processed_data: Path = PROJECT_ROOT / "data" / "processed"
    models_dir: Path = PROJECT_ROOT / "models"
    reports_dir: Path = PROJECT_ROOT / "reports"

    @classmethod
    def from_dict(cls, data: dict[str, Any], root: Path = PROJECT_ROOT) -> PathsConfig:
        def _resolve(rel_or_abs: str, default: str) -> Path:
            p = Path(data.get(rel_or_abs, default))
            return p if p.is_absolute() else (root / p)

        return cls(
            raw_data=_resolve("raw_data", "data/raw"),
            interim_data=_resolve("interim_data", "data/interim"),
            processed_data=_resolve("processed_data", "data/processed"),
            models_dir=_resolve("models_dir", "models"),
            reports_dir=_resolve("reports_dir", "reports"),
        )


@dataclass(frozen=True)
class PreprocessingConfig:
    id_col: str = "trans_num"
    card_col: str = "cc_num"
    target_col: str = "is_fraud"
    timestamp_col: str = "trans_date_trans_time"
    unix_time_col: str = "unix_time"
    rename_cols: dict[str, str] = field(
        default_factory=lambda: {
            "state": "state_code",
            "long": "lon",
            "merch_long": "merch_lon",
        }
    )
    drop_cols: list[str] = field(
        default_factory=lambda: ["Unnamed: 0", "first", "last", "street"]
    )
    categorical_cols: list[str] = field(
        default_factory=lambda: ["merchant", "category", "gender", "state_code", "job"]
    )
    numerical_cols: list[str] = field(
        default_factory=lambda: ["amt", "lat", "lon", "city_pop", "merch_lat", "merch_lon"]
    )
    val_size: float = 0.15


@dataclass(frozen=True)
class TrainingConfig:
    threshold: float = 0.5


@dataclass(frozen=True)
class AppConfig:
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    ui_port: int = 8501


@dataclass(frozen=True)
class DatabaseConfig:
    url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fraud_detection"
    echo: bool = False


@dataclass(frozen=True)
class Settings:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    app: AppConfig = field(default_factory=AppConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    raw: dict[str, Any] = field(default_factory=dict)


def load_raw_config(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    """Load the raw YAML dictionary from disk."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def load_config(config_path: str | Path = CONFIG_PATH) -> Settings:
    """Load and parse the project YAML configuration into typed dataclasses."""
    raw = load_raw_config(config_path)

    proj_raw = raw.get("project", {})
    prep_raw = raw.get("preprocessing", {})
    train_raw = raw.get("training", {})
    app_raw = raw.get("app", {})
    db_raw = raw.get("database", {})

    return Settings(
        project=ProjectConfig(
            name=proj_raw.get("name", "transaction-fraud-detection-platform"),
            dataset=proj_raw.get("dataset", "sparkov_credit_card_fraud"),
            seed=int(proj_raw.get("seed", 42)),
        ),
        paths=PathsConfig.from_dict(raw.get("paths", {}), root=PROJECT_ROOT),
        preprocessing=PreprocessingConfig(
            id_col=prep_raw.get("id_col", "trans_num"),
            card_col=prep_raw.get("card_col", "cc_num"),
            target_col=prep_raw.get("target_col", "is_fraud"),
            timestamp_col=prep_raw.get("timestamp_col", "trans_date_trans_time"),
            unix_time_col=prep_raw.get("unix_time_col", "unix_time"),
            rename_cols=dict(
                prep_raw.get(
                    "rename_cols",
                    {"state": "state_code", "long": "lon", "merch_long": "merch_lon"},
                )
            ),
            drop_cols=list(
                prep_raw.get("drop_cols", ["Unnamed: 0", "first", "last", "street"])
            ),
            categorical_cols=list(
                prep_raw.get(
                    "categorical_cols",
                    ["merchant", "category", "gender", "state_code", "job"],
                )
            ),
            numerical_cols=list(
                prep_raw.get(
                    "numerical_cols",
                    ["amt", "lat", "lon", "city_pop", "merch_lat", "merch_lon"],
                )
            ),
            val_size=float(prep_raw.get("val_size", 0.15)),
        ),
        training=TrainingConfig(
            threshold=float(train_raw.get("threshold", 0.5)),
        ),
        app=AppConfig(
            api_host=app_raw.get("api_host", "0.0.0.0"),
            api_port=int(app_raw.get("api_port", 8000)),
            ui_port=int(app_raw.get("ui_port", 8501)),
        ),
        database=DatabaseConfig(
            url=db_raw.get(
                "url",
                "postgresql+psycopg://postgres:postgres@localhost:5432/fraud_detection",
            ),
            echo=bool(db_raw.get("echo", False)),
        ),
        raw=raw,
    )
