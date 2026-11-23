"""End-to-end preprocessing pipeline orchestration (Load -> Clean -> Validate -> Save Interim)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from fraud_detection.config import Settings, load_config
from fraud_detection.utils.logger import get_logger
from preprocessing.cleaner import clean_transactions
from preprocessing.loader import load_raw_csv, save_parquet
from preprocessing.validation import ValidationReport, validate_transactions

logger = get_logger(__name__)


@dataclass
class BatchPreprocessingResult:
    """Result container for a single CSV-to-Parquet preprocessing batch run."""

    source_path: Path
    output_path: Path | None
    validation_report: ValidationReport
    cleaned_df: pd.DataFrame


def process_raw_file(
    csv_path: str | Path,
    *,
    output_parquet_path: str | Path | None = None,
    settings: Settings | None = None,
    drop_pii: bool = False,
    nrows: int | None = None,
) -> BatchPreprocessingResult:
    """Load a raw Sparkov CSV file, standardize columns, validate data quality, and save to Parquet.

    Args:
        csv_path: Path to raw CSV (e.g., data/raw/fraudTrain.csv).
        output_parquet_path: Optional destination Parquet path (e.g., data/interim/train_cleaned.parquet).
        settings: Optional loaded project Settings.
        drop_pii: Whether to drop PII columns (`first`, `last`, `street`) before saving.
        nrows: Optional row limit for quick testing.

    Returns:
        BatchPreprocessingResult with cleaned valid DataFrame and validation report.
    """
    cfg = settings if settings is not None else load_config()
    raw_df = load_raw_csv(csv_path, nrows=nrows)

    # Standardize column names and timestamps first; keep duplicates so validator can count & quarantine them
    standardized_df = clean_transactions(
        raw_df,
        rename_map=cfg.preprocessing.rename_cols,
        drop_cols=("Unnamed: 0",),
        drop_pii=drop_pii,
        deduplicate=False,
        id_col=cfg.preprocessing.id_col,
        timestamp_col=cfg.preprocessing.timestamp_col,
    )

    report = validate_transactions(
        standardized_df,
        id_col=cfg.preprocessing.id_col,
        target_col=cfg.preprocessing.target_col,
    )

    saved_path: Path | None = None
    if output_parquet_path is not None:
        saved_path = save_parquet(report.valid_df, output_parquet_path)

    return BatchPreprocessingResult(
        source_path=Path(csv_path),
        output_path=saved_path,
        validation_report=report,
        cleaned_df=report.valid_df,
    )
